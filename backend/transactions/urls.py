from django.urls import path

from .views import AcceptInvitationView, InviteCounterpartyView, TransactionDetailView, TransactionListCreateView

urlpatterns = [
    path("transactions/", TransactionListCreateView.as_view(), name="transaction-list"),
    path("transactions/<uuid:id>/", TransactionDetailView.as_view(), name="transaction-detail"),
    path(
        "transactions/<uuid:id>/invite-counterparty/",
        InviteCounterpartyView.as_view(),
        name="transaction-invite-counterparty",
    ),
    path("invitations/<str:token>/accept/", AcceptInvitationView.as_view(), name="accept-invitation"),
]
