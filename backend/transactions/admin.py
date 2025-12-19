from django.contrib import admin

from .models import (
    CommissionSplit,
    Transaction,
    TransactionDetails,
    TransactionInvitation,
    TransactionParticipant,
)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("id", "type", "status", "created_by", "created_at")
    search_fields = ("id", "title", "property_address")
    list_filter = ("type", "status")


@admin.register(TransactionParticipant)
class TransactionParticipantAdmin(admin.ModelAdmin):
    list_display = ("transaction", "role", "invited_email", "user", "joined_at")
    list_filter = ("role",)


@admin.register(TransactionInvitation)
class TransactionInvitationAdmin(admin.ModelAdmin):
    list_display = ("transaction", "participant", "status", "expires_at")
    list_filter = ("status",)
    search_fields = ("token",)


@admin.register(TransactionDetails)
class TransactionDetailsAdmin(admin.ModelAdmin):
    list_display = ("transaction",)


@admin.register(CommissionSplit)
class CommissionSplitAdmin(admin.ModelAdmin):
    list_display = ("transaction", "primary_broker_pct", "secondary_broker_pct")
