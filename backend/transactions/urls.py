from django.urls import path

from .views import CounterpartyInviteView, InvitationListView, TransactionListCreateView

urlpatterns = [
    path("transactions/", TransactionListCreateView.as_view(), name="transactions-list-create"),
    path(
        "transactions/<int:pk>/invite-counterparty/",
        CounterpartyInviteView.as_view(),
        name="transactions-counterparty-invite",
    ),
    path("invitations/", InvitationListView.as_view(), name="transactions-invitations"),
]
