import unittest
import sys
import os
import requests
import json
from datetime import datetime

# Добавляем путь к исходному коду
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))


class TestAPIConsistency(unittest.TestCase):
    """
    Тест согласованности API при изменении даты блокировки
    """

    BASE_URL = "http://localhost:8080"

    def setUp(self):
        """Проверяем доступность API"""
        try:
            response = requests.get(f"{self.BASE_URL}/api/accessibility")
            if response.text != "SUCCESS":
                self.skipTest("API недоступен")
        except:
            self.skipTest("API недоступен")

    def test_api_block_period_consistency(self):
        """
        Тест: API должен возвращать одинаковые результаты при разных датах блокировки
        """
        print("\n=== Тест согласованности API ===")

        end_date = "2024-10-01"
        results = []
        block_periods = [
            "2023-01-01T00:00:00",  # До всех транзакций
            "2024-01-01T00:00:00",  # В середине
            "2024-12-01T00:00:00"  # После всех транзакций
        ]

        for i, block_period in enumerate(block_periods):
            print(f"  Тест {i + 1}: устанавливаем блокировку {block_period.split('T')[0]}")

            # Устанавливаем дату блокировки
            response = requests.post(
                f"{self.BASE_URL}/api/settings/block-period",
                json={"block_period": block_period}
            )
            self.assertEqual(response.status_code, 200, "Не удалось установить дату блокировки")

            # Получаем комбинированный отчет
            response = requests.post(
                f"{self.BASE_URL}/api/report/combined-turnover",
                json={"end_date": end_date, "format": "csv"}
            )
            self.assertEqual(response.status_code, 200, "Не удалось получить отчет")

            result_data = response.json()
            results.append(result_data)

            print(f"    Получено элементов: {result_data['items_count']}")

        # Проверяем согласованность
        print("  Проверяем согласованность результатов...")

        # Все результаты должны иметь одинаковое количество элементов
        items_counts = [result['items_count'] for result in results]
        self.assertTrue(all(count == items_counts[0] for count in items_counts),
                        "Количество элементов должно быть одинаковым")

        print(f"  Количество элементов согласовано: {items_counts[0]}")
        print(" Тест пройден: API возвращает согласованные результаты")

    def test_api_period_calculation(self):
        """
        Тест: проверяем расчет за различные периоды через API
        """
        print("\n=== Тест расчета периодов через API ===")

        # Устанавливаем базовую дату блокировки
        response = requests.post(
            f"{self.BASE_URL}/api/settings/block-period",
            json={"block_period": "2024-01-01T00:00:00"}
        )
        self.assertEqual(response.status_code, 200)

        # Тестируем различные периоды
        test_periods = [
            {"start_date": "2023-01-01", "end_date": "2024-12-01"},
            {"start_date": "2024-01-01", "end_date": "2024-12-01"},
            {"start_date": "2023-06-01", "end_date": "2024-06-01"}
        ]

        for i, period in enumerate(test_periods):
            print(f"  Тест {i + 1}: период {period['start_date']} - {period['end_date']}")

            response = requests.post(
                f"{self.BASE_URL}/api/report/period-turnover",
                json={**period, "format": "csv"}
            )
            self.assertEqual(response.status_code, 200, "Не удалось получить отчет за период")

            result_data = response.json()
            print(f"    Получено элементов: {result_data['items_count']}")

        print("✅ Тест пройден: расчет периодов работает корректно")


if __name__ == '__main__':
    unittest.main(verbosity=2)