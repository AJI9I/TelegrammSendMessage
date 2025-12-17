"""
Модуль для парсинга файла с адресами групп
"""
import re
from typing import List, Optional
from pathlib import Path


class FileParser:
    """Парсер файлов с адресами групп Telegram"""
    
    # Паттерны для различных форматов адресов
    USERNAME_PATTERN = re.compile(r'@?([a-zA-Z0-9_]{5,32})')
    FULL_LINK_PATTERN = re.compile(r'https?://t\.me/([a-zA-Z0-9_]{5,32})')
    SHORT_LINK_PATTERN = re.compile(r't\.me/([a-zA-Z0-9_]{5,32})')
    INVITE_LINK_PATTERN = re.compile(r'(https?://)?t\.me/joinchat/([a-zA-Z0-9_-]+)')
    
    @staticmethod
    def parse_file(filepath: str) -> List[str]:
        """
        Парсинг файла с адресами групп
        
        Args:
            filepath: Путь к файлу
            
        Returns:
            Список нормализованных адресов групп
            
        Raises:
            FileNotFoundError: Если файл не найден
        """
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Файл не найден: {filepath}")
        
        groups = []
        with open(path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('#'):  # Пропускаем пустые строки и комментарии
                    continue
                
                normalized = FileParser.normalize_address(line)
                if normalized:
                    groups.append(normalized)
                else:
                    # Логируем невалидные строки, но не останавливаем парсинг
                    print(f"Предупреждение: строка {line_num} содержит невалидный адрес: {line}")
        
        # Удаляем дубликаты, сохраняя порядок
        seen = set()
        unique_groups = []
        for group in groups:
            if group not in seen:
                seen.add(group)
                unique_groups.append(group)
        
        return unique_groups
    
    @staticmethod
    def normalize_address(address: str) -> Optional[str]:
        """
        Нормализация адреса группы
        
        Args:
            address: Адрес группы в любом формате
            
        Returns:
            Нормализованный адрес (username без @) или None если невалидный
        """
        address = address.strip()
        if not address:
            return None
        
        # Проверка на username (@username или просто username)
        match = FileParser.USERNAME_PATTERN.search(address)
        if match:
            return match.group(1)
        
        # Проверка на полную ссылку https://t.me/username
        match = FileParser.FULL_LINK_PATTERN.search(address)
        if match:
            return match.group(1)
        
        # Проверка на короткую ссылку t.me/username
        match = FileParser.SHORT_LINK_PATTERN.search(address)
        if match:
            return match.group(1)
        
        # Проверка на invite link (возвращаем как есть, т.к. это специальный формат)
        match = FileParser.INVITE_LINK_PATTERN.search(address)
        if match:
            # Для invite links возвращаем полную ссылку
            if match.group(1):
                return address  # Уже полная ссылка
            else:
                return f"https://t.me/joinchat/{match.group(2)}"
        
        return None
    
    @staticmethod
    def extract_username(link: str) -> Optional[str]:
        """
        Извлечение username из ссылки
        
        Args:
            link: Ссылка на группу
            
        Returns:
            Username без @ или None
        """
        return FileParser.normalize_address(link)
    
    @staticmethod
    def validate_address(address: str) -> bool:
        """
        Валидация адреса группы
        
        Args:
            address: Адрес для проверки
            
        Returns:
            True если адрес валидный, False иначе
        """
        return FileParser.normalize_address(address) is not None

