from Src.Core.validator import validator, operation_exception
from Src.Models.transaction_model import transaction_model
from Src.Models.settings_model import settings_model
from Src.Models.nomenclature_model import nomenclature_model
from Src.Models.storage_model import storage_model
from Src.Models.range_model import range_model
from Src.reposity import reposity
from datetime import datetime
from decimal import Decimal
import json
import os

"""
Модель для хранения рассчитанных оборотов до блокировки
"""


class blocked_turnover_item:
    def __init__(self):
        self.nomenclature_id = ""
        self.nomenclature_name = ""
        self.storage_id = ""
        self.storage_name = ""
        self.unit_id = ""
        self.unit_name = ""
        self.blocked_income = Decimal('0.0')
        self.blocked_outcome = Decimal('0.0')
        self.calculation_date = datetime.now()
        # ДОБАВЛЯЕМ ПОЛЯ ДЛЯ КОМБИНИРОВАННОГО РАСЧЕТА
        self.blocked_period_income = Decimal('0.0')  # Обороты до блокировки
        self.blocked_period_outcome = Decimal('0.0')  # Обороты до блокировки
        self.fresh_period_income = Decimal('0.0')  # Обороты после блокировки
        self.fresh_period_outcome = Decimal('0.0')  # Обороты после блокировки


"""
Сервис для расчета и хранения оборотов до даты блокировки
"""


class block_period_service:

    def __init__(self):
        self.__repo = reposity()
        self.__settings = settings_model()  # Создаем экземпляр настроек
        self.__settings.block_period = datetime(2025, 1, 1)  # Устанавливаем дату по умолчанию
        self.__cache_file = "blocked_turnovers.json"

    def calculate_blocked_turnovers(self) -> list:
        """
        Рассчитывает обороты за период с 1900-01-01 до block_period
        Возвращает список blocked_turnover_item
        """
        try:
            # Получаем все транзакции
            all_transactions = self.__repo.data.get(reposity.transaction_key(), [])

            # Фильтруем транзакции до даты блокировки
            blocked_transactions = self._filter_transactions_before_block(all_transactions)

            # Группируем и рассчитываем обороты
            blocked_turnovers = self._calculate_turnovers(blocked_transactions)

            # Сохраняем результаты
            self._save_blocked_turnovers(blocked_turnovers)

            return blocked_turnovers

        except Exception as e:
            raise operation_exception(f"Ошибка расчета оборотов до блокировки: {str(e)}")

    # ДОБАВЛЯЕМ НОВЫЕ МЕТОДЫ ДЛЯ КОМБИНИРОВАННОГО РАСЧЕТА:

    def calculate_combined_turnovers(self, end_date: datetime) -> list:
        """
        Комбинированный расчет оборотов за период 1900-01-01 до end_date:
        - До блокировки: используем сохраненные значения
        - После блокировки: рассчитываем свежие обороты
        - Объединяем и группируем результат
        """
        try:
            # 1. Получаем сохраненные обороты до блокировки
            blocked_turnovers = self.load_blocked_turnovers()

            # 2. Рассчитываем обороты с даты блокировки до end_date
            fresh_turnovers = self._calculate_fresh_turnovers(end_date)

            # 3. Объединяем и группируем результаты
            combined_turnovers = self._combine_turnovers(blocked_turnovers, fresh_turnovers)

            return combined_turnovers

        except Exception as e:
            raise operation_exception(f"Ошибка комбинированного расчета оборотов: {str(e)}")

    def _calculate_fresh_turnovers(self, end_date: datetime) -> list:
        """
        Рассчитывает обороты с даты блокировки до указанной конечной даты
        """
        try:
            # Получаем все транзакции
            all_transactions = self.__repo.data.get(reposity.transaction_key(), [])
            block_period = self.__settings.block_period

            # Фильтруем транзакции после блокировки до end_date
            fresh_transactions = []

            for transaction in all_transactions:
                if block_period < transaction.period <= end_date:
                    fresh_transactions.append(transaction)

            # Группируем и рассчитываем обороты
            fresh_turnovers = self._calculate_turnovers(fresh_transactions)

            return fresh_turnovers

        except Exception as e:
            raise operation_exception(f"Ошибка расчета свежих оборотов: {str(e)}")

    def _combine_turnovers(self, blocked_turnovers: list, fresh_turnovers: list) -> list:
        """
        Объединяет сохраненные обороты до блокировки и свежие обороты после блокировки
        """
        combined = {}

        # Добавляем сохраненные обороты до блокировки
        for blocked_item in blocked_turnovers:
            key = f"{blocked_item.nomenclature_id}_{blocked_item.storage_id}"
            combined[key] = {
                'nomenclature_id': blocked_item.nomenclature_id,
                'nomenclature_name': blocked_item.nomenclature_name,
                'storage_id': blocked_item.storage_id,
                'storage_name': blocked_item.storage_name,
                'unit_id': blocked_item.unit_id,
                'unit_name': blocked_item.unit_name,
                'total_income': blocked_item.blocked_income,
                'total_outcome': blocked_item.blocked_outcome,
                'blocked_period_income': blocked_item.blocked_income,
                'blocked_period_outcome': blocked_item.blocked_outcome,
                'fresh_period_income': Decimal('0.0'),
                'fresh_period_outcome': Decimal('0.0')
            }

        # Добавляем свежие обороты после блокировки
        for fresh_item in fresh_turnovers:
            key = f"{fresh_item.nomenclature_id}_{fresh_item.storage_id}"

            if key in combined:
                # Обновляем существующую запись
                combined[key]['fresh_period_income'] = fresh_item.blocked_income
                combined[key]['fresh_period_outcome'] = fresh_item.blocked_outcome
                combined[key]['total_income'] += fresh_item.blocked_income
                combined[key]['total_outcome'] += fresh_item.blocked_outcome
            else:
                # Создаем новую запись (если нет сохраненных оборотов до блокировки)
                combined[key] = {
                    'nomenclature_id': fresh_item.nomenclature_id,
                    'nomenclature_name': fresh_item.nomenclature_name,
                    'storage_id': fresh_item.storage_id,
                    'storage_name': fresh_item.storage_name,
                    'unit_id': fresh_item.unit_id,
                    'unit_name': fresh_item.unit_name,
                    'total_income': fresh_item.blocked_income,
                    'total_outcome': fresh_item.blocked_outcome,
                    'blocked_period_income': Decimal('0.0'),
                    'blocked_period_outcome': Decimal('0.0'),
                    'fresh_period_income': fresh_item.blocked_income,
                    'fresh_period_outcome': fresh_item.blocked_outcome
                }

        # Преобразуем обратно в список blocked_turnover_item
        result = []
        for key, data in combined.items():
            item = blocked_turnover_item()
            item.nomenclature_id = data['nomenclature_id']
            item.nomenclature_name = data['nomenclature_name']
            item.storage_id = data['storage_id']
            item.storage_name = data['storage_name']
            item.unit_id = data['unit_id']
            item.unit_name = data['unit_name']
            item.blocked_income = data['total_income']  # Общие обороты
            item.blocked_outcome = data['total_outcome']  # Общие обороты

            # Сохраняем детализацию по периодам
            item.blocked_period_income = data['blocked_period_income']
            item.blocked_period_outcome = data['blocked_period_outcome']
            item.fresh_period_income = data['fresh_period_income']
            item.fresh_period_outcome = data['fresh_period_outcome']

            item.calculation_date = datetime.now()
            result.append(item)

        return result

    def get_combined_turnover_for_period(self, start_date: datetime, end_date: datetime) -> list:
        """
        Универсальный метод для расчета оборотов за любой период
        Автоматически использует сохраненные данные до блокировки
        """
        try:
            block_period = self.__settings.block_period

            # Если период полностью после блокировки - простой расчет
            if start_date >= block_period:
                return self._calculate_turnovers_for_period(start_date, end_date)

            # Если период охватывает блокировку - комбинированный расчет
            if end_date > block_period:
                # Получаем сохраненные обороты до блокировки
                blocked_turnovers = self.load_blocked_turnovers()

                # Рассчитываем свежие обороты после блокировки
                fresh_turnovers = self._calculate_turnovers_for_period(block_period, end_date)

                # Объединяем
                return self._combine_turnovers(blocked_turnovers, fresh_turnovers)
            else:
                # Период полностью до блокировки - используем сохраненные данные
                return self.load_blocked_turnovers()

        except Exception as e:
            raise operation_exception(f"Ошибка расчета оборотов за период: {str(e)}")

    def _calculate_turnovers_for_period(self, start_date: datetime, end_date: datetime) -> list:
        """
        Рассчитывает обороты за указанный период
        """
        try:
            all_transactions = self.__repo.data.get(reposity.transaction_key(), [])

            # Фильтруем транзакции по периоду
            period_transactions = []
            for transaction in all_transactions:
                if start_date <= transaction.period <= end_date:
                    period_transactions.append(transaction)

            # Рассчитываем обороты
            return self._calculate_turnovers(period_transactions)

        except Exception as e:
            raise operation_exception(f"Ошибка расчета оборотов за период: {str(e)}")

    # СУЩЕСТВУЮЩИЕ МЕТОДЫ (оставляем без изменений):

    def _filter_transactions_before_block(self, transactions: list) -> list:
        """Фильтрует транзакции до даты блокировки"""
        blocked_period = self.__settings.block_period
        filtered = []

        for transaction in transactions:
            if transaction.period <= blocked_period:
                filtered.append(transaction)

        return filtered

    def _calculate_turnovers(self, transactions: list) -> list:
        """Рассчитывает обороты по отфильтрованным транзакциям"""
        grouped = {}

        for transaction in transactions:
            if not transaction.nomenclature or not transaction.storage:
                continue

            key = f"{transaction.nomenclature.unique_code}_{transaction.storage.unique_code}"

            if key not in grouped:
                grouped[key] = {
                    'nomenclature_id': transaction.nomenclature.unique_code,
                    'nomenclature_name': transaction.nomenclature.name,
                    'storage_id': transaction.storage.unique_code,
                    'storage_name': transaction.storage.name,
                    'unit_id': transaction.range.unique_code if transaction.range else "",
                    'unit_name': transaction.range.name if transaction.range else "",
                    'income': Decimal('0.0'),
                    'outcome': Decimal('0.0')
                }

            # Суммируем обороты
            if transaction.value > 0:
                grouped[key]['income'] += Decimal(str(transaction.value))
            else:
                grouped[key]['outcome'] += Decimal(str(abs(transaction.value)))

        # Преобразуем в blocked_turnover_item
        result = []
        for key, data in grouped.items():
            item = blocked_turnover_item()
            item.nomenclature_id = data['nomenclature_id']
            item.nomenclature_name = data['nomenclature_name']
            item.storage_id = data['storage_id']
            item.storage_name = data['storage_name']
            item.unit_id = data['unit_id']
            item.unit_name = data['unit_name']
            item.blocked_income = data['income']
            item.blocked_outcome = data['outcome']
            item.calculation_date = datetime.now()
            result.append(item)

        return result

    def _save_blocked_turnovers(self, turnovers: list):
        """Сохраняет рассчитанные обороты в файл"""
        try:
            data = []
            for item in turnovers:
                item_data = {
                    'nomenclature_id': item.nomenclature_id,
                    'nomenclature_name': item.nomenclature_name,
                    'storage_id': item.storage_id,
                    'storage_name': item.storage_name,
                    'unit_id': item.unit_id,
                    'unit_name': item.unit_name,
                    'blocked_income': str(item.blocked_income),
                    'blocked_outcome': str(item.blocked_outcome),
                    'calculation_date': item.calculation_date.isoformat()
                }
                # ДОБАВЛЯЕМ НОВЫЕ ПОЛЯ ДЛЯ СОХРАНЕНИЯ
                if hasattr(item, 'blocked_period_income'):
                    item_data['blocked_period_income'] = str(item.blocked_period_income)
                    item_data['blocked_period_outcome'] = str(item.blocked_period_outcome)
                    item_data['fresh_period_income'] = str(item.fresh_period_income)
                    item_data['fresh_period_outcome'] = str(item.fresh_period_outcome)

                data.append(item_data)

            with open(self.__cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            raise operation_exception(f"Ошибка сохранения оборотов: {str(e)}")

    def load_blocked_turnovers(self) -> list:
        """Загружает ранее рассчитанные обороты"""
        try:
            if not os.path.exists(self.__cache_file):
                return []

            with open(self.__cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            result = []
            for item_data in data:
                item = blocked_turnover_item()
                item.nomenclature_id = item_data['nomenclature_id']
                item.nomenclature_name = item_data['nomenclature_name']
                item.storage_id = item_data['storage_id']
                item.storage_name = item_data['storage_name']
                item.unit_id = item_data['unit_id']
                item.unit_name = item_data['unit_name']
                item.blocked_income = Decimal(item_data['blocked_income'])
                item.blocked_outcome = Decimal(item_data['blocked_outcome'])
                item.calculation_date = datetime.fromisoformat(item_data['calculation_date'])

                # ЗАГРУЖАЕМ НОВЫЕ ПОЛЯ ЕСЛИ ЕСТЬ
                if 'blocked_period_income' in item_data:
                    item.blocked_period_income = Decimal(item_data['blocked_period_income'])
                    item.blocked_period_outcome = Decimal(item_data['blocked_period_outcome'])
                    item.fresh_period_income = Decimal(item_data['fresh_period_income'])
                    item.fresh_period_outcome = Decimal(item_data['fresh_period_outcome'])

                result.append(item)

            return result

        except Exception as e:
            raise operation_exception(f"Ошибка загрузки оборотов: {str(e)}")

    def get_block_period(self) -> datetime:
        """Возвращает текущую дату блокировки"""
        return self.__settings.block_period

    def set_block_period(self, new_period: datetime):
        """Устанавливает новую дату блокировки"""
        validator.validate(new_period, datetime)
        self.__settings.block_period = new_period
        # Пересчитываем обороты при изменении даты
        self.calculate_blocked_turnovers()

    def get_blocked_turnover_for_item(self, nomenclature_id: str, storage_id: str) -> blocked_turnover_item:
        """Возвращает обороты для конкретной номенклатуры и склада"""
        turnovers = self.load_blocked_turnovers()
        for item in turnovers:
            if item.nomenclature_id == nomenclature_id and item.storage_id == storage_id:
                return item
        return None

    def recalculate_blocked_turnovers(self):
        """Принудительный пересчет оборотов до блокировки"""
        return self.calculate_blocked_turnovers()