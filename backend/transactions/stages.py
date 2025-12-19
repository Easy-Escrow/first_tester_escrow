from __future__ import annotations

from typing import Optional

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from .models import (
    InvitationStatus,
    ParticipantRole,
    Transaction,
    TransactionEvent,
    TransactionEventType,
    TransactionInvitation,
    TransactionStage,
    TransactionType,
)

User = get_user_model()


def log_transaction_event(
    *, transaction: Transaction, event_type: str, actor: Optional[User] = None, data: Optional[dict] = None
) -> TransactionEvent:
    return TransactionEvent.objects.create(
        transaction=transaction,
        type=event_type,
        actor=actor,
        data=data or {},
    )


def _required_roles(transaction: Transaction) -> set[str]:
    base_roles = {ParticipantRole.BROKER_PRIMARY, ParticipantRole.BUYER, ParticipantRole.SELLER}
    if transaction.type == TransactionType.DOUBLE_BROKER_SPLIT:
        base_roles.add(ParticipantRole.BROKER_SECONDARY)
    return base_roles


def _is_participant_accepted(participant) -> bool:
    if not participant.user_id or not participant.joined_at:
        return False
    try:
        invitation = participant.transactioninvitation
        return invitation.status == InvitationStatus.ACCEPTED
    except TransactionInvitation.DoesNotExist:
        return True


def evaluate_stage(transaction: Transaction) -> str:
    participants = list(transaction.participants.all().select_related("transactioninvitation"))
    role_map = {participant.role: participant for participant in participants}
    required_roles = _required_roles(transaction)
    accepted_roles: set[str] = set()

    for role in required_roles:
        participant = role_map.get(role)
        if participant and _is_participant_accepted(participant):
            accepted_roles.add(role)

    if transaction.type == TransactionType.DOUBLE_BROKER_SPLIT:
        counterparty_present = ParticipantRole.BUYER in role_map and ParticipantRole.SELLER in role_map
        if not counterparty_present:
            return TransactionStage.PENDING_INVITATIONS

    if required_roles.issubset(accepted_roles):
        return TransactionStage.PENDING_USER_INFORMATION

    return TransactionStage.PENDING_INVITATIONS


@transaction.atomic
def recalc_and_transition_stage(transaction: Transaction, actor: Optional[User] = None) -> Transaction:
    old_stage = transaction.stage
    new_stage = evaluate_stage(transaction)

    if new_stage != old_stage:
        transaction.stage = new_stage
        transaction.stage_updated_at = timezone.now()
        transaction.save(update_fields=["stage", "stage_updated_at", "updated_at"])
        log_transaction_event(
            transaction=transaction,
            event_type=TransactionEventType.STAGE_CHANGED,
            actor=actor,
            data={"from": old_stage, "to": new_stage},
        )

    return transaction
