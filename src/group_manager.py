"""
Модуль для управления группами
"""
from typing import List, Set
from src.utils.file_parser import FileParser
from src.utils.logger import setup_logger

logger = setup_logger()


class GroupManager:
    """Менеджер для работы с группами"""
    
    def __init__(self):
        """Инициализация менеджера групп"""
        self.selected_groups: List[str] = []
        self.parser = FileParser()
    
    def load_from_file(self, filepath: str) -> List[str]:
        """
        Загрузка групп из файла
        
        Args:
            filepath: Путь к файлу
            
        Returns:
            Список адресов групп
        """
        try:
            groups = self.parser.parse_file(filepath)
            self.selected_groups.extend(groups)
            # Удаляем дубликаты
            self.selected_groups = list(dict.fromkeys(self.selected_groups))
            logger.info(f"Загружено {len(groups)} групп из файла {filepath}")
            return groups
        except Exception as e:
            logger.error(f"Ошибка загрузки групп из файла: {e}")
            return []
    
    def add_group(self, group_address: str) -> bool:
        """
        Добавление группы в список
        
        Args:
            group_address: Адрес группы
            
        Returns:
            True если группа добавлена, False если невалидная
        """
        normalized = self.parser.normalize_address(group_address)
        if normalized:
            if normalized not in self.selected_groups:
                self.selected_groups.append(normalized)
                logger.info(f"Добавлена группа: {normalized}")
                return True
            else:
                logger.warning(f"Группа уже в списке: {normalized}")
                return False
        else:
            logger.warning(f"Невалидный адрес группы: {group_address}")
            return False
    
    def remove_group(self, group_address: str) -> bool:
        """
        Удаление группы из списка
        
        Args:
            group_address: Адрес группы
            
        Returns:
            True если группа удалена
        """
        normalized = self.parser.normalize_address(group_address)
        if normalized and normalized in self.selected_groups:
            self.selected_groups.remove(normalized)
            logger.info(f"Удалена группа: {normalized}")
            return True
        return False
    
    def clear_groups(self):
        """Очистка списка групп"""
        self.selected_groups.clear()
        logger.info("Список групп очищен")
    
    def get_groups(self) -> List[str]:
        """
        Получение списка выбранных групп
        
        Returns:
            Список адресов групп
        """
        return self.selected_groups.copy()
    
    def validate_address(self, address: str) -> bool:
        """
        Валидация адреса группы
        
        Args:
            address: Адрес для проверки
            
        Returns:
            True если адрес валидный
        """
        return self.parser.validate_address(address)
    
    def filter_duplicates(self, groups: List[str]) -> List[str]:
        """
        Фильтрация дубликатов из списка групп
        
        Args:
            groups: Список групп
            
        Returns:
            Список без дубликатов
        """
        seen: Set[str] = set()
        unique_groups = []
        for group in groups:
            normalized = self.parser.normalize_address(group)
            if normalized and normalized not in seen:
                seen.add(normalized)
                unique_groups.append(normalized)
        return unique_groups

