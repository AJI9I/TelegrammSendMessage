"""
Модуль для настройки логирования
"""
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logger(name: str = "TeggammMessage", log_dir: str = "logs") -> logging.Logger:
    """
    Настройка системы логирования
    
    Args:
        name: Имя логгера
        log_dir: Директория для логов
        
    Returns:
        Настроенный логгер
    """
    # Получаем логгер (если он уже существует, вернется тот же объект)
    logger = logging.getLogger(name)
    
    # Если у логгера уже есть обработчики, значит он уже настроен
    # Возвращаем его без добавления новых обработчиков
    if logger.handlers:
        return logger
    
    # Создаем директорию для логов, если её нет
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    
    # Устанавливаем уровень логирования только если логгер новый
    logger.setLevel(logging.DEBUG)
    
    # Предотвращаем распространение логов на родительский логгер
    logger.propagate = False
    
    # Формат логов
    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] [%(module)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Обработчик для консоли
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Обработчик для файла (общий лог)
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, 'app.log'),
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Обработчик для файла (только ошибки)
    error_handler = RotatingFileHandler(
        os.path.join(log_dir, 'errors.log'),
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    logger.addHandler(error_handler)
    
    return logger

