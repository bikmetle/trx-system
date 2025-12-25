from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal


class Wallet(models.Model):
    user_id = models.BigIntegerField(unique=True, db_index=True, help_text="ID пользователя")
    balance = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Баланс кошелька"
    )
    is_admin = models.BooleanField(default=False, help_text="Технический кошелек администратора")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'wallets'
        constraints = [
            models.CheckConstraint(
                check=models.Q(balance__gte=0),
                name='wallets_balance_non_negative'
            ),
        ]

    def __str__(self):
        return f"Wallet(user_id={self.user_id}, balance={self.balance}, is_admin={self.is_admin})"


class Transaction(models.Model):
    TRANSACTION_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    from_wallet = models.ForeignKey(
        Wallet,
        on_delete=models.PROTECT,
        related_name='outgoing_transactions',
        null=True,
        blank=True,
        help_text="Кошелек отправителя (null для пополнений)"
    )
    to_wallet = models.ForeignKey(
        Wallet,
        on_delete=models.PROTECT,
        related_name='incoming_transactions',
        help_text="Кошелек получателя"
    )
    amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Сумма перевода"
    )
    fee = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Комиссия системы"
    )
    status = models.CharField(
        max_length=20,
        choices=TRANSACTION_STATUS_CHOICES,
        default='pending',
        help_text="Статус транзакции"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'transactions'
        constraints = [
            models.CheckConstraint(
                check=models.Q(amount__gt=0),
                name='transactions_amount_positive'
            ),
            models.CheckConstraint(
                check=models.Q(fee__gte=0),
                name='transactions_fee_non_negative'
            ),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"Transaction(id={self.id}, from={self.from_wallet_id}, to={self.to_wallet_id}, amount={self.amount}, fee={self.fee})"

