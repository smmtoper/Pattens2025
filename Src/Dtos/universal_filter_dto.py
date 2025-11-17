from Src.Core.abstract_dto import abstract_dto
from Src.Core.filter_type import FilterType
from Src.Core.validator import validator


class universal_filter_dto(abstract_dto):
    """
    Универсальная DTO модель для фильтрации DOMAIN моделей
    """
    __field_name: str = ""
    __value: str = ""
    __filter_type: FilterType = FilterType.EQUALS
    __model_type: str = ""  # Тип модели: nomenclature, group, range, receipt
    __nested_field: str = ""  # Для поиска во вложенных структурах

    @property
    def field_name(self) -> str:
        return self.__field_name

    @field_name.setter
    def field_name(self, value: str):
        validator.validate(value, str)
        self.__field_name = value.strip()

    @property
    def value(self) -> str:
        return self.__value

    @value.setter
    def value(self, value: str):
        validator.validate(value, str)
        self.__value = value.strip()

    @property
    def filter_type(self) -> FilterType:
        return self.__filter_type

    @filter_type.setter
    def filter_type(self, value: FilterType):
        validator.validate(value, FilterType)
        self.__filter_type = value

    @property
    def model_type(self) -> str:
        return self.__model_type

    @model_type.setter
    def model_type(self, value: str):
        validator.validate(value, str)
        allowed_types = ["nomenclature", "group", "range", "receipt"]
        if value not in allowed_types:
            raise ValueError(f"Некорректный тип модели. Допустимые значения: {allowed_types}")
        self.__model_type = value.strip()

    @property
    def nested_field(self) -> str:
        return self.__nested_field

    @nested_field.setter
    def nested_field(self, value: str):
        validator.validate(value, str)
        self.__nested_field = value.strip()

    def create(self, data) -> "universal_filter_dto":
        """
        Фабричный метод для создания из словаря
        """
        validator.validate(data, dict)

        if "field_name" in data:
            self.field_name = data["field_name"]
        if "value" in data:
            self.value = data["value"]
        if "filter_type" in data:
            self.filter_type = FilterType(data["filter_type"])
        if "model_type" in data:
            self.model_type = data["model_type"]
        if "nested_field" in data:
            self.nested_field = data["nested_field"]

        return self