from rest_framework import serializers
from decimal import Decimal
from .models import Wallet, Transaction


class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = ['id', 'user_id', 'balance', 'is_admin', 'created_at', 'updated_at']
        read_only_fields = ['id', 'balance', 'created_at', 'updated_at']


class TransactionSerializer(serializers.ModelSerializer):
    from_wallet_id = serializers.IntegerField(required=True)
    to_wallet_id = serializers.IntegerField(required=True)
    amount = serializers.DecimalField(max_digits=20, decimal_places=2, min_value=Decimal('0.01'))

    class Meta:
        model = Transaction
        fields = ['id', 'from_wallet_id', 'to_wallet_id', 'amount', 'fee', 'status', 'created_at', 'updated_at']
        read_only_fields = ['id', 'fee', 'status', 'created_at', 'updated_at']


class TransferRequestSerializer(serializers.Serializer):
    from_wallet_id = serializers.IntegerField(required=True)
    to_wallet_id = serializers.IntegerField(required=True)
    amount = serializers.DecimalField(max_digits=20, decimal_places=2, min_value=Decimal('0.01'))

    def validate(self, attrs):
        if attrs['from_wallet_id'] == attrs['to_wallet_id']:
            raise serializers.ValidationError("Cannot transfer to the same wallet")
        return attrs

