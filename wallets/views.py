from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db import transaction, DatabaseError, OperationalError
from django.db.models import F
from django.conf import settings
from decimal import Decimal
import logging
import re
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    retry_if_exception_message,
    retry_all,
    before_sleep_log,
    after_log,
)
from .models import Wallet, Transaction
from .serializers import TransferRequestSerializer, TransactionSerializer
from .tasks import send_notification_task

logger = logging.getLogger(__name__)


retry_on_deadlock = retry(
    retry=retry_all(
        retry_if_exception_type((DatabaseError, OperationalError)),
    ),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.1, min=0.1, max=1.0),  # Exponential backoff: 0.1s, 0.2s, 0.4s
    before_sleep=before_sleep_log(logger, logging.WARNING),
    after=after_log(logger, logging.ERROR),
    reraise=True,
)


@api_view(['POST'])
def transfer(request):
    serializer = TransferRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    from_wallet_id = serializer.validated_data['from_wallet_id']
    to_wallet_id = serializer.validated_data['to_wallet_id']
    amount = serializer.validated_data['amount']

    try:
        return _execute_transfer(from_wallet_id, to_wallet_id, amount)
    except (DatabaseError, OperationalError) as e:
        logger.error(f"Database error in transfer: {e}")
        return Response(
            {'error': 'Transaction conflict. Please try again.'},
            status=status.HTTP_409_CONFLICT
        )
    except Wallet.DoesNotExist as e:
        return Response(
            {'error': str(e) if str(e) else 'One or both wallets not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except ValueError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Unexpected error in transfer: {e}", exc_info=True)
        return Response(
            {'error': 'An unexpected error occurred'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@retry_on_deadlock
def _execute_transfer(from_wallet_id, to_wallet_id, amount):
    with transaction.atomic():
        wallets = {
            wallet.id: wallet
            for wallet in Wallet.objects.select_for_update().filter(
                id__in=[from_wallet_id, to_wallet_id]
            ).order_by('id')
        }
        
        if from_wallet_id not in wallets or to_wallet_id not in wallets:
            raise Wallet.DoesNotExist("One or both wallets not found")
        
        from_wallet = wallets[from_wallet_id]
        to_wallet = wallets[to_wallet_id]
        
        fee = Decimal('0.00')
        fee_threshold = Decimal(str(settings.TRANSACTION_FEE_THRESHOLD))
        if amount > fee_threshold:
            fee_percent = Decimal(str(settings.TRANSACTION_FEE_PERCENT))
            fee = amount * fee_percent

        total_debit = amount + fee

        if from_wallet.balance < total_debit:
            raise ValueError(
                f'Insufficient balance. Required: {total_debit}, Available: {from_wallet.balance}'
            )

        admin_wallet = None
        if fee > 0:
            admin_wallet = Wallet.objects.select_for_update().get(
                user_id=0,
                is_admin=True
            )

        transaction_obj = Transaction.objects.create(
            from_wallet=from_wallet,
            to_wallet=to_wallet,
            amount=amount,
            fee=fee,
            status='completed'
        )

        Wallet.objects.filter(id=from_wallet_id).update(
            balance=F('balance') - total_debit
        )
        
        Wallet.objects.filter(id=to_wallet_id).update(
            balance=F('balance') + amount
        )
        
        if fee > 0 and admin_wallet:
            Wallet.objects.filter(id=admin_wallet.id).update(
                balance=F('balance') + fee
            )

    send_notification_task.delay(
        transaction_id=transaction_obj.id,
        to_wallet_id=to_wallet_id,
        amount=str(amount)
    )

    transaction_serializer = TransactionSerializer(transaction_obj)
    return Response(transaction_serializer.data, status=status.HTTP_201_CREATED)





# если перечислять с админского?
# если перечислять на админский?
# админский кошелек должен быть создан при первом переводе?
