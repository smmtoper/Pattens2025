from Src.reposity import reposity
from Src.Models.range_model import range_model
from Src.Models.group_model import group_model
from Src.Models.nomenclature_model import nomenclature_model
from Src.Core.validator import validator, argument_exception, operation_exception
import os
import json
from Src.Models.receipt_model import receipt_model
from Src.Models.receipt_item_model import receipt_item_model
from Src.Dtos.nomenclature_dto import nomenclature_dto
from Src.Dtos.range_dto import range_dto
from Src.Dtos.category_dto import category_dto
from Src.Dtos.storage_dto import storage_dto
from Src.Models.storage_model import storage_model
from Src.Models.transaction_model import transaction_model
from Src.Dtos.transaction_dto import transaction_dto
from Src.Logics.turnover_report_service import turnover_report_service


# Добавляем импорт filter_service
from Src.Logics.filter_service import filter_service


class start_service:
    # Репозиторий
    __repo: reposity = reposity()

    # Сервис фильтрации
    __filter_service: filter_service = None

    # Рецепт по умолчанию
    __default_receipt: receipt_model

    # Словарь который содержит загруженные и инициализованные инстансы нужных объектов
    # Ключ - id записи, значение - abstract_model
    __cache = {}

    # Наименование файла (полный путь)
    __full_file_name: str = ""

    # Описание ошибки
    __error_message: str = ""

    # Сервис ОСВ
    __turnover_service: turnover_report_service = None

    def __init__(self):
        self.__repo.initalize()
        # Инициализируем сервис фильтрации
        self.__filter_service = filter_service()
        # Инициализируем сервис ОСВ
        self.__turnover_service = turnover_report_service()
    @property
    def filter_service(self):
        return self.__filter_service

    # Singletone
    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(start_service, cls).__new__(cls)
        return cls.instance

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

    # Информация об ошибке
    @property
    def error_message(self) -> str:
        return self.__error_message

        # Сервис фильтрации

    @property
    def filter_service(self) -> filter_service:
        return self.__filter_service

    # Загрузить настройки из Json файла
    def load(self) -> bool:
        if self.__full_file_name == "":
            raise operation_exception("Не найден файл настроек!")

        try:
            # ИЗМЕНЕНИЕ: добавляем кодировку utf-8
            with open(self.__full_file_name, 'r', encoding='utf-8') as file_instance:
                settings = json.load(file_instance)
                return self.convert(settings)
        except Exception as e:
            self.__error_message = str(e)
            return False

    # Сохранить элемент в репозитории
    def __save_item(self, key: str, dto, item):
        validator.validate(key, str)
        item.unique_code = dto.id
        self.__cache.setdefault(dto.id, item)
        self.__repo.data[key].append(item)

    # Загрузить единицы измерений
    def __convert_ranges(self, data: dict) -> bool:
        validator.validate(data, dict)
        ranges = data['ranges'] if 'ranges' in data else []
        if len(ranges) == 0:
            return False

        for range in ranges:
            dto = range_dto().create(range)
            item = range_model.from_dto(dto, self.__cache)
            self.__save_item(reposity.range_key(), dto, item)

        return True

    # Загрузить группы номенклатуры
    def __convert_groups(self, data: dict) -> bool:
        validator.validate(data, dict)
        categories = data['categories'] if 'categories' in data else []
        if len(categories) == 0:
            return False

        for category in categories:
            dto = category_dto().create(category)
            item = group_model.from_dto(dto, self.__cache)
            self.__save_item(reposity.group_key(), dto, item)

        return True

    # Загрузить склады
    def __convert_storages(self, data: dict) -> bool:
        validator.validate(data, dict)
        storages = data['storages'] if 'storages' in data else []
        if len(storages) == 0:
            return False

        for storage in storages:
            dto = storage_dto().create(storage)
            item = storage_model.from_dto(dto, self.__cache)
            self.__save_item(reposity.storage_key(), dto, item)

        return True

        # Загрузить тестовые транзакции

    def __convert_transactions(self, data: list) -> bool:
        validator.validate(data, list)
        if len(data) == 0:
            return False

        for transaction in data:
            dto = transaction_dto().create(transaction)
            item = transaction_model.from_dto(dto, self.__cache)
            self.__save_item(reposity.transaction_key(), dto, item)

        return True

        # Загрузить номенклатуру

    def __convert_nomenclatures(self, data: dict) -> bool:
        validator.validate(data, dict)
        nomenclatures = data['nomenclatures'] if 'nomenclatures' in data else []
        if len(nomenclatures) == 0:
            return False

        for nomenclature in nomenclatures:
            dto = nomenclature_dto().create(nomenclature)
            item = nomenclature_model.from_dto(dto, self.__cache)
            self.__save_item(reposity.nomenclature_key(), dto, item)

        return True

        # Обработать справочники

    def __convert_references(self, data: dict) -> bool:
        validator.validate(data, dict)

        try:
            self.__convert_ranges(data)
            self.__convert_groups(data)
            self.__convert_nomenclatures(data)
            self.__convert_storages(data)
            return True
        except Exception as e:
            self.__error_message = str(e)
            return False

    # Обработать рецепт по умолчанию
    def __convert_receipt(self, data: dict) -> bool:
        validator.validate(data, dict)

        try:
            # 1 Созданим рецепт
            cooking_time = data['cooking_time'] if 'cooking_time' in data else ""
            portions = int(data['portions']) if 'portions' in data else 0
            name = data['name'] if 'name' in data else "НЕ ИЗВЕСТНО"
            self.__default_receipt = receipt_model.create(name, cooking_time, portions)

            # Загрузим шаги приготовления
            steps = data['steps'] if 'steps' in data else []
            for step in steps:
                if step.strip() != "":
                    self.__default_receipt.steps.append(step)

            # Собираем рецепт
            compositions = data['composition'] if 'composition' in data else []
            for composition in compositions:
                # TODO: Заменить код через Dto
                namnomenclature_id = composition['nomenclature_id'] if 'nomenclature_id' in composition else ""
                range_id = composition['range_id'] if 'range_id' in composition else ""
                value = composition['value'] if 'value' in composition else ""
                nomenclature = self.__cache[namnomenclature_id] if namnomenclature_id in self.__cache else None
                range = self.__cache[range_id] if range_id in self.__cache else None
                item = receipt_item_model.create(nomenclature, range, value)
                self.__default_receipt.composition.append(item)

            # Сохраняем рецепт
            self.__repo.data[reposity.receipt_key()].append(self.__default_receipt)
            return True
        except Exception as e:
            self.__error_message = str(e)
            return False

    # Обработать полученный словарь
    def convert(self, data: dict) -> bool:
        validator.validate(data, dict)
        loaded_references = True
        loaded_receipt = True
        loaded_transactions = True

        # Обработать справочники
        if "default_refenences" in data.keys():
            default_refenences = data["default_refenences"]
            loaded_references = self.__convert_references(default_refenences)

        # Обработать рецепт
        if "default_receipt" in data.keys():
            default_receipt = data["default_receipt"]
            loaded_receipt = self.__convert_receipt(default_receipt)

            # Загрузить транзакции
        if "default_transactions" in data.keys():
            default_transactions = data["default_transactions"]
            loaded_transactions = self.__convert_transactions(default_transactions)

        return loaded_references and loaded_receipt and loaded_transactions

    """
    Стартовый набор данных
    """

    @property
    def data(self):
        return self.__repo.data

    """
    Основной метод для генерации эталонных данных
    """

    def start(self):
        self.file_name = "settings.json"
        result = self.load()
        if result == False:
            raise operation_exception(
                f"Невозможно сформировать стартовый набор данных!\nОписание: {self.error_message}")
    @property
    def turnover_service(self):
        return self.__turnover_service