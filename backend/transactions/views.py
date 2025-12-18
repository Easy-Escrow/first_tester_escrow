from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status, views
from rest_framework.response import Response

from accounts.models import User
from .models import ParticipantRole, Transaction
from .serializers import (
    AcceptInvitationSerializer,
    InviteCounterpartySerializer,
    TransactionCreateSerializer,
    TransactionDetailSerializer,
    TransactionListSerializer,
)
from .services import accept_invitation, create_transaction, invite_counterparty


class IsBroker(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_broker)


class TransactionQuerysetMixin:
    def get_queryset(self):
        user: User = self.request.user
        return (
            Transaction.objects.filter(participants__user=user)
            | Transaction.objects.filter(created_by=user)
        ).distinct().prefetch_related("participants", "invitations", "details", "commission_split")


class TransactionListCreateView(TransactionQuerysetMixin, generics.ListCreateAPIView):
    serializer_class = TransactionListSerializer

    def get_permissions(self):
        if self.request.method.lower() == "post":
            return [IsBroker()]
        return super().get_permissions()

    def get_serializer_class(self):
        if self.request.method.lower() == "post":
            return TransactionCreateSerializer
        return super().get_serializer_class()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tx = create_transaction(created_by=request.user, type=serializer.validated_data["type"], payload=serializer.validated_data.get("payload", {}))
        output = TransactionDetailSerializer(tx, context={"request": request}).data
        return Response(output, status=status.HTTP_201_CREATED)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True, context={"request": request})
        return Response(serializer.data)


class TransactionDetailView(TransactionQuerysetMixin, generics.RetrieveAPIView):
    serializer_class = TransactionDetailSerializer
    lookup_field = "id"

    def get_queryset(self):
        return super().get_queryset().prefetch_related("participants", "invitations", "details", "commission_split")


class InviteCounterpartyView(views.APIView):
    def post(self, request, *args, **kwargs):
        transaction_id = kwargs.get("id")
        transaction_obj = get_object_or_404(Transaction, id=transaction_id)
        serializer = InviteCounterpartySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        participant, _ = invite_counterparty(
            transaction_obj=transaction_obj,
            acting_user=request.user,
            counterparty_email=serializer.validated_data["counterparty_email"],
        )
        return Response(
            {
                "participant": participant.role,
                "invited_email": participant.invited_email,
            },
            status=status.HTTP_201_CREATED,
        )


class AcceptInvitationView(views.APIView):
    def post(self, request, token: str, *args, **kwargs):
        serializer = AcceptInvitationSerializer(data={"token": token})
        serializer.is_valid(raise_exception=True)
        transaction_obj = accept_invitation(token=token, user=request.user)
        data = TransactionDetailSerializer(transaction_obj, context={"request": request}).data
        return Response(data)
