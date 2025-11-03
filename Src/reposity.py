from Src.Core.common import common

"""
Репозиторий данных
"""
class reposity:
    __data = {}

    @property
    def data(self):
        return self.__data
    
    """
    Ключ для единц измерений
    """
    @staticmethod
    def range_key():
        return "range_model"
    

    """
    Ключ для категорий
    """
    @staticmethod
    def group_key():
        return "group_model"
    
    """
    Ключ для склада
    """
    @staticmethod
    def storage_key():
        return "storage_key"
        
    """
    Ключ для транзакций
    """    
    def transaction_key():
        return "transaction_key"    
    

    """
    Ключ для номенклатуры
    """
    @staticmethod
    def nomenclature_key():
        return "nomenclature_model"
    

    """
    Ключ для рецептов
    """
    @staticmethod
    def receipt_key():
        return "receipt_model"
    
    """
    Получить список всех ключей
    Источник: https://github.com/Alyona1619
    """
    @staticmethod
    def keys() -> list:
        result = []
        methods = [method for method in dir(reposity) if
                    callable(getattr(reposity, method)) and method.endswith('_key')]
        for method in methods:
            key = getattr(reposity, method)()
            result.append(key)

        return result

    
    """
    Инициализация
    """
    def initalize(self):
        keys = reposity.keys()
        for key in keys:
            self.__data[ key ] = []
    
    
