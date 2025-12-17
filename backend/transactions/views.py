from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Transaction, TransactionInvitation
from .serializers import (
    InvitationWithTransactionSerializer,
    TransactionCreateSerializer,
    TransactionSerializer,
)


class TransactionListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return (
            Transaction.objects.filter(
                Q(created_by=user) | Q(invitations__email=user.email)
            )
            .prefetch_related("invitations")
            .distinct()
        )

    def get_serializer_class(self):
        if self.request.method == "POST":
            return TransactionCreateSerializer
        return TransactionSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context

    def perform_create(self, serializer):
        if not self.request.user.is_broker:
            raise PermissionDenied("Only brokers can create transactions.")
        serializer.save()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        output = TransactionSerializer(serializer.instance, context=self.get_serializer_context()).data
        return Response(output, status=status.HTTP_201_CREATED, headers=headers)


class InvitationListView(generics.ListAPIView):
    serializer_class = InvitationWithTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return TransactionInvitation.objects.filter(email=user.email).select_related(
            "transaction", "invited_by"
        )


class CounterpartyInviteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        transaction = get_object_or_404(Transaction, pk=pk)

        if transaction.transaction_type != Transaction.TYPE_DOUBLE:
            return Response(
                {"detail": "Counterparty invites only apply to double broker transactions."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not transaction.invitations.filter(
            role=Transaction.ROLE_SECONDARY_BROKER, email=request.user.email
        ).exists():
            return Response(
                {"detail": "Only the secondary broker can invite the counterparty."},
                status=status.HTTP_403_FORBIDDEN,
            )

        pending_role = transaction.pending_counterparty_role()
        if pending_role is None:
            return Response(
                {"detail": "Both parties are already invited."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        counterparty_email = request.data.get("email")
        if not counterparty_email:
            return Response(
                {"detail": "Email is required."}, status=status.HTTP_400_BAD_REQUEST
            )

        if transaction.invitations.filter(role=pending_role, email=counterparty_email).exists():
            return Response(
                {"detail": "This counterparty has already been invited."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        TransactionInvitation.objects.create(
            transaction=transaction,
            email=counterparty_email,
            role=pending_role,
            invited_by=request.user,
        )

        serializer = TransactionSerializer(
            transaction, context={"request": request}
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)
