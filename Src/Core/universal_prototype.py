from Src.Core.prototype import prototype
from Src.Core.validator import validator
from Src.Dtos.universal_filter_dto import universal_filter_dto
from Src.Core.filter_type import FilterType
from Src.Core.common import common
from Src.Models.nomenclature_model import nomenclature_model
from Src.Models.group_model import group_model
from Src.Models.range_model import range_model
from Src.Models.receipt_model import receipt_model


class universal_prototype(prototype):
    """
    Универсальный прототип для фильтрации всех DOMAIN моделей
    Поддерживает: nomenclature, group, range, receipt
    """

    def __init__(self, data: list):
        super().__init__(data)

    def clone(self, data: list = None) -> "universal_prototype":
        inner_data = self.data if data is None else data
        return universal_prototype(inner_data)

    def apply_filter(self, filter_dto: universal_filter_dto) -> "universal_prototype":
        """
        Основной метод фильтрации для всех DOMAIN моделей
        """
        validator.validate(filter_dto, universal_filter_dto)

        # Проверяем, что тип модели соответствует данным
        self.__validate_model_type(filter_dto.model_type)

        filtered_data = universal_prototype.__filter_by_dto(self.data, filter_dto)
        return self.clone(filtered_data)

    @staticmethod
    def __validate_model_type(model_type: str):
        """Проверяет корректность типа модели"""
        allowed_types = ["nomenclature", "group", "range", "receipt"]
        if model_type not in allowed_types:
            raise ValueError(f"Неподдерживаемый тип модели: {model_type}. Допустимо: {allowed_types}")

    @staticmethod
    def __filter_by_dto(data: list, filter_dto: universal_filter_dto) -> list:
        """
        Универсальная фильтрация по DTO для всех моделей
        """
        if len(data) == 0:
            return []

        result = []

        for item in data:
            if universal_prototype.__item_matches_filter(item, filter_dto):
                result.append(item)

        return result

    @staticmethod
    def __item_matches_filter(item, filter_dto: universal_filter_dto) -> bool:
        """
        Проверяет соответствие элемента критериям фильтрации
        Поддерживает все DOMAIN модели и их специфичные поля
        """
        # Базовые поля, общие для всех entity_model
        if filter_dto.field_name in ['name', 'unique_code']:
            field_value = getattr(item, filter_dto.field_name, "")
            return universal_prototype.__apply_filter_logic(str(field_value), filter_dto)

        # Специфичные поля для разных моделей
        elif universal_prototype.__is_model_specific_field(item, filter_dto):
            return universal_prototype.__check_model_specific_field(item, filter_dto)

        # Вложенные структуры - ОСНОВНОЙ МЕТОД ДЛЯ ПУНКТА 4
        elif filter_dto.nested_field:
            return universal_prototype.__check_nested_structure(item, filter_dto)

        return False

    @staticmethod
    def __is_model_specific_field(item, filter_dto: universal_filter_dto) -> bool:
        """Проверяет, является ли поле специфичным для конкретной модели"""
        specific_fields = {
            'nomenclature_model': ['group', 'range'],
            'range_model': ['value', 'base'],
            'receipt_model': ['portions', 'cooking_time', 'steps', 'composition'],
            'group_model': []  # Группа имеет только базовые поля
        }

        model_class = item.__class__.__name__
        return (filter_dto.field_name in specific_fields.get(model_class, []))

    @staticmethod
    def __check_model_specific_field(item, filter_dto: universal_filter_dto) -> bool:
        """Обрабатывает специфичные поля разных моделей"""
        try:
            field_value = getattr(item, filter_dto.field_name)

            # Для объектных полей (group, range, base) берем name
            if hasattr(field_value, 'name'):
                return universal_prototype.__apply_filter_logic(field_value.name, filter_dto)
            # Для примитивных полей
            else:
                return universal_prototype.__apply_filter_logic(str(field_value), filter_dto)

        except (AttributeError, ValueError):
            return False

    @staticmethod
    def __check_nested_structure(item, filter_dto: universal_filter_dto) -> bool:
        """
        Рекурсивный поиск по вложенным структурам - РЕАЛИЗАЦИЯ ПУНКТА 4
        Поддерживает многоуровневые вложенности через точку (.)

        Примеры использования:
        - "range.base.name"        - базовая единица измерения единицы измерения
        - "group.name"             - группа номенклатуры
        - "nomenclature.group.name" - группа номенклатуры номенклатуры
        - "composition.nomenclature.name" - номенклатура в составе рецепта
        """
        try:
            nested_parts = filter_dto.nested_field.split('.')
            current_obj = item

            # Рекурсивно проходим по цепочке вложенных объектов
            for part in nested_parts:
                if current_obj is None:
                    return False

                # Обработка списков/массивов (например, composition в рецепте)
                if isinstance(current_obj, list):
                    return universal_prototype.__check_nested_list(current_obj, part, filter_dto, nested_parts)

                # Обработка обычных объектов
                if hasattr(current_obj, part):
                    current_obj = getattr(current_obj, part)
                else:
                    return False

            # Применяем фильтр к конечному значению
            return universal_prototype.__apply_filter_to_nested_value(current_obj, filter_dto)

        except (AttributeError, ValueError, IndexError):
            return False

    @staticmethod
    def __check_nested_list(obj_list: list, current_part: str, filter_dto: universal_filter_dto,
                            remaining_parts: list) -> bool:
        """
        Обрабатывает вложенные структуры, когда встречается список
        Например: composition в receipt_model - это список receipt_item_model
        """
        for list_item in obj_list:
            if hasattr(list_item, current_part):
                nested_value = getattr(list_item, current_part)

                # Если остались еще уровни вложенности, продолжаем рекурсию
                if len(remaining_parts) > 1:
                    temp_obj = nested_value
                    for next_part in remaining_parts[1:]:
                        if hasattr(temp_obj, next_part):
                            temp_obj = getattr(temp_obj, next_part)
                        else:
                            break
                    else:
                        if universal_prototype.__apply_filter_to_nested_value(temp_obj, filter_dto):
                            return True
                # Если это последний уровень
                else:
                    if universal_prototype.__apply_filter_to_nested_value(nested_value, filter_dto):
                        return True
        return False

    @staticmethod
    def __apply_filter_to_nested_value(value, filter_dto: universal_filter_dto) -> bool:
        """
        Применяет фильтр к значению из вложенной структуры
        """
        if value is None:
            return False

        # Если значение - объект с именем, используем name
        if hasattr(value, 'name'):
            return universal_prototype.__apply_filter_logic(value.name, filter_dto)
        # Если значение - строка или число, конвертируем в строку
        else:
            return universal_prototype.__apply_filter_logic(str(value), filter_dto)

    @staticmethod
    def __apply_filter_logic(field_value: str, filter_dto: universal_filter_dto) -> bool:
        """
        Применяет логику фильтрации в зависимости от типа
        """
        field_value_str = str(field_value).lower()
        filter_value = filter_dto.value.lower()

        if filter_dto.filter_type == FilterType.EQUALS:
            return field_value_str == filter_value
        elif filter_dto.filter_type == FilterType.LIKE:
            return filter_value in field_value_str

        return False

    # СПЕЦИАЛЬНЫЕ МЕТОДЫ ДЛЯ ВЛОЖЕННЫХ СТРУКТУР (ПУНКТ 4)

    def filter_by_base_unit_name(self, base_unit_name: str,
                                 filter_type: FilterType = FilterType.LIKE) -> "universal_prototype":
        """
        Фильтрует единицы измерения по имени базовой единицы
        Пример: найти все единицы измерения, где базовая единица - 'грамм'
        """
        filter_dto = universal_filter_dto()
        filter_dto.nested_field = "base.name"
        filter_dto.value = base_unit_name
        filter_dto.filter_type = filter_type
        filter_dto.model_type = self.__detect_model_type()
        return self.apply_filter(filter_dto)

    def filter_by_group_name(self, group_name: str, filter_type: FilterType = FilterType.LIKE) -> "universal_prototype":
        """
        Фильтрует номенклатуру по имени группы
        Пример: найти всю номенклатуру в группе 'Мука'
        """
        filter_dto = universal_filter_dto()
        filter_dto.nested_field = "group.name"
        filter_dto.value = group_name
        filter_dto.filter_type = filter_type
        filter_dto.model_type = self.__detect_model_type()
        return self.apply_filter(filter_dto)

    def filter_by_parent_group_name(self, parent_name: str,
                                    filter_type: FilterType = FilterType.LIKE) -> "universal_prototype":
        """
        Фильтрует группы по имени родительской группы
        Пример: найти все подгруппы группы 'Бакалея'
        """
        filter_dto = universal_filter_dto()
        filter_dto.nested_field = "base.name"  # для групп base может быть родительской группой
        filter_dto.value = parent_name
        filter_dto.filter_type = filter_type
        filter_dto.model_type = self.__detect_model_type()
        return self.apply_filter(filter_dto)

    # Удобные методы для базовой фильтрации
    def filter_by_name(self, name: str, filter_type: FilterType = FilterType.LIKE) -> "universal_prototype":
        """Фильтрует по наименованию"""
        filter_dto = universal_filter_dto()
        filter_dto.field_name = "name"
        filter_dto.value = name
        filter_dto.filter_type = filter_type
        filter_dto.model_type = self.__detect_model_type()
        return self.apply_filter(filter_dto)

    def filter_by_code(self, code: str, filter_type: FilterType = FilterType.EQUALS) -> "universal_prototype":
        """Фильтрует по уникальному коду"""
        filter_dto = universal_filter_dto()
        filter_dto.field_name = "unique_code"
        filter_dto.value = code
        filter_dto.filter_type = filter_type
        filter_dto.model_type = self.__detect_model_type()
        return self.apply_filter(filter_dto)

    def __detect_model_type(self) -> str:
        """Автоматически определяет тип модели по данным"""
        if len(self.data) == 0:
            return "unknown"

        first_item = self.data[0]
        class_name = first_item.__class__.__name__.lower()

        type_mapping = {
            'nomenclature_model': 'nomenclature',
            'group_model': 'group',
            'range_model': 'range',
            'receipt_model': 'receipt'
        }

        return type_mapping.get(class_name, 'unknown')