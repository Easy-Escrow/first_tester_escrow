from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from .models import (
    CommissionSplit,
    ParticipantRole,
    Transaction,
    TransactionEventType,
    TransactionInvitation,
    TransactionStage,
    TransactionType,
)

User = get_user_model()


class TransactionServiceTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.broker = User.objects.create_user(email="broker@example.com", password="pass", is_broker=True)
        self.other_user = User.objects.create_user(email="user@example.com", password="pass", is_broker=False)
        self.client.force_authenticate(self.broker)

    def _core_fields(self, overrides: dict | None = None):
        base = {
            "title": "Test Transaction",
            "property_description": "A great property",
            "purchase_price": "100000.00",
            "earnest_deposit": "10000.00",
            "due_diligence_end_date": "2024-01-01",
            "estimated_closing_date": "2024-02-01",
        }
        if overrides:
            base.update(overrides)
        return base

    def test_broker_can_create_single_broker_sale(self):
        response = self.client.post(
            reverse("transaction-list"),
            {
                **self._core_fields(),
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
                **self._core_fields(),
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
                **self._core_fields(),
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
                **self._core_fields(),
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
                **self._core_fields(),
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
                **self._core_fields(),
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

    def test_required_core_fields_missing(self):
        response = self.client.post(
            reverse("transaction-list"),
            {
                "type": TransactionType.SINGLE_BROKER_SALE,
                "payload": {"buyer_email": "buyer@example.com", "seller_email": "seller@example.com"},
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("title", response.data)

    def test_validation_for_earnest_exceeds_purchase_price(self):
        response = self.client.post(
            reverse("transaction-list"),
            {
                **self._core_fields({"earnest_deposit": "200000.00"}),
                "type": TransactionType.SINGLE_BROKER_SALE,
                "payload": {"buyer_email": "buyer@example.com", "seller_email": "seller@example.com"},
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("earnest_deposit", response.data)

    def test_validation_for_invalid_dates(self):
        response = self.client.post(
            reverse("transaction-list"),
            {
                **self._core_fields({"estimated_closing_date": "2023-12-31"}),
                "type": TransactionType.SINGLE_BROKER_SALE,
                "payload": {"buyer_email": "buyer@example.com", "seller_email": "seller@example.com"},
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("estimated_closing_date", response.data)

    def test_optional_depositor_name_persists(self):
        response = self.client.post(
            reverse("transaction-list"),
            {
                **self._core_fields({"depositor_name": "Escrow Corp"}),
                "type": TransactionType.SINGLE_BROKER_SALE,
                "payload": {"buyer_email": "buyer@example.com", "seller_email": "seller@example.com"},
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        transaction = Transaction.objects.get()
        self.assertEqual(transaction.depositor_name, "Escrow Corp")

    def test_single_broker_stage_progression_and_events(self):
        self.client.post(
            reverse("transaction-list"),
            {
                **self._core_fields(),
                "type": TransactionType.SINGLE_BROKER_SALE,
                "payload": {"buyer_email": "buyer@example.com", "seller_email": "seller@example.com"},
            },
            format="json",
        )
        transaction = Transaction.objects.get()
        self.assertEqual(transaction.stage, TransactionStage.PENDING_INVITATIONS)

        buyer_invite = TransactionInvitation.objects.get(participant__role=ParticipantRole.BUYER)
        seller_invite = TransactionInvitation.objects.get(participant__role=ParticipantRole.SELLER)

        buyer_user = User.objects.create_user(email="buyer@example.com", password="pass")
        seller_user = User.objects.create_user(email="seller@example.com", password="pass")

        buyer_client = APIClient()
        buyer_client.force_authenticate(buyer_user)
        buyer_client.post(reverse("accept-invitation", kwargs={"token": buyer_invite.token}))
        transaction.refresh_from_db()
        self.assertEqual(transaction.stage, TransactionStage.PENDING_INVITATIONS)

        seller_client = APIClient()
        seller_client.force_authenticate(seller_user)
        seller_client.post(reverse("accept-invitation", kwargs={"token": seller_invite.token}))
        transaction.refresh_from_db()
        self.assertEqual(transaction.stage, TransactionStage.PENDING_USER_INFORMATION)
        self.assertEqual(
            transaction.events.filter(type=TransactionEventType.STAGE_CHANGED).count(),
            1,
        )

    def test_double_broker_stage_progression_with_counterparty(self):
        self.client.post(
            reverse("transaction-list"),
            {
                **self._core_fields(),
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
        self.assertEqual(transaction.stage, TransactionStage.PENDING_INVITATIONS)

        buyer_invite = TransactionInvitation.objects.get(participant__role=ParticipantRole.BUYER)
        secondary_invite = TransactionInvitation.objects.get(participant__role=ParticipantRole.BROKER_SECONDARY)

        buyer_user = User.objects.create_user(email="buyer@example.com", password="pass")
        secondary_user = User.objects.create_user(email="second@example.com", password="pass", is_broker=True)

        buyer_client = APIClient()
        buyer_client.force_authenticate(buyer_user)
        buyer_client.post(reverse("accept-invitation", kwargs={"token": buyer_invite.token}))
        transaction.refresh_from_db()
        self.assertEqual(transaction.stage, TransactionStage.PENDING_INVITATIONS)

        secondary_client = APIClient()
        secondary_client.force_authenticate(secondary_user)
        secondary_client.post(reverse("accept-invitation", kwargs={"token": secondary_invite.token}))
        transaction.refresh_from_db()
        self.assertEqual(transaction.stage, TransactionStage.PENDING_INVITATIONS)

        secondary_client.post(
            reverse("transaction-invite-counterparty", kwargs={"id": transaction.id}),
            {"counterparty_email": "seller@example.com"},
            format="json",
        )
        counterparty_invite = TransactionInvitation.objects.get(participant__role=ParticipantRole.SELLER)
        transaction.refresh_from_db()
        self.assertEqual(transaction.stage, TransactionStage.PENDING_INVITATIONS)

        seller_user = User.objects.create_user(email="seller@example.com", password="pass")
        seller_client = APIClient()
        seller_client.force_authenticate(seller_user)
        seller_client.post(reverse("accept-invitation", kwargs={"token": counterparty_invite.token}))

        transaction.refresh_from_db()
        self.assertEqual(transaction.stage, TransactionStage.PENDING_USER_INFORMATION)
        self.assertGreaterEqual(
            transaction.events.filter(type=TransactionEventType.INVITATION_SENT).count(),
            3,
        )
        self.assertGreaterEqual(
            transaction.events.filter(type=TransactionEventType.INVITATION_ACCEPTED).count(),
            3,
        )
        self.assertEqual(
            transaction.events.filter(type=TransactionEventType.STAGE_CHANGED).count(),
            1,
        )
