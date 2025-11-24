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
from Src.Logics.block_period_service import block_period_service

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
Модель для комбинированного отчета с детализацией по периодам
"""


class combined_turnover_item:
    def __init__(self):
        self.nomenclature_name = ""
        self.nomenclature_code = ""
        self.storage_name = ""
        self.storage_code = ""
        self.unit_name = ""
        self.blocked_period_income = Decimal('0.0')  # Обороты до блокировки
        self.blocked_period_outcome = Decimal('0.0')  # Обороты до блокировки
        self.fresh_period_income = Decimal('0.0')  # Обороты после блокировки
        self.fresh_period_outcome = Decimal('0.0')  # Обороты после блокировки
        self.total_income = Decimal('0.0')  # Общие обороты
        self.total_outcome = Decimal('0.0')  # Общие обороты
        self.start_balance = Decimal('0.0')  # Сальдо на начало (до блокировки)
        self.end_balance = Decimal('0.0')  # Сальдо на конец


"""
Сервис для формирования оборотно-сальдовой ведомости
"""


class turnover_report_service:

    def __init__(self):
        self.__repo = reposity()
        self.__block_service = block_period_service()  # Добавляем сервис блокировки

    def setup_routes(self, app):
        """Настройка маршрутов API для ОСВ"""

        @app.route("/api/report/turnover", methods=['POST'])
        def generate_turnover_report():
            """
            POST запрос для генерации ОСВ с учетом фильтрации
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

        # ДОБАВЛЯЕМ НОВЫЕ ENDPOINTS ДЛЯ КОМБИНИРОВАННОГО РАСЧЕТА:

        @app.route("/api/report/combined-turnover", methods=['POST'])
        def generate_combined_turnover_report():
            """
            Комбинированный расчет оборотов за период 1900-01-01 до end_date
            с использованием сохраненных данных до блокировки
            """
            try:
                data = request.get_json() or {}
                format = data.get('format', response_formats.csv())
                end_date_str = data.get('end_date')

                if not end_date_str:
                    return jsonify({"error": "Не указана конечная дата периода"}), 400

                end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
                block_period = self.__block_service.get_block_period()

                # Комбинированный расчет
                combined_turnovers = self.__block_service.calculate_combined_turnovers(end_date)

                # Формируем детализированный отчет
                report_items = self._build_combined_report_items(combined_turnovers)

                # Формируем ответ
                response_data = self._build_response(report_items, format)

                return jsonify({
                    "success": True,
                    "report_type": "combined_turnover",
                    "period": {
                        "start_date": "1900-01-01",  # Фиксированная начальная дата
                        "block_period": block_period.isoformat(),
                        "end_date": end_date_str
                    },
                    "items_count": len(report_items),
                    "data": response_data
                })

            except operation_exception as e:
                return jsonify({"error": str(e)}), 400
            except Exception as e:
                return jsonify({"error": f"Внутренняя ошибка сервера: {str(e)}"}), 500

        @app.route("/api/report/period-turnover", methods=['POST'])
        def generate_period_turnover_report():
            """
            Универсальный расчет оборотов за любой период
            с автоматическим использованием сохраненных данных до блокировки
            """
            try:
                data = request.get_json() or {}
                format = data.get('format', response_formats.csv())
                start_date_str = data.get('start_date', '1900-01-01')
                end_date_str = data.get('end_date')

                if not end_date_str:
                    return jsonify({"error": "Не указана конечная дата периода"}), 400

                start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d")

                # Универсальный расчет
                period_turnovers = self.__block_service.get_combined_turnover_for_period(start_date, end_date)

                # Формируем детализированный отчет
                report_items = self._build_combined_report_items(period_turnovers)

                # Формируем ответ
                response_data = self._build_response(report_items, format)

                return jsonify({
                    "success": True,
                    "report_type": "period_turnover",
                    "period": {
                        "start_date": start_date_str,
                        "end_date": end_date_str
                    },
                    "items_count": len(report_items),
                    "data": response_data
                })

            except operation_exception as e:
                return jsonify({"error": str(e)}), 400
            except Exception as e:
                return jsonify({"error": f"Внутренняя ошибка сервера: {str(e)}"}), 500

        # СУЩЕСТВУЮЩИЕ ENDPOINTS (оставляем без изменений):

        @app.route("/api/report/blocked-turnover", methods=['POST'])
        def generate_blocked_turnover_report():
            """Генерирует отчет по оборотам до даты блокировки"""
            try:
                data = request.get_json() or {}
                format = data.get('format', response_formats.csv())

                # Рассчитываем обороты до блокировки
                blocked_turnovers = self.__block_service.calculate_blocked_turnovers()

                # Формируем ответ
                response_data = self._build_response(blocked_turnovers, format)

                return jsonify({
                    "success": True,
                    "report_type": "blocked_turnover",
                    "block_period": self.__block_service.get_block_period().isoformat(),
                    "items_count": len(blocked_turnovers),
                    "data": response_data
                })

            except operation_exception as e:
                return jsonify({"error": str(e)}), 400
            except Exception as e:
                return jsonify({"error": f"Внутренняя ошибка сервера: {str(e)}"}), 500

        @app.route("/api/settings/block-period", methods=['GET', 'POST'])
        def manage_block_period():
            """Управление датой блокировки"""
            try:
                if request.method == 'GET':
                    # Получить текущую дату блокировки
                    return jsonify({
                        "block_period": self.__block_service.get_block_period().isoformat()
                    })
                else:
                    # Установить новую дату блокировки
                    data = request.get_json()
                    if not data or 'block_period' not in data:
                        return jsonify({"error": "Не указана дата блокировки"}), 400

                    new_period = datetime.fromisoformat(data['block_period'])
                    self.__block_service.set_block_period(new_period)

                    return jsonify({
                        "success": True,
                        "message": "Дата блокировки обновлена",
                        "block_period": new_period.isoformat()
                    })

            except Exception as e:
                return jsonify({"error": str(e)}), 400

        @app.route("/api/report/blocked-turnover/recalculate", methods=['POST'])
        def recalculate_blocked_turnovers():
            """Принудительный пересчет оборотов до блокировки"""
            try:
                blocked_turnovers = self.__block_service.recalculate_blocked_turnovers()

                return jsonify({
                    "success": True,
                    "message": "Обороты до блокировки пересчитаны",
                    "items_count": len(blocked_turnovers),
                    "block_period": self.__block_service.get_block_period().isoformat()
                })

            except Exception as e:
                return jsonify({"error": str(e)}), 500

    # ДОБАВЛЯЕМ МЕТОДЫ ДЛЯ КОМБИНИРОВАННОГО ОТЧЕТА:

    def _build_combined_report_items(self, combined_turnovers: list) -> list:
        """
        Строит строки отчета для комбинированного расчета
        с детализацией по периодам
        """
        report_items = []

        for blocked_item in combined_turnovers:
            item = combined_turnover_item()

            # Заполняем基本信息
            item.nomenclature_name = blocked_item.nomenclature_name
            item.nomenclature_code = blocked_item.nomenclature_id
            item.storage_name = blocked_item.storage_name
            item.storage_code = blocked_item.storage_id
            item.unit_name = blocked_item.unit_name

            # Заполняем обороты по периодам
            item.blocked_period_income = blocked_item.blocked_period_income
            item.blocked_period_outcome = blocked_item.blocked_period_outcome
            item.fresh_period_income = blocked_item.fresh_period_income
            item.fresh_period_outcome = blocked_item.fresh_period_outcome

            # Рассчитываем общие обороты
            item.total_income = blocked_item.blocked_income
            item.total_outcome = blocked_item.blocked_outcome

            # Сальдо на начало = обороты до блокировки
            item.start_balance = blocked_item.blocked_period_income - blocked_item.blocked_period_outcome

            # Сальдо на конец = общие обороты
            item.end_balance = item.total_income - item.total_outcome

            report_items.append(item)

        return report_items

    # СУЩЕСТВУЮЩИЕ МЕТОДЫ (оставляем без изменений):

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

            # Формируем строки отчета с учетом блокировки
            report_items = self._build_report_items_with_blocked(grouped_data)

            return report_items

        except Exception as e:
            raise operation_exception(f"Ошибка генерации ОСВ: {str(e)}")

    def _build_report_items_with_blocked(self, grouped_data: dict) -> list:
        """
        Строит строки отчета с учетом оборотов до блокировки
        """
        report_items = []

        for key, group_data in grouped_data.items():
            item = turnover_item()

            item.nomenclature_name = group_data['nomenclature'].name
            item.nomenclature_code = group_data['nomenclature'].unique_code
            item.storage_name = group_data['storage'].name
            item.storage_code = group_data['storage'].unique_code
            item.unit_name = group_data['unit'].name if group_data['unit'] else ""

            # Рассчитываем обороты за период
            for transaction in group_data['transactions']:
                if transaction.value > 0:
                    item.income += Decimal(str(transaction.value))
                else:
                    item.outcome += Decimal(str(abs(transaction.value)))

            # Начальное сальдо = обороты до блокировки
            blocked_item = self.__block_service.get_blocked_turnover_for_item(
                group_data['nomenclature'].unique_code,
                group_data['storage'].unique_code
            )

            if blocked_item:
                item.start_balance = blocked_item.blocked_income - blocked_item.blocked_outcome
            else:
                item.start_balance = Decimal('0.0')

            # Сальдо на конец
            item.end_balance = item.start_balance + item.income - item.outcome

            report_items.append(item)

        return report_items

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
        return self._build_report_items_with_blocked(grouped_data)