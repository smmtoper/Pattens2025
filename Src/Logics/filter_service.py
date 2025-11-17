from flask import request, jsonify
from Src.Dtos.universal_filter_dto import universal_filter_dto
from Src.Core.universal_prototype import universal_prototype
from Src.Core.validator import validator, operation_exception
from Src.Models.nomenclature_model import nomenclature_model
from Src.Models.group_model import group_model
from Src.Models.range_model import range_model
from Src.Models.receipt_model import receipt_model
from Src.Core.response_formats import response_formats
from Src.Logics.factory_entities import factory_entities
from Src.reposity import reposity

"""
Сервис для фильтрации данных через REST API (Flask version)
"""


class filter_service:

    def __init__(self):
        self.__repo = reposity()

    def setup_routes(self, app):
        """Настройка маршрутов API для Flask"""

        @app.route("/api/filter/<model_type>", methods=['POST'])
        def filter_data(model_type):
            """
            POST запрос для фильтрации данных по DOMAIN модели

            Args:
                model_type: Тип DOMAIN модели (nomenclature, group, range, receipt)

            Body:
                filter_dto: DTO модель фильтрации
                format: Формат ответа (csv, markdown) - опционально
            """
            try:
                # Получаем данные из запроса
                data = request.get_json()
                if not data:
                    return jsonify({"error": "No JSON data provided"}), 400

                format = data.get('format', response_formats.csv())

                # Создаем DTO фильтрации
                filter_dto = universal_filter_dto()
                filter_dto.create(data)

                # Валидация типа модели
                validator.validate(model_type, str)
                allowed_types = ["nomenclature", "group", "range", "receipt"]
                if model_type not in allowed_types:
                    return jsonify({"error": f"Неподдерживаемый тип модели. Допустимо: {allowed_types}"}), 400

                # Устанавливаем тип модели в DTO
                filter_dto.model_type = model_type

                # Получаем данные в зависимости от типа модели
                data_list = self._get_data_by_model_type(model_type)

                if not data_list:
                    return jsonify({"error": f"Данные для модели {model_type} не найдены"}), 404

                # Создаем прототип и применяем фильтр
                prototype = universal_prototype(data_list)
                filtered_prototype = prototype.apply_filter(filter_dto)

                # Формируем ответ в нужном формате
                response_data = self._build_response(filtered_prototype.data, format)

                return jsonify({
                    "success": True,
                    "model_type": model_type,
                    "filter_applied": filter_dto.field_name or filter_dto.nested_field,
                    "filter_value": filter_dto.value,
                    "filter_type": filter_dto.filter_type.value,
                    "items_count": len(filtered_prototype.data),
                    "data": response_data
                })

            except operation_exception as e:
                return jsonify({"error": str(e)}), 400
            except Exception as e:
                return jsonify({"error": f"Внутренняя ошибка сервера: {str(e)}"}), 500

        @app.route("/api/filter/fields/<model_type>", methods=['GET'])
        def get_filter_fields(model_type):
            """
            Возвращает список полей, по которым можно фильтровать для указанной модели
            """
            try:
                validator.validate(model_type, str)

                fields_info = {
                    "nomenclature": {
                        "basic_fields": ["name", "unique_code"],
                        "specific_fields": ["group", "range"],
                        "nested_examples": [
                            "group.name",
                            "range.name",
                            "range.base.name"
                        ]
                    },
                    "group": {
                        "basic_fields": ["name", "unique_code"],
                        "specific_fields": [],
                        "nested_examples": []
                    },
                    "range": {
                        "basic_fields": ["name", "unique_code"],
                        "specific_fields": ["value", "base"],
                        "nested_examples": [
                            "base.name",
                            "base.base.name"
                        ]
                    },
                    "receipt": {
                        "basic_fields": ["name", "unique_code"],
                        "specific_fields": ["portions", "cooking_time"],
                        "nested_examples": [
                            "composition.nomenclature.name",
                            "composition.range.name"
                        ]
                    }
                }

                if model_type not in fields_info:
                    return jsonify({"error": "Неподдерживаемый тип модели"}), 400

                return jsonify({
                    "model_type": model_type,
                    "supported_fields": fields_info[model_type]
                })

            except Exception as e:
                return jsonify({"error": str(e)}), 500

    def _get_data_by_model_type(self, model_type: str) -> list:
        """
        Получает данные по типу модели из репозитория
        """
        try:
            if model_type == "nomenclature":
                return self.__repo.data.get(reposity.nomenclature_key(), [])
            elif model_type == "group":
                return self.__repo.data.get(reposity.group_key(), [])
            elif model_type == "range":
                return self.__repo.data.get(reposity.range_key(), [])
            elif model_type == "receipt":
                return self.__repo.data.get(reposity.receipt_key(), [])
            else:
                return []

        except Exception as e:
            raise operation_exception(f"Ошибка получения данных для модели {model_type}: {str(e)}")

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