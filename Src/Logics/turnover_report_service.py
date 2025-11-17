from flask import request, jsonify
from Src.Dtos.universal_filter_dto import universal_filter_dto
from Src.Core.universal_prototype import universal_prototype
from Src.Core.validator import validator, operation_exception
from Src.Models.nomenclature_model import nomenclature_model
from Src.Models.transaction_model import transaction_model
from Src.Models.storage_model import storage_model
from Src.Core.response_formats import response_formats
from Src.Logics.factory_entities import factory_entities
from Src.reposity import reposity
from datetime import datetime
from decimal import Decimal

"""
Модель для строки ОСВ
"""


class turnover_item:
    def __init__(self):
        self.nomenclature_name = ""
        self.nomenclature_code = ""
        self.storage_name = ""
        self.storage_code = ""
        self.unit_name = ""
        self.start_balance = Decimal('0.0')
        self.income = Decimal('0.0')
        self.outcome = Decimal('0.0')
        self.end_balance = Decimal('0.0')


"""
Сервис для формирования оборотно-сальдовой ведомости
"""


class turnover_report_service:

    def __init__(self):
        self.__repo = reposity()

    def setup_routes(self, app):
        """Настройка маршрутов API для ОСВ"""

        @app.route("/api/report/turnover", methods=['POST'])
        def generate_turnover_report():
            """
            POST запрос для генерации ОСВ с учетом фильтрации

            Body:
                filter_dto: DTO модель фильтрации (опционально)
                format: Формат ответа (csv, markdown) - опционально
                start_date: Дата начала периода (опционально)
                end_date: Дата окончания периода (опционально)
            """
            try:
                # Получаем данные из запроса
                data = request.get_json()
                if not data:
                    return jsonify({"error": "No JSON data provided"}), 400

                format = data.get('format', response_formats.csv())
                start_date_str = data.get('start_date')
                end_date_str = data.get('end_date')

                # Парсим даты если указаны
                start_date = None
                end_date = None

                if start_date_str:
                    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
                if end_date_str:
                    end_date = datetime.strptime(end_date_str, "%Y-%m-%d")

                # Создаем DTO фильтрации если передан
                filter_dto = None
                if any(key in data for key in ['field_name', 'nested_field', 'value', 'filter_type']):
                    filter_dto = universal_filter_dto()
                    filter_dto.create(data)
                    if not filter_dto.model_type:
                        filter_dto.model_type = "nomenclature"  # по умолчанию для ОСВ

                # Генерируем отчет
                report_data = self._generate_turnover_report(filter_dto, start_date, end_date)

                # Формируем ответ в нужном формате
                response_data = self._build_response(report_data, format)

                return jsonify({
                    "success": True,
                    "report_type": "turnover",
                    "items_count": len(report_data),
                    "period": {
                        "start_date": start_date_str,
                        "end_date": end_date_str
                    },
                    "data": response_data
                })

            except operation_exception as e:
                return jsonify({"error": str(e)}), 400
            except Exception as e:
                return jsonify({"error": f"Внутренняя ошибка сервера: {str(e)}"}), 500

    def _generate_turnover_report(self, filter_dto: universal_filter_dto = None,
                                  start_date: datetime = None, end_date: datetime = None) -> list:
        """
        Генерирует оборотно-сальдовую ведомость с учетом фильтрации
        """
        try:
            # Получаем все транзакции
            all_transactions = self.__repo.data.get(reposity.transaction_key(), [])

            # Фильтруем транзакции по дате если указаны периоды
            filtered_transactions = self._filter_transactions_by_date(all_transactions, start_date, end_date)

            # Применяем дополнительную фильтрацию если указана
            if filter_dto:
                prototype = universal_prototype(filtered_transactions)
                filtered_transactions = prototype.apply_filter(filter_dto).data

            # Группируем транзакции по номенклатуре и складу
            grouped_data = self._group_transactions(filtered_transactions)

            # Формируем строки отчета
            report_items = self._build_report_items(grouped_data)

            return report_items

        except Exception as e:
            raise operation_exception(f"Ошибка генерации ОСВ: {str(e)}")

    def _filter_transactions_by_date(self, transactions: list, start_date: datetime, end_date: datetime) -> list:
        """
        Фильтрует транзакции по периоду
        """
        if not start_date and not end_date:
            return transactions

        filtered = []
        for transaction in transactions:
            transaction_date = transaction.period

            # Проверяем попадание в период
            in_period = True
            if start_date and transaction_date < start_date:
                in_period = False
            if end_date and transaction_date > end_date:
                in_period = False

            if in_period:
                filtered.append(transaction)

        return filtered

    def _group_transactions(self, transactions: list) -> dict:
        """
        Группирует транзакции по номенклатуре и складу
        """
        grouped = {}

        for transaction in transactions:
            if not transaction.nomenclature or not transaction.storage:
                continue

            key = f"{transaction.nomenclature.unique_code}_{transaction.storage.unique_code}"

            if key not in grouped:
                grouped[key] = {
                    'nomenclature': transaction.nomenclature,
                    'storage': transaction.storage,
                    'unit': transaction.range,
                    'transactions': []
                }

            grouped[key]['transactions'].append(transaction)

        return grouped

    def _build_report_items(self, grouped_data: dict) -> list:
        """
        Строит строки отчета из сгруппированных данных
        """
        report_items = []

        for key, group_data in grouped_data.items():
            item = turnover_item()

            # Заполняем基本信息
            item.nomenclature_name = group_data['nomenclature'].name
            item.nomenclature_code = group_data['nomenclature'].unique_code
            item.storage_name = group_data['storage'].name
            item.storage_code = group_data['storage'].unique_code
            item.unit_name = group_data['unit'].name if group_data['unit'] else ""

            # Рассчитываем обороты
            for transaction in group_data['transactions']:
                if transaction.value > 0:
                    item.income += Decimal(str(transaction.value))
                else:
                    item.outcome += Decimal(str(abs(transaction.value)))

            # Сальдо на начало (в реальной системе нужно получать из БД)
            item.start_balance = Decimal('0.0')

            # Сальдо на конец
            item.end_balance = item.start_balance + item.income - item.outcome

            report_items.append(item)

        return report_items

    def _build_response(self, data: list, format: str) -> str:
        try:
            if not data:
                return "Нет данных, соответствующих критериям фильтрации"

            # Используем существующую фабрику
            factory = factory_entities()
            response_builder_class = factory.create(format)  # Получаем класс
            response_builder = response_builder_class()  # Создаем экземпляр

            return response_builder.build(data)

        except Exception as e:
            raise operation_exception(f"Ошибка формирования ответа: {str(e)}")
    # Методы для работы с прототипом (шаблон Prototype)
    def create_prototype_from_transactions(self, filter_dto: universal_filter_dto = None) -> universal_prototype:
        """
        Создает прототип из транзакций с учетом фильтрации
        """
        transactions = self.__repo.data.get(reposity.transaction_key(), [])

        if filter_dto:
            prototype = universal_prototype(transactions)
            return prototype.apply_filter(filter_dto)
        else:
            return universal_prototype(transactions)

    def generate_turnover_from_prototype(self, prototype: universal_prototype) -> list:
        """
        Генерирует ОСВ из прототипа с отфильтрованными транзакциями
        """
        transactions = prototype.data
        grouped_data = self._group_transactions(transactions)
        return self._build_report_items(grouped_data)