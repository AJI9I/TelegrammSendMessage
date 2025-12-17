"""
Модуль для генерации уникальных хэш-строк для сообщений
"""
import hashlib
from datetime import datetime
from src.utils.logger import setup_logger

logger = setup_logger()


def generate_message_hash(group_identifier: str, length: int = 15) -> str:
    """
    Генерация уникальной хэш-строки для сообщения на основе даты и группы
    
    Args:
        group_identifier: Идентификатор группы (username или ID)
        length: Длина хэш-строки (по умолчанию 15)
        
    Returns:
        Хэш-строка указанной длины
    """
    # Получаем текущую дату и время в формате YYYYMMDDHHMMSS (включая секунды)
    now = datetime.now()
    date_str = now.strftime("%Y%m%d%H%M%S")
    
    # Нормализуем идентификатор группы (убираем @ если есть)
    group_id = group_identifier.lstrip('@')
    
    # Создаем строку для хэширования: дата + идентификатор группы
    hash_input = f"{date_str}{group_id}"
    
    # Генерируем MD5 хэш
    hash_obj = hashlib.md5(hash_input.encode('utf-8'))
    hash_hex = hash_obj.hexdigest()
    
    # Берем первые length символов из хэша
    # MD5 дает 32 символа hex, берем первые length
    final_hash = hash_hex[:length]
    
    logger.debug(f"Сгенерирован хэш для группы {group_identifier}: {final_hash}")
    return final_hash


def add_hash_to_message(message: str, group_identifier: str) -> str:
    """
    Добавление хэш-строки к сообщению
    
    Args:
        message: Исходное сообщение
        group_identifier: Идентификатор группы (username или ID)
        
    Returns:
        Сообщение с добавленной хэш-строкой
    """
    hash_str = generate_message_hash(group_identifier)
    
    # Добавляем хэш с новой строки в конец сообщения
    if message.strip():
        return f"{message}\n{hash_str}"
    else:
        return hash_str

