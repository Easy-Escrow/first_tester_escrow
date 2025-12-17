from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers

from .models import Transaction, TransactionInvitation

User = get_user_model()


class TransactionInvitationSerializer(serializers.ModelSerializer):
    invited_by = serializers.EmailField(source="invited_by.email", read_only=True)
    role_label = serializers.CharField(source="get_role_display", read_only=True)

    class Meta:
        model = TransactionInvitation
        fields = [
            "id",
            "email",
            "role",
            "role_label",
            "status",
            "invited_by",
            "created_at",
        ]
        read_only_fields = fields


class TransactionSerializer(serializers.ModelSerializer):
    invitations = TransactionInvitationSerializer(many=True, read_only=True)
    created_by_email = serializers.EmailField(source="created_by.email", read_only=True)
    pending_counterparty_role = serializers.SerializerMethodField()
    can_invite_counterparty = serializers.SerializerMethodField()

    class Meta:
        model = Transaction
        fields = [
            "id",
            "name",
            "currency",
            "transaction_type",
            "property_type",
            "purchase_price",
            "earnest_deposit",
            "due_diligence_end_date",
            "estimated_closing_date",
            "created_at",
            "created_by_email",
            "pending_counterparty_role",
            "can_invite_counterparty",
            "invitations",
        ]

    def get_pending_counterparty_role(self, obj: Transaction):
        return obj.pending_counterparty_role()

    def get_can_invite_counterparty(self, obj: Transaction):
        user = self.context.get("request").user
        if obj.transaction_type != Transaction.TYPE_DOUBLE:
            return False
        if obj.pending_counterparty_role() is None:
            return False
        return obj.invitations.filter(
            role=Transaction.ROLE_SECONDARY_BROKER, email=user.email
        ).exists()


class TransactionSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = [
            "id",
            "name",
            "transaction_type",
            "currency",
            "property_type",
            "purchase_price",
            "earnest_deposit",
            "due_diligence_end_date",
            "estimated_closing_date",
        ]
        read_only_fields = fields


class TransactionCreateSerializer(serializers.ModelSerializer):
    buyer_email = serializers.EmailField(write_only=True, required=False)
    seller_email = serializers.EmailField(write_only=True, required=False)
    initiating_party_email = serializers.EmailField(write_only=True, required=False)
    initiating_party_role = serializers.ChoiceField(
        choices=((Transaction.ROLE_BUYER, "Buyer"), (Transaction.ROLE_SELLER, "Seller")),
        required=False,
    )
    secondary_broker_email = serializers.EmailField(write_only=True, required=False)
    participant_emails = serializers.ListField(
        child=serializers.EmailField(), write_only=True, required=False, allow_empty=True
    )

    class Meta:
        model = Transaction
        fields = [
            "id",
            "name",
            "currency",
            "transaction_type",
            "property_type",
            "purchase_price",
            "earnest_deposit",
            "due_diligence_end_date",
            "estimated_closing_date",
            "buyer_email",
            "seller_email",
            "initiating_party_email",
            "initiating_party_role",
            "secondary_broker_email",
            "participant_emails",
        ]

    def validate(self, attrs):
        transaction_type = attrs.get("transaction_type")
        if transaction_type == Transaction.TYPE_SINGLE:
            if not attrs.get("buyer_email") or not attrs.get("seller_email"):
                raise serializers.ValidationError(
                    "Buyer and seller emails are required for a single broker sale."
                )
        elif transaction_type == Transaction.TYPE_DOUBLE:
            missing_fields = [
                field
                for field in [
                    "initiating_party_email",
                    "initiating_party_role",
                    "secondary_broker_email",
                ]
                if not attrs.get(field)
            ]
            if missing_fields:
                raise serializers.ValidationError(
                    "Initiating party email, initiating party role, and secondary broker email are required for a double broker transaction."
                )
        return attrs

    def create(self, validated_data):
        user = self.context.get("request").user
        buyer_email = validated_data.pop("buyer_email", None)
        seller_email = validated_data.pop("seller_email", None)
        initiating_party_email = validated_data.pop("initiating_party_email", None)
        initiating_party_role = validated_data.pop("initiating_party_role", None)
        secondary_broker_email = validated_data.pop("secondary_broker_email", None)
        participant_emails = validated_data.pop("participant_emails", [])

        with transaction.atomic():
            tx = Transaction.objects.create(
                created_by=user, initiating_party_role=initiating_party_role, **validated_data
            )

            invitations_to_create: list[TransactionInvitation] = []

            if tx.transaction_type == Transaction.TYPE_SINGLE:
                invitations_to_create.append(
                    TransactionInvitation(
                        transaction=tx,
                        email=buyer_email,
                        role=Transaction.ROLE_BUYER,
                        invited_by=user,
                    )
                )
                invitations_to_create.append(
                    TransactionInvitation(
                        transaction=tx,
                        email=seller_email,
                        role=Transaction.ROLE_SELLER,
                        invited_by=user,
                    )
                )
            elif tx.transaction_type == Transaction.TYPE_DOUBLE:
                counterparty_role = None
                if initiating_party_role == Transaction.ROLE_BUYER:
                    counterparty_role = Transaction.ROLE_SELLER
                elif initiating_party_role == Transaction.ROLE_SELLER:
                    counterparty_role = Transaction.ROLE_BUYER

                invitations_to_create.append(
                    TransactionInvitation(
                        transaction=tx,
                        email=initiating_party_email,
                        role=initiating_party_role,
                        invited_by=user,
                    )
                )
                invitations_to_create.append(
                    TransactionInvitation(
                        transaction=tx,
                        email=secondary_broker_email,
                        role=Transaction.ROLE_SECONDARY_BROKER,
                        invited_by=user,
                    )
                )

                if counterparty_role is None:
                    raise serializers.ValidationError("Invalid initiating party role supplied.")
            # Additional participants for any transaction type
            for participant_email in participant_emails:
                invitations_to_create.append(
                    TransactionInvitation(
                        transaction=tx,
                        email=participant_email,
                        role=Transaction.ROLE_PARTICIPANT,
                        invited_by=user,
                    )
                )

            TransactionInvitation.objects.bulk_create(invitations_to_create)

        return tx


class InvitationWithTransactionSerializer(TransactionInvitationSerializer):
    transaction = TransactionSummarySerializer(read_only=True)

    class Meta(TransactionInvitationSerializer.Meta):
        fields = TransactionInvitationSerializer.Meta.fields + ["transaction"]
