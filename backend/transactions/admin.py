from django.contrib import admin

from .models import Transaction, TransactionInvitation


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "transaction_type",
        "currency",
        "property_type",
        "purchase_price",
        "earnest_deposit",
        "created_by",
        "created_at",
    )
    search_fields = ("name", "created_by__email")
    list_filter = ("transaction_type", "currency")


@admin.register(TransactionInvitation)
class TransactionInvitationAdmin(admin.ModelAdmin):
    list_display = ("transaction", "email", "role", "status", "invited_by", "created_at")
    search_fields = ("email", "transaction__name")
    list_filter = ("role", "status")
