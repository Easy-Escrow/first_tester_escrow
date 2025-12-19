from __future__ import annotations

from typing import Any, Dict

from rest_framework import serializers

from accounts.models import User
from .models import (
    CommissionSplit,
    InvitationStatus,
    ParticipantRole,
    Transaction,
    TransactionDetails,
    TransactionEvent,
    TransactionInvitation,
    TransactionStatus,
    TransactionType,
)


class CommissionSplitSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommissionSplit
        fields = ("primary_broker_pct", "secondary_broker_pct")


class TransactionListSerializer(serializers.ModelSerializer):
    my_role = serializers.SerializerMethodField()
    pending_invites_count = serializers.SerializerMethodField()
    required_next_action = serializers.SerializerMethodField()

    class Meta:
        model = Transaction
        fields = (
            "id",
            "type",
            "status",
            "title",
            "property_description",
            "purchase_price",
            "earnest_deposit",
            "due_diligence_end_date",
            "estimated_closing_date",
            "depositor_name",
            "property_address",
            "stage",
            "stage_updated_at",
            "updated_at",
            "my_role",
            "pending_invites_count",
            "required_next_action",
        )

    def get_my_role(self, obj: Transaction) -> str | None:
        user: User = self.context.get("request").user
        participation = obj.participants.filter(user=user).first()
        return participation.role if participation else None

    def get_pending_invites_count(self, obj: Transaction) -> int:
        return obj.invitations.filter(status=InvitationStatus.PENDING).count()

    def get_required_next_action(self, obj: Transaction) -> str | None:
        roles = set(obj.participants.values_list("role", flat=True))
        accepted_roles = set(obj.participants.filter(joined_at__isnull=False).values_list("role", flat=True))
        if obj.type == TransactionType.DOUBLE_BROKER_SPLIT:
            if ParticipantRole.BROKER_SECONDARY not in accepted_roles:
                return "Waiting for secondary broker"
            if ParticipantRole.BUYER in roles and ParticipantRole.SELLER not in roles:
                return "Secondary broker must invite seller"
            if ParticipantRole.SELLER in roles and ParticipantRole.BUYER not in roles:
                return "Secondary broker must invite buyer"
        return None


class TransactionEventSerializer(serializers.ModelSerializer):
    actor_email = serializers.SerializerMethodField()

    class Meta:
        model = TransactionEvent
        fields = ("type", "actor", "actor_email", "data", "created_at")

    def get_actor_email(self, obj: TransactionEvent) -> str | None:
        return getattr(obj.actor, "email", None)


class TransactionDetailSerializer(serializers.ModelSerializer):
    participants = serializers.SerializerMethodField()
    invitations = serializers.SerializerMethodField()
    details = serializers.SerializerMethodField()
    commission_split = CommissionSplitSerializer(read_only=True)
    events = TransactionEventSerializer(many=True, read_only=True)

    class Meta:
        model = Transaction
        fields = (
            "id",
            "type",
            "status",
            "stage",
            "stage_updated_at",
            "title",
            "property_description",
            "purchase_price",
            "earnest_deposit",
            "due_diligence_end_date",
            "estimated_closing_date",
            "depositor_name",
            "property_address",
            "created_at",
            "updated_at",
            "participants",
            "invitations",
            "details",
            "commission_split",
            "events",
        )

    def get_participants(self, obj: Transaction) -> list[dict[str, Any]]:
        return [
            {
                "role": participant.role,
                "invited_email": participant.invited_email,
                "user": participant.user_id,
                "joined_at": participant.joined_at,
            }
            for participant in obj.participants.all()
        ]

    def get_invitations(self, obj: Transaction) -> list[dict[str, Any]]:
        return [
            {
                "participant_role": invite.participant.role,
                "status": invite.status,
                "expires_at": invite.expires_at,
            }
            for invite in obj.invitations.all()
        ]

    def get_details(self, obj: Transaction) -> Dict[str, Any]:
        try:
            return obj.details.data
        except TransactionDetails.DoesNotExist:
            return {}


class TransactionCreateSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=TransactionType.choices)
    title = serializers.CharField(max_length=200)
    property_description = serializers.CharField()
    purchase_price = serializers.DecimalField(max_digits=14, decimal_places=2)
    earnest_deposit = serializers.DecimalField(max_digits=14, decimal_places=2)
    due_diligence_end_date = serializers.DateField()
    estimated_closing_date = serializers.DateField()
    depositor_name = serializers.CharField(max_length=200, required=False, allow_null=True, allow_blank=True)
    property_address = serializers.CharField(max_length=255, required=False, allow_blank=True)
    payload = serializers.DictField()

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        tx_type = attrs.get("type")
        payload: Dict[str, Any] = attrs.get("payload") or {}
        if attrs["earnest_deposit"] > attrs["purchase_price"]:
            raise serializers.ValidationError(
                {"earnest_deposit": "Earnest deposit cannot exceed purchase price."}
            )

        if attrs["estimated_closing_date"] <= attrs["due_diligence_end_date"]:
            raise serializers.ValidationError(
                {"estimated_closing_date": "Estimated closing must be after due diligence end date."}
            )

        if tx_type == TransactionType.SINGLE_BROKER_SALE:
            for field in ("buyer_email", "seller_email"):
                if not payload.get(field):
                    raise serializers.ValidationError({"payload": f"{field} is required"})
        elif tx_type == TransactionType.DOUBLE_BROKER_SPLIT:
            for field in ("known_party_role", "known_party_email", "secondary_broker_email"):
                if not payload.get(field):
                    raise serializers.ValidationError({"payload": f"{field} is required"})
        return attrs

    def core_fields(self) -> Dict[str, Any]:
        allowed_fields = [
            "title",
            "property_description",
            "purchase_price",
            "earnest_deposit",
            "due_diligence_end_date",
            "estimated_closing_date",
            "depositor_name",
            "property_address",
        ]
        return {field: self.validated_data[field] for field in allowed_fields if field in self.validated_data}


class AcceptInvitationSerializer(serializers.Serializer):
    token = serializers.CharField()


class InviteCounterpartySerializer(serializers.Serializer):
    counterparty_email = serializers.EmailField()
