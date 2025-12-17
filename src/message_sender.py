"""
Модуль для рассылки сообщений
"""
from typing import List, Dict, Callable, Optional
from src.telegram_client import TelegramClientWrapper
from src.utils.delay_manager import DelayManager
from src.utils.message_hash import add_hash_to_message
from src.utils.logger import setup_logger

logger = setup_logger()


class MessageSender:
    """Класс для управления рассылкой сообщений"""
    
    def __init__(self, 
                 telegram_client: TelegramClientWrapper,
                 delay_manager: DelayManager):
        """
        Инициализация отправителя
        
        Args:
            telegram_client: Клиент Telegram
            delay_manager: Менеджер задержек
        """
        self.client = telegram_client
        self.delay_manager = delay_manager
        self._progress = 0.0
        self._status = "Готов"
        self._total_groups = 0
        self._processed_groups = 0
        self._on_progress_update: Optional[Callable] = None
        self._on_result_update: Optional[Callable] = None
    
    def set_progress_callback(self, callback: Callable[[float, str], None]):
        """
        Установка callback для обновления прогресса
        
        Args:
            callback: Функция для вызова при обновлении прогресса
        """
        self._on_progress_update = callback
    
    def set_result_callback(self, callback: Callable[[str, str, str], None]):
        """
        Установка callback для вывода результатов отправки
        
        Args:
            callback: Функция для вызова при отправке сообщения
                     Принимает: (group, message_link, status)
        """
        self._on_result_update = callback
    
    def _update_progress(self, status: str = None):
        """Обновление прогресса"""
        if self._total_groups > 0:
            self._progress = (self._processed_groups / self._total_groups) * 100
        else:
            self._progress = 0.0
        
        if status:
            self._status = status
        
        if self._on_progress_update:
            self._on_progress_update(self._progress, self._status)
    
    async def join_groups_if_needed(self, groups: List[str]) -> Dict[str, any]:
        """
        Автоматическое вступление в группы, если пользователь не состоит
        
        Args:
            groups: Список адресов групп
            
        Returns:
            Словарь с результатами
        """
        self._total_groups = len(groups)
        self._processed_groups = 0
        self._progress = 0.0
        
        results = {
            "total": len(groups),
            "joined": 0,
            "already_member": 0,
            "failed": 0,
            "details": []
        }
        
        self._update_progress("Проверка участия в группах...")
        
        for group in groups:
            try:
                # Проверяем участие
                is_member = await self.client.is_member(group)
                
                if not is_member:
                    # Вступаем в группу
                    self._update_progress(f"Вступление в группу: {group}")
                    result = await self.client.join_group(group)
                    
                    if result.get("success"):
                        if result.get("already_member"):
                            results["already_member"] += 1
                        else:
                            results["joined"] += 1
                    else:
                        results["failed"] += 1
                    
                    results["details"].append({
                        "group": group,
                        "action": "join",
                        **result
                    })
                    
                    # Задержка перед следующей операцией
                    await self.delay_manager.wait_join_delay()
                else:
                    results["already_member"] += 1
                    results["details"].append({
                        "group": group,
                        "action": "join",
                        "success": True,
                        "already_member": True
                    })
                
                self._processed_groups += 1
                self._update_progress(f"Обработано: {self._processed_groups}/{self._total_groups}")
                
            except Exception as e:
                logger.error(f"Ошибка при обработке группы {group}: {e}")
                results["failed"] += 1
                results["details"].append({
                    "group": group,
                    "action": "join",
                    "success": False,
                    "error": str(e)
                })
                self._processed_groups += 1
        
        self._update_progress("Завершено")
        return results
    
    async def send_to_groups(self, groups: List[str], message: str) -> Dict[str, any]:
        """
        Рассылка сообщения в группы с автоматической проверкой членства и прав
        
        Args:
            groups: Список адресов групп
            message: Текст сообщения
            
        Returns:
            Словарь с результатами рассылки
        """
        if not message or not message.strip():
            logger.warning("Попытка отправить пустое сообщение")
            return {
                "total": 0,
                "sent": 0,
                "failed": 0,
                "error": "Сообщение пустое"
            }
        
        self._total_groups = len(groups)
        self._processed_groups = 0
        self._progress = 0.0
        
        results = {
            "total": len(groups),
            "sent": 0,
            "failed": 0,
            "joined": 0,
            "already_member": 0,
            "no_permission": 0,
            "details": []
        }
        
        self._update_progress("Начало рассылки...")
        
        for group in groups:
            try:
                self._update_progress(f"Проверка группы: {group}")
                
                # Шаг 1: Проверяем, состоит ли пользователь в группе
                is_member = await self.client.is_member(group)
                
                if not is_member:
                    # Шаг 2: Если не состоит, вступаем в группу
                    self._update_progress(f"Вступление в группу: {group}")
                    join_result = await self.client.join_group(group)
                    
                    if not join_result.get("success"):
                        # Не удалось вступить
                        results["failed"] += 1
                        error_msg = f"Не удалось вступить в группу: {join_result.get('error', 'Неизвестная ошибка')}"
                        results["details"].append({
                            "group": group,
                            "action": "send",
                            "success": False,
                            "error": error_msg,
                            "join_error": join_result.get("error")
                        })
                        # Выводим ошибку в UI в реальном времени
                        if self._on_result_update:
                            self._on_result_update(group, error_msg, "ERROR")
                        self._processed_groups += 1
                        self._update_progress(f"Ошибка вступления: {self._processed_groups}/{self._total_groups}")
                        continue
                    
                    # Успешно вступили (или уже были участником)
                    if join_result.get("already_member"):
                        results["already_member"] += 1
                    else:
                        results["joined"] += 1
                        # Ждем после вступления перед отправкой сообщения
                        self._update_progress(f"Ожидание после вступления в {group}...")
                        await self.delay_manager.wait_join_delay()
                
                # Шаг 3: Проверяем права на отправку сообщений
                self._update_progress(f"Проверка прав отправки в: {group}")
                can_send_check = await self.client.can_send_message(group)
                
                if not can_send_check.get("can_send"):
                    # Нет прав на отправку
                    results["no_permission"] += 1
                    results["failed"] += 1
                    error_msg = f"Нет прав на отправку: {can_send_check.get('reason', 'Неизвестная причина')}"
                    results["details"].append({
                        "group": group,
                        "action": "send",
                        "success": False,
                        "error": error_msg,
                        "reason": can_send_check.get("reason")
                    })
                    logger.warning(f"Нет прав на отправку в {group}: {can_send_check.get('reason')}")
                    # Выводим ошибку в UI в реальном времени
                    if self._on_result_update:
                        self._on_result_update(group, error_msg, "ERROR")
                    self._processed_groups += 1
                    self._update_progress(f"Нет прав: {self._processed_groups}/{self._total_groups}")
                    continue
                
                # Шаг 4: Добавляем уникальную хэш-строку к сообщению
                message_with_hash = add_hash_to_message(message, group)
                
                # Шаг 5: Отправляем сообщение
                self._update_progress(f"Отправка в: {group}")
                result = await self.client.send_message(group, message_with_hash)
                
                if result.get("success"):
                    results["sent"] += 1
                    message_link = result.get("message_link", "")
                    if message_link:
                        logger.info(f"✓ Сообщение отправлено в {group}: {message_link}")
                        # Выводим результат в UI в реальном времени
                        if self._on_result_update:
                            self._on_result_update(group, message_link, "SUCCESS")
                    else:
                        logger.info(f"✓ Сообщение отправлено в {group}")
                        # Выводим результат в UI в реальном времени
                        if self._on_result_update:
                            self._on_result_update(group, "", "SUCCESS")
                else:
                    results["failed"] += 1
                    error_msg = result.get('error', 'Неизвестная ошибка')
                    logger.warning(f"✗ Не удалось отправить в {group}: {error_msg}")
                    # Выводим ошибку в UI в реальном времени
                    if self._on_result_update:
                        self._on_result_update(group, error_msg, "ERROR")
                
                results["details"].append({
                    "group": group,
                    "action": "send",
                    **result
                })
                
                self._processed_groups += 1
                self._update_progress(f"Отправлено: {self._processed_groups}/{self._total_groups}")
                
                # Задержка перед следующей отправкой
                await self.delay_manager.wait_send_delay()
                
            except Exception as e:
                logger.error(f"Ошибка при обработке группы {group}: {e}")
                error_msg = str(e)
                results["failed"] += 1
                results["details"].append({
                    "group": group,
                    "action": "send",
                    "success": False,
                    "error": error_msg
                })
                # Выводим ошибку в UI в реальном времени
                if self._on_result_update:
                    self._on_result_update(group, error_msg, "ERROR")
                self._processed_groups += 1
        
        self._update_progress("Рассылка завершена")
        return results
    
    def get_progress(self) -> float:
        """Получить текущий прогресс (0-100)"""
        return self._progress
    
    def get_status(self) -> str:
        """Получить текущий статус"""
        return self._status

