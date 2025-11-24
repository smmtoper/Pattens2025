from Src.Models.settings_model import settings_model
from Src.Core.validator import argument_exception
from Src.Core.validator import operation_exception
from Src.Core.validator import validator
from Src.Models.company_model import company_model
from Src.Core.common import common
from Src.Core.response_formats import response_formats
from Src.Logics.block_period_service import block_period_service
from Src.reposity import reposity
from flask import request, jsonify
from datetime import datetime
from decimal import Decimal
import os
import json


####################################################
# Менеджер настроек.
# Предназначен для управления настройками и хранения параметров приложения
class settings_manager:
    # Наименование файла (полный путь)
    __full_file_name: str = ""

    # Настройки
    __settings: settings_model = None

    # Сервис блокировки
    __block_service: block_period_service = None

    # Singletone
    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(settings_manager, cls).__new__(cls)
        return cls.instance

    def __init__(self):
        self.set_default()
        self.__block_service = block_period_service()
        self.__repo = reposity()

    # Текущие настройки
    @property
    def settings(self) -> settings_model:
        return self.__settings

    # Текущий файл
    @property
    def file_name(self) -> str:
        return self.__full_file_name

    # Полный путь к файлу настроек
    @file_name.setter
    def file_name(self, value: str):
        validator.validate(value, str)
        full_file_name = os.path.abspath(value)
        if os.path.exists(full_file_name):
            self.__full_file_name = full_file_name.strip()
        else:
            raise argument_exception(f'Не найден файл настроек {full_file_name}')

    # Загрузить настройки из Json файла
    def load(self) -> bool:
        if self.__full_file_name == "":
            raise operation_exception("Не найден файл настроек!")

        try:
            with open(self.__full_file_name, 'r', encoding='utf-8') as file_instance:
                settings = json.load(file_instance)

                if "company" in settings.keys():
                    data = settings["company"]
                    result = self.convert(data)

                if "default_format" in settings.keys() and result == True:
                    data = settings["default_format"]
                    if data in response_formats.list_all_formats():
                        self.settings.default_response_format = data

                # Загружаем дату блокировки если есть
                if "block_period" in settings.keys():
                    block_period_str = settings["block_period"]
                    try:
                        block_period = self._parse_date(block_period_str)
                        self.settings.block_period = block_period
                        self.__block_service.set_block_period(block_period)
                    except:
                        pass  # Игнорируем ошибки загрузки даты блокировки

                return result
        except Exception as e:
            print(f"Ошибка загрузки настроек: {e}")
            return False

    # Обработать полученный словарь
    def convert(self, data: dict) -> bool:
        validator.validate(data, dict)

        fields = common.get_fields(self.__settings.company)
        matching_keys = list(filter(lambda key: key in fields, data.keys()))

        try:
            for key in matching_keys:
                setattr(self.__settings.company, key, data[key])
        except:
            return False

        return True

    # Параметры настроек по умолчанию
    def set_default(self):
        company = company_model()
        company.name = "Рога и копыта"
        company.inn = -1

        self.__settings = settings_model()
        self.__settings.company = company

    # ДОБАВЛЯЕМ API МЕТОДЫ ДЛЯ ТРЕХ ЗАПРОСОВ

    def setup_routes(self, app):
        """Настройка маршрутов API для управления настройками"""

        # 5. POST запрос для изменения даты блокировки
        @app.route("/api/settings/block-period", methods=['POST'])
        def set_block_period():
            """
            POST запрос для изменения даты блокировки в настройках Settings_model
            Body: {"block_period": "2024-01-01"}
            """
            try:
                return self._set_block_period()

            except operation_exception as e:
                return jsonify({"error": str(e)}), 400
            except Exception as e:
                return jsonify({"error": f"Внутренняя ошибка сервера: {str(e)}"}), 500

        # 6. GET запрос для получения текущей даты блокировки
        @app.route("/api/settings/block-period", methods=['GET'])
        def get_block_period():
            """
            GET запрос который возвращает текущую дату блокировки
            """
            try:
                return self._get_block_period()

            except operation_exception as e:
                return jsonify({"error": str(e)}), 400
            except Exception as e:
                return jsonify({"error": f"Внутренняя ошибка сервера: {str(e)}"}), 500

        # 7. GET запрос для получения остатков на указанную дату
        @app.route("/api/report/balances", methods=['GET'])
        def get_balances_by_date():
            """
            GET запрос который возвращает остатки на указанную дату
            Query Parameters: date=2024-10-01
            """
            try:
                return self._get_balances_by_date()

            except operation_exception as e:
                return jsonify({"error": str(e)}), 400
            except Exception as e:
                return jsonify({"error": f"Внутренняя ошибка сервера: {str(e)}"}), 500

        # Дополнительный endpoint для получения всех настроек
        @app.route("/api/settings", methods=['GET'])
        def get_all_settings():
            """Получить все настройки приложения"""
            try:
                return jsonify({
                    "success": True,
                    "settings": {
                        "block_period": self.__settings.block_period.isoformat(),
                        "block_period_display": self.__settings.block_period.strftime("%Y-%m-%d"),
                        "default_response_format": self.__settings.default_response_format,
                        "company": {
                            "name": self.__settings.company.name if self.__settings.company else None,
                            "inn": self.__settings.company.inn if self.__settings.company else None
                        } if self.__settings.company else None
                    }
                })

            except Exception as e:
                return jsonify({"error": str(e)}), 500

    def _get_block_period(self):
        """
        6. GET запрос - возвращает текущую дату блокировки
        """
        current_block_period = self.__settings.block_period

        return jsonify({
            "success": True,
            "block_period": current_block_period.isoformat(),
            "block_period_display": current_block_period.strftime("%Y-%m-%d"),
            "message": "Текущая дата блокировки"
        })

    def _set_block_period(self):
        """
        5. POST запрос - меняет дату блокировки в настройках Settings_model
        """
        data = request.get_json()

        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        if 'block_period' not in data:
            return jsonify({"error": "Не указана дата блокировки"}), 400

        try:
            # Парсим дату из разных форматов
            block_period_str = data['block_period']
            new_block_period = self._parse_date(block_period_str)

            # Сохраняем старую дату
            old_block_period = self.__settings.block_period

            # Устанавливаем новую дату блокировки в settings_model
            self.__settings.block_period = new_block_period

            # Также обновляем дату в block_service для согласованности
            self.__block_service.set_block_period(new_block_period)

            # Сохраняем настройки в файл
            self._save_settings_to_file()

            return jsonify({
                "success": True,
                "message": "Дата блокировки успешно обновлена",
                "old_block_period": old_block_period.isoformat(),
                "old_block_period_display": old_block_period.strftime("%Y-%m-%d"),
                "new_block_period": new_block_period.isoformat(),
                "new_block_period_display": new_block_period.strftime("%Y-%m-%d")
            })

        except ValueError as e:
            return jsonify({"error": f"Неверный формат даты: {str(e)}"}), 400
        except Exception as e:
            return jsonify({"error": str(e)}), 400

    def _get_balances_by_date(self):
        """
        7. GET запрос - возвращает остатки на указанную дату
        """
        # Получаем дату из query parameters
        date_str = request.args.get('date')

        if not date_str:
            return jsonify({"error": "Не указана дата (параметр 'date')"}), 400

        try:
            # Парсим дату
            target_date = self._parse_date(date_str)

            # Рассчитываем остатки на указанную дату
            balances = self._calculate_balances_by_date(target_date)

            return jsonify({
                "success": True,
                "date": target_date.isoformat(),
                "date_display": target_date.strftime("%Y-%m-%d"),
                "balances": balances,
                "items_count": len(balances),
                "message": f"Остатки на {target_date.strftime('%Y-%m-%d')}"
            })

        except ValueError as e:
            return jsonify({"error": f"Неверный формат даты: {str(e)}"}), 400
        except Exception as e:
            return jsonify({"error": str(e)}), 400

    def _calculate_balances_by_date(self, target_date: datetime) -> list:
        """
        Рассчитывает остатки на указанную дату
        """
        # Используем комбинированный расчет до целевой даты
        turnovers = self.__block_service.calculate_combined_turnovers(target_date)

        balances = []
        for turnover in turnovers:
            balance_item = {
                "nomenclature_id": turnover.nomenclature_id,
                "nomenclature_name": turnover.nomenclature_name,
                "storage_id": turnover.storage_id,
                "storage_name": turnover.storage_name,
                "unit_id": turnover.unit_id,
                "unit_name": turnover.unit_name,
                "total_income": float(turnover.blocked_income),
                "total_outcome": float(turnover.blocked_outcome),
                "balance": float(turnover.blocked_income - turnover.blocked_outcome),
                "block_period_income": float(turnover.blocked_period_income),
                "block_period_outcome": float(turnover.blocked_period_outcome),
                "fresh_period_income": float(turnover.fresh_period_income),
                "fresh_period_outcome": float(turnover.fresh_period_outcome)
            }
            balances.append(balance_item)

        return balances

    def _parse_date(self, date_str):
        """Парсит дату из различных форматов"""
        formats = [
            "%Y-%m-%dT%H:%M:%S",  # 2024-01-01T00:00:00
            "%Y-%m-%d %H:%M:%S",  # 2024-01-01 00:00:00
            "%Y-%m-%d",  # 2024-01-01
            "%d.%m.%Y",  # 01.01.2024
            "%d/%m/%Y",  # 01/01/2024
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        raise ValueError(f"Не удалось распознать формат даты: {date_str}")

    def _save_settings_to_file(self):
        """Сохраняет настройки в файл"""
        try:
            if self.__full_file_name:
                settings_data = {
                    "company": {
                        "name": self.__settings.company.name,
                        "inn": self.__settings.company.inn,
                        "bic": getattr(self.__settings.company, 'bic', None),
                        "corr_account": getattr(self.__settings.company, 'corr_account', None),
                        "account": getattr(self.__settings.company, 'account', None),
                        "ownership": getattr(self.__settings.company, 'ownership', None)
                    },
                    "default_format": self.__settings.default_response_format,
                    "block_period": self.__settings.block_period.isoformat()
                }

                with open(self.__full_file_name, 'w', encoding='utf-8') as f:
                    json.dump(settings_data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            print(f"⚠️ Предупреждение: не удалось сохранить настройки в файл: {e}")

    def get_block_service(self) -> block_period_service:
        """Получить сервис блокировки"""
        return self.__block_service