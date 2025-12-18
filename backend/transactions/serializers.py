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
            "property_address",
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


class TransactionDetailSerializer(serializers.ModelSerializer):
    participants = serializers.SerializerMethodField()
    invitations = serializers.SerializerMethodField()
    details = serializers.SerializerMethodField()
    commission_split = CommissionSplitSerializer(read_only=True)

    class Meta:
        model = Transaction
        fields = (
            "id",
            "type",
            "status",
            "title",
            "property_address",
            "created_at",
            "updated_at",
            "participants",
            "invitations",
            "details",
            "commission_split",
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
    payload = serializers.DictField()

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        tx_type = attrs.get("type")
        payload: Dict[str, Any] = attrs.get("payload") or {}
        if tx_type == TransactionType.SINGLE_BROKER_SALE:
            for field in ("buyer_email", "seller_email"):
                if not payload.get(field):
                    raise serializers.ValidationError({"payload": f"{field} is required"})
        elif tx_type == TransactionType.DOUBLE_BROKER_SPLIT:
            for field in ("known_party_role", "known_party_email", "secondary_broker_email"):
                if not payload.get(field):
                    raise serializers.ValidationError({"payload": f"{field} is required"})
        return attrs


class AcceptInvitationSerializer(serializers.Serializer):
    token = serializers.CharField()


class InviteCounterpartySerializer(serializers.Serializer):
    counterparty_email = serializers.EmailField()
