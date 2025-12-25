import time
from celery import shared_task
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=3)
def send_notification_task(self, transaction_id, to_wallet_id, amount):
    try:
        logger.info(f"Sending notification for transaction {transaction_id} to wallet {to_wallet_id}, amount: {amount}")
        
        # Имитация долгого запроса
        time.sleep(5)
        
        # Симуляция случайной ошибки (для тестирования retry)
        # В реальности здесь был бы запрос к Telegram API
        import random
        if random.random() < 0.3:  # 30% вероятность ошибки для демонстрации
            raise Exception("Simulated notification error")
        
        logger.info(f"Notification sent successfully for transaction {transaction_id}")
        return {
            'status': 'success',
            'transaction_id': transaction_id,
            'to_wallet_id': to_wallet_id,
            'amount': amount
        }
    
    except Exception as exc:
        logger.error(f"Error sending notification for transaction {transaction_id}: {exc}")
        
        # Проверяем, не превышен ли лимит попыток
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying notification for transaction {transaction_id}. Attempt {self.request.retries + 1}/{self.max_retries}")
            # Перезапускаем задачу через 3 секунды
            raise self.retry(exc=exc, countdown=3)
        else:
            logger.error(f"Max retries reached for transaction {transaction_id}. Notification failed.")
            raise exc

