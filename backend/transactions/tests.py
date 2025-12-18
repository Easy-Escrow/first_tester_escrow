from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from .models import CommissionSplit, ParticipantRole, Transaction, TransactionInvitation, TransactionType

User = get_user_model()


class TransactionServiceTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.broker = User.objects.create_user(email="broker@example.com", password="pass", is_broker=True)
        self.other_user = User.objects.create_user(email="user@example.com", password="pass", is_broker=False)
        self.client.force_authenticate(self.broker)

    def test_broker_can_create_single_broker_sale(self):
        response = self.client.post(
            reverse("transaction-list"),
            {
                "type": TransactionType.SINGLE_BROKER_SALE,
                "payload": {"buyer_email": "buyer@example.com", "seller_email": "seller@example.com"},
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        transaction = Transaction.objects.get()
        self.assertEqual(transaction.participants.count(), 3)
        self.assertEqual(TransactionInvitation.objects.count(), 2)

    def test_non_broker_cannot_create_transaction(self):
        self.client.force_authenticate(self.other_user)
        response = self.client.post(
            reverse("transaction-list"),
            {
                "type": TransactionType.SINGLE_BROKER_SALE,
                "payload": {"buyer_email": "buyer@example.com", "seller_email": "seller@example.com"},
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_double_broker_creation_sets_split(self):
        response = self.client.post(
            reverse("transaction-list"),
            {
                "type": TransactionType.DOUBLE_BROKER_SPLIT,
                "payload": {
                    "known_party_role": ParticipantRole.BUYER,
                    "known_party_email": "buyer@example.com",
                    "secondary_broker_email": "second@example.com",
                    "commission_split": {"primary_broker_pct": 70, "secondary_broker_pct": 30},
                },
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        transaction = Transaction.objects.get()
        split = CommissionSplit.objects.get(transaction=transaction)
        self.assertEqual(split.primary_broker_pct, 70)
        self.assertEqual(split.secondary_broker_pct, 30)
        self.assertEqual(TransactionInvitation.objects.count(), 2)

    def test_secondary_broker_invites_counterparty(self):
        # create double broker transaction
        self.client.post(
            reverse("transaction-list"),
            {
                "type": TransactionType.DOUBLE_BROKER_SPLIT,
                "payload": {
                    "known_party_role": ParticipantRole.BUYER,
                    "known_party_email": "buyer@example.com",
                    "secondary_broker_email": "second@example.com",
                },
            },
            format="json",
        )
        transaction = Transaction.objects.get()
        secondary_invite = TransactionInvitation.objects.get(participant__role=ParticipantRole.BROKER_SECONDARY)
        secondary_user = User.objects.create_user(email="second@example.com", password="pass", is_broker=True)
        self.client.force_authenticate(secondary_user)
        self.client.post(reverse("accept-invitation", kwargs={"token": secondary_invite.token}))
        response = self.client.post(
            reverse("transaction-invite-counterparty", kwargs={"id": transaction.id}),
            {"counterparty_email": "seller@example.com"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(transaction.participants.filter(role=ParticipantRole.SELLER).exists())

    def test_accept_invitation_requires_broker_for_secondary(self):
        self.client.post(
            reverse("transaction-list"),
            {
                "type": TransactionType.DOUBLE_BROKER_SPLIT,
                "payload": {
                    "known_party_role": ParticipantRole.BUYER,
                    "known_party_email": "buyer@example.com",
                    "secondary_broker_email": "second@example.com",
                },
            },
            format="json",
        )
        secondary_invite = TransactionInvitation.objects.get(participant__role=ParticipantRole.BROKER_SECONDARY)
        self.client.force_authenticate(self.other_user)
        response = self.client.post(reverse("accept-invitation", kwargs={"token": secondary_invite.token}))
        self.assertEqual(response.status_code, 403)

    def test_invited_user_can_view_transaction_list(self):
        self.client.post(
            reverse("transaction-list"),
            {
                "type": TransactionType.SINGLE_BROKER_SALE,
                "payload": {"buyer_email": "buyer@example.com", "seller_email": "seller@example.com"},
            },
            format="json",
        )

        invited_user = User.objects.create_user(email="buyer@example.com", password="pass", is_broker=False)
        invited_client = APIClient()
        invited_client.force_authenticate(invited_user)

        response = invited_client.get(reverse("transaction-list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertIsNone(response.data[0].get("my_role"))
