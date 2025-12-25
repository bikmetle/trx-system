# Transaction System (TRX-SYS)

Система обработки транзакций с защитой от race condition и асинхронными уведомлениями.

## Технологии

- Python 3.8+
- Django 4.2
- Django REST Framework
- Celery 5.3
- Redis
- PostgreSQL

## Установка

1. Создайте виртуальное окружение:
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# или
.venv\Scripts\activate  # Windows
```

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

3. Создайте файл `.env` на основе `.env.example` и настройте параметры подключения к БД и Redis.

4. Выполните миграции:
```bash
python manage.py makemigrations
python manage.py migrate
```

5. Создайте суперпользователя (опционально):
```bash
python manage.py createsuperuser
```

## Запуск

### Запуск Django сервера:
```bash
python manage.py runserver
```

### Запуск Celery worker:
```bash
celery -A trx_system worker --loglevel=info
```

## API

### POST /api/transfer

Перевод средств между кошельками.

**Request Body:**
```json
{
    "from_wallet_id": 1,
    "to_wallet_id": 2,
    "amount": "1500.00"
}
```

**Response (201 Created):**
```json
{
    "id": 1,
    "from_wallet_id": 1,
    "to_wallet_id": 2,
    "amount": "1500.00",
    "fee": "150.00",
    "status": "completed",
    "created_at": "2024-01-01T12:00:00Z",
    "updated_at": "2024-01-01T12:00:00Z"
}
```

**Особенности:**
- Защита от race condition через `select_for_update()`
- Комиссия 10% при сумме > 1000
- Атомарность всех операций (списание, зачисление, комиссия)
- Автоматическая отправка уведомления через Celery

## Защита от Race Condition

Система использует `SELECT FOR UPDATE` для блокировки строк в БД во время транзакции. Это предотвращает:
- Double spending (двойное списание)
- Несогласованность балансов
- Race conditions при параллельных запросах

## Комиссия

- Если сумма перевода > 1000, система берет комиссию 10%
- Комиссия зачисляется на технический кошелек admin (user_id=0)
- Все операции выполняются атомарно

## Асинхронные уведомления

После успешной транзакции запускается Celery задача для отправки уведомления:
- Имитация долгого запроса (5 секунд)
- Автоматический retry при ошибке (через 3 секунды)
- Максимум 3 попытки

