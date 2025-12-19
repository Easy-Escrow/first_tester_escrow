import secrets
from datetime import timedelta
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class TransactionType(models.TextChoices):
    SINGLE_BROKER_SALE = "single_broker_sale", "Single Broker Sale"
    DOUBLE_BROKER_SPLIT = "double_broker_split", "Double Broker Split"
    DUE_DILIGENCE = "due_diligence", "Due Diligence"
    HIDDEN_DEFECTS = "hidden_defects", "Hidden Defects"


class TransactionStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    INVITING = "inviting", "Inviting"
    ACTIVE = "active", "Active"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"


class ParticipantRole(models.TextChoices):
    BROKER_PRIMARY = "broker_primary", "Primary Broker"
    BROKER_SECONDARY = "broker_secondary", "Secondary Broker"
    BUYER = "buyer", "Buyer"
    SELLER = "seller", "Seller"
    OTHER = "other", "Other"


class InvitationStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    ACCEPTED = "accepted", "Accepted"
    EXPIRED = "expired", "Expired"
    REVOKED = "revoked", "Revoked"


class Transaction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="transactions_created")
    type = models.CharField(max_length=50, choices=TransactionType.choices)
    status = models.CharField(max_length=20, choices=TransactionStatus.choices, default=TransactionStatus.DRAFT)
    title = models.CharField(max_length=200)
    property_description = models.TextField()
    purchase_price = models.DecimalField(max_digits=14, decimal_places=2)
    earnest_deposit = models.DecimalField(max_digits=14, decimal_places=2)
    due_diligence_end_date = models.DateField()
    estimated_closing_date = models.DateField()
    depositor_name = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Only required if depositor is not the purchaser",
    )
    property_address = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:  # pragma: no cover - representation helper
        return f"{self.get_type_display()} ({self.id})"


class TransactionParticipant(models.Model):
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, related_name="participants")
    role = models.CharField(max_length=30, choices=ParticipantRole.choices)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="transaction_participations")
    invited_email = models.EmailField()
    invited_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="transaction_invites_sent")
    joined_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["transaction", "role"], name="unique_transaction_role"),
        ]

    def __str__(self) -> str:  # pragma: no cover - representation helper
        return f"{self.role} - {self.invited_email}"


class TransactionInvitation(models.Model):
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, related_name="invitations")
    participant = models.OneToOneField(TransactionParticipant, on_delete=models.CASCADE)
    token = models.CharField(max_length=128, unique=True, default=secrets.token_urlsafe)
    status = models.CharField(max_length=20, choices=InvitationStatus.choices, default=InvitationStatus.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def is_expired(self) -> bool:
        return timezone.now() > self.expires_at

    def __str__(self) -> str:  # pragma: no cover
        return f"Invite {self.token} for {self.participant}"


class TransactionDetails(models.Model):
    transaction = models.OneToOneField(Transaction, on_delete=models.CASCADE, related_name="details")
    data = models.JSONField(default=dict, blank=True)


class CommissionSplit(models.Model):
    transaction = models.OneToOneField(Transaction, on_delete=models.CASCADE, related_name="commission_split")
    primary_broker_pct = models.DecimalField(max_digits=5, decimal_places=2)
    secondary_broker_pct = models.DecimalField(max_digits=5, decimal_places=2)

    def clean(self) -> None:
        total = (self.primary_broker_pct or 0) + (self.secondary_broker_pct or 0)
        if total != 100:
            raise ValidationError("Commission split must total 100%")

    def full_clean(self, *args, **kwargs):
        super().full_clean(*args, **kwargs)
        self.clean()

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.primary_broker_pct}/{self.secondary_broker_pct} for {self.transaction_id}"


def default_invitation_expiry(days: int = 7) -> timezone.datetime:
    return timezone.now() + timedelta(days=days)
