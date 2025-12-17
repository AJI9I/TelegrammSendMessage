"""
Модуль для управления конфигурацией
"""
import configparser
from pathlib import Path
from typing import Optional
from src.utils.logger import setup_logger

logger = setup_logger()


class ConfigManager:
    """Менеджер конфигурации приложения"""
    
    def __init__(self, config_file: str = "config/config.ini"):
        """
        Инициализация менеджера конфигурации
        
        Args:
            config_file: Путь к файлу конфигурации
        """
        self.config_file = Path(config_file)
        self.config = configparser.ConfigParser()
        self._load_config()
    
    def _load_config(self):
        """Загрузка конфигурации из файла"""
        if self.config_file.exists():
            try:
                self.config.read(self.config_file, encoding='utf-8')
                logger.info(f"Конфигурация загружена из {self.config_file}")
            except Exception as e:
                logger.error(f"Ошибка загрузки конфигурации: {e}")
                self._create_default_config()
        else:
            logger.warning(f"Файл конфигурации не найден: {self.config_file}")
            self._create_default_config()
    
    def _create_default_config(self):
        """Создание конфигурации по умолчанию"""
        self.config['telegram'] = {
            'api_id': '',
            'api_hash': '',
            'session_file': 'sessions/session'
        }
        self.config['delays'] = {
            'join_group_min': '5',
            'join_group_max': '15',
            'send_message_min_minutes': '1',
            'send_message_max_minutes': '3'
        }
        self.config['scheduler'] = {
            'enabled': 'false',
            'mode': 'immediate',
            'interval_hours': '3',
            'schedule_times': '9,12,14,19',
            'timezone': 'UTC'
        }
        self.config['message'] = {
            'text': '',
            'templates': ''
        }
        self.config['ui'] = {
            'theme': 'default',
            'language': 'ru'
        }
        self.config['groups'] = {
            'selected': ''
        }
    
    def save_config(self):
        """Сохранение конфигурации в файл"""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                self.config.write(f)
            logger.info(f"Конфигурация сохранена в {self.config_file}")
        except Exception as e:
            logger.error(f"Ошибка сохранения конфигурации: {e}")
    
    # Telegram
    def get_telegram_api_id(self) -> Optional[int]:
        """Получить API ID"""
        try:
            return int(self.config.get('telegram', 'api_id'))
        except (ValueError, configparser.NoOptionError):
            return None
    
    def get_telegram_api_hash(self) -> str:
        """Получить API Hash"""
        return self.config.get('telegram', 'api_hash', fallback='')
    
    def get_session_file(self) -> str:
        """Получить путь к файлу сессии"""
        return self.config.get('telegram', 'session_file', fallback='sessions/session')
    
    def set_telegram_credentials(self, api_id: int, api_hash: str):
        """Установить учетные данные Telegram"""
        self.config.set('telegram', 'api_id', str(api_id))
        self.config.set('telegram', 'api_hash', api_hash)
        self.save_config()
    
    # Delays
    def get_delays(self) -> dict:
        """Получить настройки задержек"""
        return {
            'join_min': float(self.config.get('delays', 'join_group_min', fallback='5')),
            'join_max': float(self.config.get('delays', 'join_group_max', fallback='15')),
            'send_min_minutes': float(self.config.get('delays', 'send_message_min_minutes', fallback='1')),
            'send_max_minutes': float(self.config.get('delays', 'send_message_max_minutes', fallback='3'))
        }
    
    def set_delays(self, join_min: float = None, join_max: float = None, 
                   send_min_minutes: float = None, send_max_minutes: float = None):
        """Установить задержки"""
        if join_min is not None:
            self.config.set('delays', 'join_group_min', str(join_min))
        if join_max is not None:
            self.config.set('delays', 'join_group_max', str(join_max))
        if send_min_minutes is not None:
            self.config.set('delays', 'send_message_min_minutes', str(send_min_minutes))
        if send_max_minutes is not None:
            self.config.set('delays', 'send_message_max_minutes', str(send_max_minutes))
        self.save_config()
    
    # Scheduler
    def get_scheduler_config(self) -> dict:
        """Получить настройки планировщика"""
        schedule_times_str = self.config.get('scheduler', 'schedule_times', fallback='9,12,14,19')
        schedule_times = [t.strip() for t in schedule_times_str.split(',') if t.strip()]
        
        return {
            'enabled': self.config.getboolean('scheduler', 'enabled', fallback=False),
            'mode': self.config.get('scheduler', 'mode', fallback='immediate'),
            'interval_hours': self.config.getint('scheduler', 'interval_hours', fallback=3),
            'schedule_times': schedule_times,
            'timezone': self.config.get('scheduler', 'timezone', fallback='UTC')
        }
    
    def set_scheduler_config(self, enabled: bool, mode: str, interval_hours: int = None,
                            schedule_times: list = None, timezone: str = None):
        """Установить настройки планировщика"""
        self.config.set('scheduler', 'enabled', str(enabled).lower())
        self.config.set('scheduler', 'mode', mode)
        if interval_hours is not None:
            self.config.set('scheduler', 'interval_hours', str(interval_hours))
        if schedule_times is not None:
            self.config.set('scheduler', 'schedule_times', ','.join(schedule_times))
        if timezone is not None:
            self.config.set('scheduler', 'timezone', timezone)
        self.save_config()
    
    # Message
    def get_message_text(self) -> str:
        """Получить текст сообщения"""
        return self.config.get('message', 'text', fallback='')
    
    def set_message_text(self, text: str):
        """Установить текст сообщения"""
        self.config.set('message', 'text', text)
        self.save_config()
    
    # Groups
    def get_selected_groups(self) -> list:
        """Получить список выбранных групп"""
        # Убеждаемся, что секция groups существует
        if 'groups' not in self.config:
            return []
        try:
            groups_str = self.config.get('groups', 'selected', fallback='')
        except:
            return []
        if not groups_str:
            return []
        # Разделяем по запятой и очищаем от пробелов
        groups = [g.strip() for g in groups_str.split(',') if g.strip()]
        logger.debug(f"Загружено {len(groups)} групп из конфигурации")
        return groups
    
    def set_selected_groups(self, groups: list):
        """Установить список выбранных групп"""
        # Убеждаемся, что секция groups существует
        if 'groups' not in self.config:
            self.config['groups'] = {}
        groups_str = ','.join(groups)
        self.config.set('groups', 'selected', groups_str)
        self.save_config()
        logger.debug(f"Сохранено {len(groups)} групп: {groups_str[:100]}...")

