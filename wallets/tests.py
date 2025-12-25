from django.test import LiveServerTestCase
from decimal import Decimal
import asyncio
import aiohttp
from .models import Wallet, Transaction


class RaceConditionTest(LiveServerTestCase):
    def setUp(self):
        self.from_wallet = Wallet.objects.create(
            user_id=1,
            balance=Decimal('10000.00')
        )
        
        self.to_wallet = Wallet.objects.create(
            user_id=2,
            balance=Decimal('0.00')
        )
    
        self.admin_wallet = Wallet.objects.create(
            user_id=0,
            balance=Decimal('0.00'),
            is_admin=True
        )

    async def make_transfer(self, session, url, from_wallet_id, to_wallet_id, amount):
        payload = {
            'from_wallet_id': from_wallet_id,
            'to_wallet_id': to_wallet_id,
            'amount': str(amount)
        }
        
        try:
            async with session.post(
                url,
                json=payload,
                headers={'Content-Type': 'application/json'}
            ) as response:
                status_code = response.status
                try:
                    data = await response.json()
                except:
                    data = await response.text()
                
                return {
                    'status_code': status_code,
                    'data': data
                }
        except Exception as e:
            return {
                'status_code': 0,
                'data': {'error': str(e)}
            }
    
    def test_concurrent_transfers_balance_not_negative(self):
        initial_balance = self.from_wallet.balance
        transfer_amount = Decimal('1001.00')  # Сумма каждого перевода
        
        num_requests = 100
        
        url = f'{self.live_server_url}/api/transfer'
        
        async def run_concurrent_transfers():
            """Запускает параллельные запросы"""
            async with aiohttp.ClientSession() as session:
                tasks = [
                    self.make_transfer(
                        session,
                        url,
                        self.from_wallet.id,
                        self.to_wallet.id,
                        transfer_amount
                    )
                    for _ in range(num_requests)
                ]
                results = await asyncio.gather(*tasks)
                return results
        
        results = asyncio.run(run_concurrent_transfers())
        
        self.from_wallet.refresh_from_db()
        self.to_wallet.refresh_from_db()
        self.admin_wallet.refresh_from_db()
        
        self.assertGreaterEqual(
            self.from_wallet.balance,
            Decimal('0.00'),
            f"Баланс не должен быть отрицательным. Текущий баланс: {self.from_wallet.balance}"
        )
        
        self.assertLessEqual(
            self.from_wallet.balance,
            initial_balance,
            f"Баланс не должен превышать начальный. Начальный: {initial_balance}, Текущий: {self.from_wallet.balance}"
        )
        
        successful = sum(1 for r in results if r['status_code'] == 201)
        failed = sum(1 for r in results if r['status_code'] != 201)
        
        max_possible_successful = int(initial_balance / transfer_amount)
        
        self.assertLessEqual(
            successful,
            max_possible_successful,
            f"Количество успешных транзакций ({successful}) не должно превышать возможное ({max_possible_successful})"
        )
        
        successful_transactions = Transaction.objects.filter(
            from_wallet=self.from_wallet,
            status='completed'
        )
        total_debited = sum(
            t.amount + t.fee for t in successful_transactions
        )
        
        self.assertLessEqual(
            total_debited,
            initial_balance,
            f"Общая сумма списанных средств ({total_debited}) не должна превышать начальный баланс ({initial_balance})"
        )
        
        expected_balance = initial_balance - total_debited
        self.assertEqual(
            self.from_wallet.balance,
            expected_balance,
            f"Финальный баланс должен быть {expected_balance}, но получен {self.from_wallet.balance}"
        )
        
        print(f"\n=== Результаты теста ===")
        print(f"Начальный баланс: {initial_balance}")
        print(f"Сумма одного перевода: {transfer_amount}")
        print(f"Количество запросов: {num_requests}")
        print(f"Успешных транзакций: {successful}")
        print(f"Неуспешных транзакций: {failed}")

        total_fee = sum(t.fee for t in successful_transactions)
        
        print(f"Финальный баланс отправителя: {self.from_wallet.balance}")
        print(f"Финальный баланс получателя: {self.to_wallet.balance}")
        print(f"Финальный баланс администратора: {self.admin_wallet.balance}")
        print(f"Ожидаемая комиссия: {total_fee}")
        self.assertEqual(
            self.admin_wallet.balance,
            total_fee,
            f"Баланс администратора должен быть {total_fee}, но получен {self.admin_wallet.balance}"
        )
        print(f"Общая сумма списаний: {total_debited}")
        print(f"Баланс НЕ ушел в минус: ✓")
