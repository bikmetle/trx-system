from django.contrib import admin
from .models import Wallet, Transaction


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ['id', 'user_id', 'balance', 'is_admin', 'created_at']
    list_filter = ['is_admin', 'created_at']
    search_fields = ['user_id']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['id', 'from_wallet', 'to_wallet', 'amount', 'fee', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['from_wallet__user_id', 'to_wallet__user_id']
    readonly_fields = ['created_at', 'updated_at']

