import unittest
import sys
import os
from datetime import datetime
from decimal import Decimal

# Добавляем путь к исходному коду
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from Src.Logics.block_period_service import block_period_service, blocked_turnover_item
from Src.Models.settings_model import settings_model
from Src.Models.transaction_model import transaction_model
from Src.Models.nomenclature_model import nomenclature_model
from Src.Models.storage_model import storage_model
from Src.Models.range_model import range_model
from Src.reposity import reposity


class TestBlockPeriodCalculations(unittest.TestCase):
    """
    Модульный тест для проверки расчетов с датой блокировки
    """

    def setUp(self):
        """Настройка тестовых данных"""
        self.repo = reposity()
        self.repo.initalize()

        # Создаем тестовые данные
        self._create_test_data()

        # Создаем сервис
        self.block_service = block_period_service()

    def _create_test_data(self):
        """Создает тестовые транзакции"""
        # Создаем тестовую номенклатуру
        nomenclature = nomenclature_model()
        nomenclature.name = "Тестовая номенклатура"
        nomenclature.unique_code = "test_nomenclature_1"

        # Создаем тестовый склад
        storage = storage_model()
        storage.name = "Тестовый склад"
        storage.unique_code = "test_storage_1"

        # Создаем тестовую единицу измерения
        unit = range_model()
        unit.name = "Тестовая единица"
        unit.unique_code = "test_unit_1"

        # Создаем транзакции до блокировки
        transaction1 = transaction_model()
        transaction1.nomenclature = nomenclature
        transaction1.storage = storage
        transaction1.range = unit
        transaction1.period = datetime(2023, 12, 15)  # До блокировки
        transaction1.value = 100.0  # Приход

        transaction2 = transaction_model()
        transaction2.nomenclature = nomenclature
        transaction2.storage = storage
        transaction2.range = unit
        transaction2.period = datetime(2023, 12, 20)  # До блокировки
        transaction2.value = -50.0  # Расход

        # Создаем транзакции после блокировки
        transaction3 = transaction_model()
        transaction3.nomenclature = nomenclature
        transaction3.storage = storage
        transaction3.range = unit
        transaction3.period = datetime(2024, 2, 1)  # После блокировки
        transaction3.value = 200.0  # Приход

        transaction4 = transaction_model()
        transaction4.nomenclature = nomenclature
        transaction4.storage = storage
        transaction4.range = unit
        transaction4.period = datetime(2024, 2, 15)  # После блокировки
        transaction4.value = -100.0  # Расход

        # Сохраняем в репозиторий
        self.repo.data[reposity.nomenclature_key()] = [nomenclature]
        self.repo.data[reposity.storage_key()] = [storage]
        self.repo.data[reposity.range_key()] = [unit]
        self.repo.data[reposity.transaction_key()] = [transaction1, transaction2, transaction3, transaction4]

        self.test_nomenclature = nomenclature
        self.test_storage = storage

    def test_block_period_change_consistency(self):
        """
        Тест: при изменении даты блокировки конечный результат не должен измениться
        """
        print("\n=== Тест согласованности при изменении даты блокировки ===")

        # Конечная дата для расчета
        end_date = datetime(2024, 10, 1)

        # Тест 1: Блокировка до всех транзакций
        print("1. Устанавливаем блокировку до всех транзакций...")
        self.block_service.set_block_period(datetime(2023, 1, 1))
        result1 = self.block_service.calculate_combined_turnovers(end_date)

        # Тест 2: Блокировка в середине периода
        print("2. Устанавливаем блокировку в середине периода...")
        self.block_service.set_block_period(datetime(2024, 1, 1))
        result2 = self.block_service.calculate_combined_turnovers(end_date)

        # Тест 3: Блокировка после всех транзакций
        print("3. Устанавливаем блокировку после всех транзакций...")
        self.block_service.set_block_period(datetime(2024, 12, 1))
        result3 = self.block_service.calculate_combined_turnovers(end_date)

        # Проверяем, что результаты согласованы
        print("4. Проверяем согласованность результатов...")

        # Извлекаем общие обороты из каждого результата
        total_income_1 = sum(item.blocked_income for item in result1)
        total_outcome_1 = sum(item.blocked_outcome for item in result1)

        total_income_2 = sum(item.blocked_income for item in result2)
        total_outcome_2 = sum(item.blocked_outcome for item in result2)

        total_income_3 = sum(item.blocked_income for item in result3)
        total_outcome_3 = sum(item.blocked_outcome for item in result3)

        print(f"   Результат 1 (блокировка до): приход={total_income_1}, расход={total_outcome_1}")
        print(f"   Результат 2 (блокировка в середине): приход={total_income_2}, расход={total_outcome_2}")
        print(f"   Результат 3 (блокировка после): приход={total_income_3}, расход={total_outcome_3}")

        # Проверяем равенство результатов
        self.assertEqual(total_income_1, total_income_2,
                         "Приход должен быть одинаковым при разных датах блокировки")
        self.assertEqual(total_income_2, total_income_3,
                         "Приход должен быть одинаковым при разных датах блокировки")
        self.assertEqual(total_outcome_1, total_outcome_2,
                         "Расход должен быть одинаковым при разных датах блокировки")
        self.assertEqual(total_outcome_2, total_outcome_3,
                         "Расход должен быть одинаковым при разных датах блокировки")

        print(" Тест пройден: результаты согласованы при разных датах блокировки")

    def test_individual_item_consistency(self):
        """
        Тест: проверяем согласованность для конкретной номенклатуры и склада
        """
        print("\n=== Тест согласованности для конкретного элемента ===")

        end_date = datetime(2024, 10, 1)

        # Тестируем с разными датами блокировки
        block_dates = [
            datetime(2023, 1, 1),  # До всех транзакций
            datetime(2024, 1, 1),  # В середине
            datetime(2024, 12, 1)  # После всех транзакций
        ]

        previous_result = None

        for i, block_date in enumerate(block_dates):
            print(f"  Тест {i + 1}: блокировка {block_date.date()}")
            self.block_service.set_block_period(block_date)
            result = self.block_service.calculate_combined_turnovers(end_date)

            # Находим наш тестовый элемент
            test_item = None
            for item in result:
                if (item.nomenclature_id == self.test_nomenclature.unique_code and
                        item.storage_id == self.test_storage.unique_code):
                    test_item = item
                    break

            self.assertIsNotNone(test_item, "Тестовый элемент должен быть найден")

            if previous_result:
                # Сравниваем с предыдущим результатом
                self.assertEqual(test_item.blocked_income, previous_result.blocked_income,
                                 f"Приход должен быть одинаковым (блокировка {block_date.date()})")
                self.assertEqual(test_item.blocked_outcome, previous_result.blocked_outcome,
                                 f"Расход должен быть одинаковым (блокировка {block_date.date()})")

            previous_result = test_item
            print(f"    Приход: {test_item.blocked_income}, Расход: {test_item.blocked_outcome}")

        print(" Тест пройден: конкретный элемент согласован при разных датах блокировки")

    def test_period_distribution(self):
        """
        Тест: проверяем правильность распределения по периодам
        """
        print("\n=== Тест распределения по периодам ===")

        end_date = datetime(2024, 10, 1)
        block_date = datetime(2024, 1, 1)  # Блокировка в середине

        self.block_service.set_block_period(block_date)
        result = self.block_service.calculate_combined_turnovers(end_date)

        # Находим тестовый элемент
        test_item = None
        for item in result:
            if (item.nomenclature_id == self.test_nomenclature.unique_code and
                    item.storage_id == self.test_storage.unique_code):
                test_item = item
                break

        self.assertIsNotNone(test_item, "Тестовый элемент должен быть найден")

        print(
            f"  Обороты до блокировки: приход={test_item.blocked_period_income}, расход={test_item.blocked_period_outcome}")
        print(
            f"  Обороты после блокировки: приход={test_item.fresh_period_income}, расход={test_item.fresh_period_outcome}")
        print(f"  Общие обороты: приход={test_item.blocked_income}, расход={test_item.blocked_outcome}")

        # Проверяем, что сумма периодов равна общему результату
        total_income = test_item.blocked_period_income + test_item.fresh_period_income
        total_outcome = test_item.blocked_period_outcome + test_item.fresh_period_outcome

        self.assertEqual(total_income, test_item.blocked_income,
                         "Сумма оборотов по периодам должна равняться общему приходу")
        self.assertEqual(total_outcome, test_item.blocked_outcome,
                         "Сумма оборотов по периодам должна равняться общему расходу")

        # Проверяем ожидаемые значения (из тестовых данных)
        expected_blocked_income = Decimal('100.0')  # transaction1
        expected_blocked_outcome = Decimal('50.0')  # transaction2
        expected_fresh_income = Decimal('200.0')  # transaction3
        expected_fresh_outcome = Decimal('100.0')  # transaction4

        self.assertEqual(test_item.blocked_period_income, expected_blocked_income,
                         "Приход до блокировки не соответствует ожидаемому")
        self.assertEqual(test_item.blocked_period_outcome, expected_blocked_outcome,
                         "Расход до блокировки не соответствует ожидаемому")
        self.assertEqual(test_item.fresh_period_income, expected_fresh_income,
                         "Приход после блокировки не соответствует ожидаемому")
        self.assertEqual(test_item.fresh_period_outcome, expected_fresh_outcome,
                         "Расход после блокировки не соответствует ожидаемому")

        print(" Тест пройден: распределение по периодам корректно")

    def test_empty_transactions(self):
        """
        Тест: проверяем работу с пустыми данными
        """
        print("\n=== Тест с пустыми данными ===")

        # Сохраняем оригинальные данные
        original_transactions = self.repo.data.get(reposity.transaction_key(), [])

        try:
            # Очищаем транзакции
            self.repo.data[reposity.transaction_key()] = []

            end_date = datetime(2024, 10, 1)
            self.block_service.set_block_period(datetime(2024, 1, 1))

            result = self.block_service.calculate_combined_turnovers(end_date)

            # Результат должен быть пустым списком
            self.assertEqual(len(result), 0, "Результат должен быть пустым при отсутствии транзакций")
            print(" Тест пройден: пустые данные обрабатываются корректно")

        finally:
            # Восстанавливаем оригинальные данные
            self.repo.data[reposity.transaction_key()] = original_transactions


if __name__ == '__main__':
    # Запускаем тесты с подробным выводом
    unittest.main(verbosity=2)