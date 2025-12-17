from django.conf import settings
from django.db import models


class Transaction(models.Model):
    CURRENCY_USD = "usd"
    CURRENCY_MXN = "mxn"
    CURRENCY_CHOICES = (
        (CURRENCY_USD, "USD"),
        (CURRENCY_MXN, "MXN"),
    )

    TYPE_SINGLE = "single_broker_sale"
    TYPE_DOUBLE = "double_broker_commission_split"
    TYPE_DUE_DILIGENCE = "due_diligence"
    TYPE_HIDDEN_DEFECTS = "hidden_defects"

    TYPE_CHOICES = (
        (TYPE_SINGLE, "Single broker sale"),
        (TYPE_DOUBLE, "Double broker commission split"),
        (TYPE_DUE_DILIGENCE, "Due diligence"),
        (TYPE_HIDDEN_DEFECTS, "Hidden defects"),
    )

    ROLE_BUYER = "buyer"
    ROLE_SELLER = "seller"
    ROLE_PRIMARY_BROKER = "primary_broker"
    ROLE_SECONDARY_BROKER = "secondary_broker"
    ROLE_PARTICIPANT = "participant"

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="transactions_created", on_delete=models.CASCADE
    )
    name = models.CharField(max_length=255)
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES)
    transaction_type = models.CharField(max_length=64, choices=TYPE_CHOICES)
    property_type = models.CharField(max_length=255)
    purchase_price = models.DecimalField(max_digits=14, decimal_places=2)
    earnest_deposit = models.DecimalField(max_digits=14, decimal_places=2)
    due_diligence_end_date = models.DateField()
    estimated_closing_date = models.DateField()
    initiating_party_role = models.CharField(
        max_length=20,
        choices=((ROLE_BUYER, "Buyer"), (ROLE_SELLER, "Seller")),
        null=True,
        blank=True,
        help_text="For double broker transactions, records whether the original broker knows the buyer or seller.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:  # pragma: no cover - repr helper
        return f"{self.name} ({self.get_transaction_type_display()})"

    def pending_counterparty_role(self):
        if self.transaction_type != self.TYPE_DOUBLE:
            return None
        buyer_invited = self.invitations.filter(role=self.ROLE_BUYER).exists()
        seller_invited = self.invitations.filter(role=self.ROLE_SELLER).exists()
        if buyer_invited and seller_invited:
            return None
        if not buyer_invited:
            return self.ROLE_BUYER
        if not seller_invited:
            return self.ROLE_SELLER
        return None


class TransactionInvitation(models.Model):
    STATUS_PENDING = "pending"
    STATUS_ACCEPTED = "accepted"
    STATUS_DECLINED = "declined"

    STATUS_CHOICES = (
        (STATUS_PENDING, "Pending"),
        (STATUS_ACCEPTED, "Accepted"),
        (STATUS_DECLINED, "Declined"),
    )

    ROLE_CHOICES = (
        (Transaction.ROLE_BUYER, "Buyer"),
        (Transaction.ROLE_SELLER, "Seller"),
        (Transaction.ROLE_PRIMARY_BROKER, "Primary broker"),
        (Transaction.ROLE_SECONDARY_BROKER, "Secondary broker"),
        (Transaction.ROLE_PARTICIPANT, "Participant"),
    )

    transaction = models.ForeignKey(
        Transaction, related_name="invitations", on_delete=models.CASCADE
    )
    email = models.EmailField()
    role = models.CharField(max_length=32, choices=ROLE_CHOICES)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="sent_invitations", on_delete=models.CASCADE
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("transaction", "email", "role")
        ordering = ["-created_at"]

    def __str__(self) -> str:  # pragma: no cover - repr helper
        return f"{self.email} invited as {self.role} for {self.transaction.name}"
