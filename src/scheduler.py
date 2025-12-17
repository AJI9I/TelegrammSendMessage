"""
Модуль планировщика рассылок
"""
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Callable, Dict
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
import pytz
from src.utils.logger import setup_logger

logger = setup_logger()


class Scheduler:
    """Планировщик для автоматической рассылки"""
    
    def __init__(self, timezone: str = "UTC"):
        """
        Инициализация планировщика
        
        Args:
            timezone: Часовой пояс (например, "Europe/Moscow", "UTC")
        """
        self.timezone = pytz.timezone(timezone)
        self.scheduler = BackgroundScheduler(timezone=self.timezone)
        self._enabled = False
        self._mode = "immediate"  # immediate, interval, schedule
        self._interval_hours: Optional[int] = None
        self._schedule_times: List[str] = []
        self._task_callback: Optional[Callable] = None
        self._next_run: Optional[datetime] = None
    
    def set_task_callback(self, callback: Callable):
        """
        Установка callback для выполнения задачи
        
        Args:
            callback: Асинхронная функция для вызова
        """
        self._task_callback = callback
    
    def set_interval_mode(self, hours: int):
        """
        Установка режима интервальной рассылки
        
        Args:
            hours: Интервал в часах
        """
        self._mode = "interval"
        self._interval_hours = hours
        self._schedule_times = []
        logger.info(f"Установлен режим интервальной рассылки: каждые {hours} часов")
    
    def set_schedule_mode(self, times: List[str]):
        """
        Установка режима рассылки по расписанию
        
        Args:
            times: Список времен в формате "HH:MM" или "H:MM"
        """
        self._mode = "schedule"
        self._schedule_times = self._parse_times(times)
        self._interval_hours = None
        logger.info(f"Установлен режим рассылки по расписанию: {self._schedule_times}")
    
    def set_immediate_mode(self):
        """Установка режима немедленной рассылки"""
        self._mode = "immediate"
        self._interval_hours = None
        self._schedule_times = []
        logger.info("Установлен режим немедленной рассылки")
    
    def _parse_times(self, times: List[str]) -> List[str]:
        """
        Парсинг времен из различных форматов
        
        Args:
            times: Список времен (может быть строками или числами)
            
        Returns:
            Список времен в формате "HH:MM"
        """
        parsed_times = []
        for time_str in times:
            time_str = str(time_str).strip()
            # Если только число (например, "9" или "09")
            if ':' not in time_str:
                try:
                    hour = int(time_str)
                    if 0 <= hour <= 23:
                        parsed_times.append(f"{hour:02d}:00")
                    else:
                        logger.warning(f"Некорректный час: {time_str}")
                except ValueError:
                    logger.warning(f"Некорректный формат времени: {time_str}")
            else:
                # Формат "HH:MM" или "H:MM"
                try:
                    parts = time_str.split(':')
                    hour = int(parts[0])
                    minute = int(parts[1]) if len(parts) > 1 else 0
                    if 0 <= hour <= 23 and 0 <= minute <= 59:
                        parsed_times.append(f"{hour:02d}:{minute:02d}")
                    else:
                        logger.warning(f"Некорректное время: {time_str}")
                except (ValueError, IndexError):
                    logger.warning(f"Некорректный формат времени: {time_str}")
        
        return sorted(set(parsed_times))  # Убираем дубликаты и сортируем
    
    def _run_task(self):
        """Внутренний метод для выполнения задачи (синхронная обертка)"""
        if self._task_callback:
            try:
                logger.info("Запуск запланированной задачи рассылки")
                # Вызываем callback (он уже настроен на запуск в правильном event loop)
                if callable(self._task_callback):
                    result = self._task_callback()
                    # Если это Future (результат run_coroutine_threadsafe), ждем его
                    if hasattr(result, 'result'):
                        try:
                            result.result(timeout=300)  # Максимум 5 минут на выполнение
                        except Exception as e:
                            logger.error(f"Ошибка выполнения задачи: {e}")
                
                self._update_next_run()
            except Exception as e:
                logger.error(f"Ошибка при выполнении запланированной задачи: {e}")
    
    def start(self):
        """Запуск планировщика"""
        if self._enabled:
            logger.warning("Планировщик уже запущен")
            return
        
        if self._mode == "immediate":
            logger.warning("Режим 'immediate' не требует планировщика")
            return
        
        # Очищаем предыдущие задачи
        try:
            self.scheduler.remove_all_jobs()
        except:
            pass  # Игнорируем ошибки, если планировщик еще не запущен
        
        if self._mode == "interval":
            if not self._interval_hours:
                logger.error("Не указан интервал для режима interval")
                return
            
            # Добавляем задачу с интервалом
            self.scheduler.add_job(
                self._run_task,
                IntervalTrigger(hours=self._interval_hours),
                id="interval_send",
                replace_existing=True
            )
            logger.info(f"Планировщик запущен: рассылка каждые {self._interval_hours} часов")
        
        elif self._mode == "schedule":
            if not self._schedule_times:
                logger.error("Не указаны времена для режима schedule")
                return
            
            # Добавляем задачи для каждого времени
            for idx, time_str in enumerate(self._schedule_times):
                hour, minute = map(int, time_str.split(':'))
                self.scheduler.add_job(
                    self._run_task,
                    CronTrigger(hour=hour, minute=minute),
                    id=f"schedule_send_{idx}",
                    replace_existing=True
                )
            logger.info(f"Планировщик запущен: рассылка в {', '.join(self._schedule_times)}")
        
        self.scheduler.start()
        self._enabled = True
        self._update_next_run()
        logger.info("Планировщик успешно запущен")
    
    def stop(self):
        """Остановка планировщика"""
        if not self._enabled:
            return
        
        self.scheduler.shutdown()
        self._enabled = False
        self._next_run = None
        logger.info("Планировщик остановлен")
    
    def _update_next_run(self):
        """Обновление времени следующей рассылки"""
        if not self._enabled:
            self._next_run = None
            return
        
        jobs = self.scheduler.get_jobs()
        if jobs:
            # Находим ближайшую задачу
            next_runs = [job.next_run_time for job in jobs if job.next_run_time]
            if next_runs:
                self._next_run = min(next_runs)
        else:
            self._next_run = None
    
    def get_next_run_time(self) -> Optional[datetime]:
        """
        Получить время следующей запланированной рассылки
        
        Returns:
            datetime следующей рассылки или None
        """
        self._update_next_run()
        return self._next_run
    
    def is_enabled(self) -> bool:
        """Проверка, включен ли планировщик"""
        return self._enabled
    
    def get_mode(self) -> str:
        """Получить текущий режим"""
        return self._mode
    
    def set_timezone(self, timezone: str):
        """
        Изменение часового пояса
        
        Args:
            timezone: Название часового пояса
        """
        try:
            self.timezone = pytz.timezone(timezone)
            # Перезапускаем планировщик с новым часовым поясом
            if self._enabled:
                was_enabled = True
                self.stop()
                self.start()
            logger.info(f"Часовой пояс изменен на: {timezone}")
        except Exception as e:
            logger.error(f"Ошибка установки часового пояса: {e}")

