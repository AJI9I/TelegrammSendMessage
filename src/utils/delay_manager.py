"""
Модуль для управления задержками между действиями
"""
import random
import asyncio
from typing import Tuple


class DelayManager:
    """Управление задержками с случайными вариациями"""
    
    def __init__(self, 
                 join_min: float = 5.0, 
                 join_max: float = 15.0,
                 send_min_minutes: float = 1.0,
                 send_max_minutes: float = 3.0):
        """
        Инициализация менеджера задержек
        
        Args:
            join_min: Минимальная задержка при вступлении (секунды)
            join_max: Максимальная задержка при вступлении (секунды)
            send_min_minutes: Минимальная задержка при отправке (минуты)
            send_max_minutes: Максимальная задержка при отправке (минуты)
        """
        self.join_min = join_min
        self.join_max = join_max
        self.send_min_minutes = send_min_minutes
        self.send_max_minutes = send_max_minutes
    
    def get_join_delay(self) -> float:
        """
        Получить случайную задержку для вступления в группу
        
        Returns:
            Случайное значение задержки в секундах
        """
        return random.uniform(self.join_min, self.join_max)
    
    def get_send_delay(self) -> float:
        """
        Получить случайную задержку для отправки сообщения
        
        Returns:
            Случайное значение задержки в секундах (конвертируется из минут)
        """
        delay_minutes = random.uniform(self.send_min_minutes, self.send_max_minutes)
        return delay_minutes * 60  # Конвертируем минуты в секунды
    
    async def wait_join_delay(self) -> None:
        """Асинхронное ожидание задержки для вступления"""
        delay = self.get_join_delay()
        await asyncio.sleep(delay)
    
    async def wait_send_delay(self) -> None:
        """Асинхронное ожидание задержки для отправки"""
        delay = self.get_send_delay()
        await asyncio.sleep(delay)
    
    def random_delay(self, min_sec: float, max_sec: float) -> float:
        """
        Получить случайную задержку в заданном диапазоне
        
        Args:
            min_sec: Минимальная задержка
            max_sec: Максимальная задержка
            
        Returns:
            Случайное значение задержки
        """
        return random.uniform(min_sec, max_sec)
    
    def update_delays(self, 
                     join_min: float = None,
                     join_max: float = None,
                     send_min_minutes: float = None,
                     send_max_minutes: float = None) -> None:
        """
        Обновить значения задержек
        
        Args:
            join_min: Новая минимальная задержка при вступлении (секунды)
            join_max: Новая максимальная задержка при вступлении (секунды)
            send_min_minutes: Новая минимальная задержка при отправке (минуты)
            send_max_minutes: Новая максимальная задержка при отправке (минуты)
        """
        if join_min is not None:
            self.join_min = join_min
        if join_max is not None:
            self.join_max = join_max
        if send_min_minutes is not None:
            self.send_min_minutes = send_min_minutes
        if send_max_minutes is not None:
            self.send_max_minutes = send_max_minutes

