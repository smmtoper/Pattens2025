from enum import Enum

class FilterType(Enum):
    """
    Перечисление с вариантами фильтрации
    """
    EQUALS = "equals"      # Полное совпадение
    LIKE = "like"         # Вхождение строки