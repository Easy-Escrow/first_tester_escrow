from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Dict

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from .models import (
    CommissionSplit,
    InvitationStatus,
    ParticipantRole,
    TransactionParticipant,
    Transaction,
    TransactionDetails,
    TransactionInvitation,
    TransactionEventType,
    TransactionStatus,
    TransactionType,
)
from .stages import log_transaction_event, recalc_and_transition_stage

User = get_user_model()


@dataclass
class TransactionCreationPayload:
    type: str
    payload: Dict[str, Any]


INVITE_EXPIRY_DAYS = 7


def _require_broker(user: User) -> None:
    if not getattr(user, "is_broker", False):
        raise PermissionDenied("Only brokers can perform this action.")


def _create_invitation(participant: "TransactionParticipant", actor: User | None = None) -> TransactionInvitation:
    invitation = TransactionInvitation.objects.create(
        transaction=participant.transaction,
        participant=participant,
        expires_at=timezone.now() + timedelta(days=INVITE_EXPIRY_DAYS),
    )
    log_transaction_event(
        transaction=participant.transaction,
        event_type=TransactionEventType.INVITATION_SENT,
        actor=actor,
        data={"participant_role": participant.role, "invited_email": participant.invited_email},
    )
    return invitation


@transaction.atomic
def create_transaction(
    *, created_by: User, type: str, payload: Dict[str, Any], core_fields: Dict[str, Any]
) -> Transaction:
    _require_broker(created_by)

    if type not in TransactionType.values:
        raise ValidationError("Invalid transaction type")

    transaction_obj = Transaction.objects.create(
        created_by=created_by,
        type=type,
        status=TransactionStatus.DRAFT,
        **core_fields,
    )

    details = payload.copy()
    participants = []

    # Primary broker is always creator
    participants.append(
        {
            "role": ParticipantRole.BROKER_PRIMARY,
            "user": created_by,
            "invited_email": created_by.email,
            "joined_at": timezone.now(),
        }
    )

    if type == TransactionType.SINGLE_BROKER_SALE:
        buyer_email = payload.get("buyer_email")
        seller_email = payload.get("seller_email")
        if not buyer_email or not seller_email:
            raise ValidationError("buyer_email and seller_email are required")

        TransactionDetails.objects.create(transaction=transaction_obj, data=details)

        participants.extend(
            [
                {
                    "role": ParticipantRole.BUYER,
                    "invited_email": buyer_email,
                },
                {
                    "role": ParticipantRole.SELLER,
                    "invited_email": seller_email,
                },
            ]
        )
    elif type == TransactionType.DOUBLE_BROKER_SPLIT:
        known_role = payload.get("known_party_role")
        known_email = payload.get("known_party_email")
        secondary_email = payload.get("secondary_broker_email")
        if known_role not in (ParticipantRole.BUYER, ParticipantRole.SELLER):
            raise ValidationError("known_party_role must be buyer or seller")
        if not known_email or not secondary_email:
            raise ValidationError("known_party_email and secondary_broker_email are required")

        split = payload.get("commission_split") or {"primary_broker_pct": 50, "secondary_broker_pct": 50}
        CommissionSplit.objects.create(
            transaction=transaction_obj,
            primary_broker_pct=split.get("primary_broker_pct", 50),
            secondary_broker_pct=split.get("secondary_broker_pct", 50),
        )
        TransactionDetails.objects.create(transaction=transaction_obj, data=details)

        participants.extend(
            [
                {
                    "role": ParticipantRole.BROKER_SECONDARY,
                    "invited_email": secondary_email,
                },
                {
                    "role": known_role,
                    "invited_email": known_email,
                },
            ]
        )
    else:
        TransactionDetails.objects.create(transaction=transaction_obj, data=details)

    participant_objs = []
    for participant in participants:
        participant_objs.append(
            transaction_obj.participants.create(
                role=participant["role"],
                invited_email=participant["invited_email"],
                invited_by=created_by,
                user=participant.get("user"),
                joined_at=participant.get("joined_at"),
            )
        )

    # Create invitations for non-creator participants
    for part in participant_objs:
        if part.user_id != created_by.id:
            _create_invitation(part, actor=created_by)

    transaction_obj.status = TransactionStatus.INVITING if len(participant_objs) > 1 else TransactionStatus.DRAFT
    transaction_obj.save(update_fields=["status", "updated_at"])
    recalc_and_transition_stage(transaction_obj, actor=created_by)

    return transaction_obj


@transaction.atomic
def invite_counterparty(*, transaction_obj: Transaction, acting_user: User, counterparty_email: str):
    if transaction_obj.type != TransactionType.DOUBLE_BROKER_SPLIT:
        raise ValidationError("Counterparty invites only valid for double broker split")

    try:
        secondary_participant = transaction_obj.participants.get(role=ParticipantRole.BROKER_SECONDARY)
    except TransactionParticipant.DoesNotExist:
        raise ValidationError("Secondary broker not found")

    if secondary_participant.user_id != acting_user.id:
        raise PermissionDenied("Only the accepted secondary broker can invite the counterparty")

    if not secondary_participant.joined_at:
        raise PermissionDenied("Secondary broker must accept invitation first")

    roles_present = set(transaction_obj.participants.values_list("role", flat=True))
    if ParticipantRole.BUYER in roles_present and ParticipantRole.SELLER in roles_present:
        raise ValidationError("All parties already present")

    missing_role = ParticipantRole.SELLER if ParticipantRole.BUYER in roles_present else ParticipantRole.BUYER
    participant = transaction_obj.participants.create(
        role=missing_role,
        invited_email=counterparty_email,
        invited_by=acting_user,
    )
    log_transaction_event(
        transaction=transaction_obj,
        event_type=TransactionEventType.COUNTERPARTY_INVITED,
        actor=acting_user,
        data={"invited_email": counterparty_email, "role": participant.role},
    )
    invitation = _create_invitation(participant, actor=acting_user)
    recalc_and_transition_stage(transaction_obj, actor=acting_user)
    return participant, invitation


@transaction.atomic
def accept_invitation(*, token: str, user: User) -> Transaction:
    try:
        invitation = TransactionInvitation.objects.select_related("participant", "transaction").get(token=token)
    except TransactionInvitation.DoesNotExist as exc:  # pragma: no cover - defensive
        raise ValidationError("Invalid invitation token") from exc

    if invitation.status != InvitationStatus.PENDING:
        raise ValidationError("Invitation is not pending")

    if invitation.is_expired():
        invitation.status = InvitationStatus.EXPIRED
        invitation.save(update_fields=["status"])
        raise ValidationError("Invitation has expired")

    participant = invitation.participant

    if participant.role == ParticipantRole.BROKER_SECONDARY and not getattr(user, "is_broker", False):
        raise PermissionDenied("Secondary broker must be a broker user")

    participant.user = user
    participant.joined_at = timezone.now()
    participant.save(update_fields=["user", "joined_at"])

    invitation.status = InvitationStatus.ACCEPTED
    invitation.save(update_fields=["status"])

    transaction_obj = invitation.transaction
    log_transaction_event(
        transaction=transaction_obj,
        event_type=TransactionEventType.INVITATION_ACCEPTED,
        actor=user,
        data={"participant_role": participant.role, "email": participant.invited_email},
    )

    required_roles = {ParticipantRole.BROKER_PRIMARY, ParticipantRole.BUYER, ParticipantRole.SELLER}
    if transaction_obj.type == TransactionType.DOUBLE_BROKER_SPLIT:
        required_roles.add(ParticipantRole.BROKER_SECONDARY)

    accepted_roles = set(
        transaction_obj.participants.filter(joined_at__isnull=False).values_list("role", flat=True)
    )
    if transaction_obj.status == TransactionStatus.INVITING and required_roles.issubset(accepted_roles):
        transaction_obj.status = TransactionStatus.ACTIVE
        transaction_obj.save(update_fields=["status", "updated_at"])

    recalc_and_transition_stage(transaction_obj, actor=user)

    return transaction_obj
