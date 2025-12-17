"""
Модуль для работы с Telegram API
"""
import asyncio
from typing import List, Optional, Dict
from telethon import TelegramClient
from telethon.errors import (
    FloodWaitError,
    UserAlreadyParticipantError,
    InviteHashExpiredError,
    UsernameNotOccupiedError,
    ChatWriteForbiddenError,
    UserBannedInChannelError,
    MessageTooLongError
)
from telethon.tl.types import Channel, Chat, User
from telethon.tl.functions.channels import JoinChannelRequest
from pathlib import Path
import sys
import os

# Добавляем путь для импортов
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.utils.logger import setup_logger

logger = setup_logger()


class TelegramClientWrapper:
    """Обертка над Telethon для работы с Telegram"""
    
    def __init__(self, api_id: int, api_hash: str, session_file: str = "sessions/session"):
        """
        Инициализация клиента
        
        Args:
            api_id: API ID из my.telegram.org
            api_hash: API Hash из my.telegram.org
            session_file: Путь к файлу сессии
        """
        self.api_id = api_id
        self.api_hash = api_hash
        self.session_file = session_file
        
        # Создаем директорию для сессий
        Path(session_file).parent.mkdir(parents=True, exist_ok=True)
        
        self.client = TelegramClient(session_file, api_id, api_hash)
        self._is_connected = False
    
    async def connect(self) -> bool:
        """
        Подключение к Telegram
        
        Returns:
            True если подключение успешно
        """
        try:
            if not self.client.is_connected():
                await self.client.connect()
            
            if not await self.client.is_user_authorized():
                logger.warning("Пользователь не авторизован в сохраненной сессии")
                return False
            
            self._is_connected = True
            logger.info("Успешное подключение к Telegram")
            return True
        except Exception as e:
            logger.error(f"Ошибка подключения: {e}")
            return False
    
    async def authenticate(self, phone: str = None) -> Dict[str, any]:
        """
        Авторизация пользователя
        
        Args:
            phone: Номер телефона (если требуется)
            
        Returns:
            Словарь с информацией о статусе авторизации
        """
        try:
            if not self.client.is_connected():
                await self.client.connect()
            
            if await self.client.is_user_authorized():
                me = await self.client.get_me()
                logger.info(f"Пользователь уже авторизован: {me.first_name}")
                return {
                    "success": True,
                    "authorized": True,
                    "user": me
                }
            
            if not phone:
                return {
                    "success": False,
                    "authorized": False,
                    "needs_phone": True
                }
            
            # Отправка кода
            await self.client.send_code_request(phone)
            return {
                "success": True,
                "authorized": False,
                "needs_code": True,
                "phone": phone
            }
            
        except Exception as e:
            logger.error(f"Ошибка авторизации: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def sign_in(self, phone: str, code: str, password: str = None) -> Dict[str, any]:
        """
        Вход с кодом подтверждения
        
        Args:
            phone: Номер телефона
            code: Код подтверждения
            password: Пароль 2FA (если требуется)
            
        Returns:
            Словарь с результатом авторизации
        """
        try:
            if password:
                await self.client.sign_in(phone, code, password=password)
            else:
                await self.client.sign_in(phone, code)
            
            me = await self.client.get_me()
            logger.info(f"Успешная авторизация: {me.first_name}")
            return {
                "success": True,
                "user": me
            }
        except Exception as e:
            logger.error(f"Ошибка входа: {e}")
            return {
                "success": False,
                "error": str(e),
                "needs_password": "password" in str(e).lower() or "2fa" in str(e).lower()
            }
    
    async def get_dialogs(self, limit: int = 100) -> List[Dict]:
        """
        Получение списка диалогов
        
        Args:
            limit: Максимальное количество диалогов
            
        Returns:
            Список диалогов
        """
        try:
            dialogs = []
            async for dialog in self.client.iter_dialogs(limit=limit):
                if isinstance(dialog.entity, (Channel, Chat)):
                    dialogs.append({
                        "id": dialog.id,
                        "name": dialog.name,
                        "username": getattr(dialog.entity, 'username', None),
                        "type": "channel" if isinstance(dialog.entity, Channel) else "group"
                    })
            return dialogs
        except Exception as e:
            logger.error(f"Ошибка получения диалогов: {e}")
            return []
    
    async def is_member(self, group_identifier: str) -> bool:
        """
        Проверка участия пользователя в группе
        
        Args:
            group_identifier: Username группы, ID или invite link
            
        Returns:
            True если пользователь состоит в группе
        """
        try:
            # Если это числовой ID, проверяем через диалоги
            # ID может быть сохранен без минуса, пробуем оба варианта
            if group_identifier.lstrip('-').isdigit():
                group_id_abs = abs(int(group_identifier))
                group_id_neg = -group_id_abs
                group_id_neg_100 = -1000000000000 - group_id_abs if group_id_abs < 1000000000000 else None
                
                async for dialog in self.client.iter_dialogs():
                    if (dialog.id == group_id_neg or 
                        dialog.id == -group_id_abs or
                        (group_id_neg_100 and dialog.id == group_id_neg_100)):
                        return True
                return False
            
            # Для username или invite link получаем entity
            entity = await self.client.get_entity(group_identifier)
            
            if isinstance(entity, Channel):
                # Для каналов/супергрупп проверяем через участников
                me = await self.client.get_me()
                try:
                    # Пытаемся получить информацию о себе как участнике
                    participant = await self.client.get_participants(
                        entity, 
                        limit=1, 
                        filter=lambda u: u.id == me.id
                    )
                    return len(list(participant)) > 0
                except:
                    # Если не можем получить участников, проверяем через left
                    try:
                        full_chat = await self.client.get_entity(entity)
                        return hasattr(full_chat, 'left') and not full_chat.left
                    except:
                        # Пробуем проверить через диалоги
                        async for dialog in self.client.iter_dialogs():
                            if hasattr(dialog.entity, 'id') and dialog.entity.id == entity.id:
                                return True
                        return False
            elif isinstance(entity, Chat):
                # Для обычных групп проверяем через диалоги
                async for dialog in self.client.iter_dialogs():
                    if hasattr(dialog.entity, 'id') and dialog.entity.id == entity.id:
                        return True
                return False
            
            return True
        except Exception as e:
            logger.debug(f"Ошибка проверки участия в {group_identifier}: {e}")
            return False
    
    async def can_send_message(self, group_identifier: str) -> Dict[str, any]:
        """
        Проверка возможности отправки сообщения в группу
        
        Args:
            group_identifier: Username группы, ID или invite link
            
        Returns:
            Словарь с результатом проверки: {"can_send": bool, "reason": str, "entity": entity}
        """
        try:
            entity = None
            
            # Если это числовой ID, получаем entity через диалоги
            # ID может быть сохранен без минуса, пробуем оба варианта
            if group_identifier.lstrip('-').isdigit():
                group_id_abs = abs(int(group_identifier))
                group_id_neg = -group_id_abs
                group_id_neg_100 = -1000000000000 - group_id_abs if group_id_abs < 1000000000000 else None
                
                async for dialog in self.client.iter_dialogs():
                    if (dialog.id == group_id_neg or 
                        dialog.id == -group_id_abs or
                        (group_id_neg_100 and dialog.id == group_id_neg_100)):
                        entity = dialog.entity
                        break
                
                if not entity:
                    return {
                        "can_send": False,
                        "reason": "Группа не найдена в диалогах",
                        "entity": None
                    }
            else:
                # Это username, получаем entity (без @ или с @)
                username = group_identifier.lstrip('@')
                entity = await self.client.get_entity(username)
            
            # Проверяем тип сущности
            if isinstance(entity, Channel):
                # Для каналов проверяем права
                if entity.broadcast:
                    # Это канал, проверяем можем ли мы отправлять сообщения
                    # В каналах обычно только админы могут отправлять
                    try:
                        # Пытаемся получить информацию о себе как участнике
                        me = await self.client.get_me()
                        participant = await self.client.get_participants(
                            entity,
                            limit=1,
                            filter=lambda u: u.id == me.id
                        )
                        participants = list(participant)
                        if participants:
                            # Проверяем права участника
                            participant_obj = participants[0]
                            if hasattr(participant_obj, 'admin_rights') and participant_obj.admin_rights:
                                return {
                                    "can_send": True,
                                    "reason": "Администратор канала",
                                    "entity": entity
                                }
                            return {
                                "can_send": False,
                                "reason": "В каналах могут отправлять только администраторы",
                                "entity": entity
                            }
                    except:
                        pass
                    return {
                        "can_send": False,
                        "reason": "Не удалось проверить права в канале",
                        "entity": entity
                    }
                else:
                    # Это супергруппа, можно отправлять если состоим
                    return {
                        "can_send": True,
                        "reason": "Супергруппа, можно отправлять",
                        "entity": entity
                    }
            elif isinstance(entity, Chat):
                # Обычная группа, можно отправлять если состоим
                return {
                    "can_send": True,
                    "reason": "Обычная группа, можно отправлять",
                    "entity": entity
                }
            
            return {
                "can_send": True,
                "reason": "Неизвестный тип, пробуем отправить",
                "entity": entity
            }
        except Exception as e:
            logger.debug(f"Ошибка проверки прав отправки в {group_identifier}: {e}")
            return {
                "can_send": False,
                "reason": f"Ошибка проверки: {str(e)}",
                "entity": None
            }
    
    async def join_group(self, group_identifier: str) -> Dict[str, any]:
        """
        Вступление в группу
        
        Args:
            group_identifier: Username группы, ID или invite link
            
        Returns:
            Словарь с результатом операции
        """
        try:
            # Если это invite link
            if "joinchat" in group_identifier:
                # Для invite links используем прямую ссылку
                await self.client(JoinChannelRequest(group_identifier))
            elif group_identifier.lstrip('-').isdigit():
                # Это числовой ID - получаем entity через диалоги
                # ID может быть сохранен без минуса, пробуем оба варианта
                group_id_abs = abs(int(group_identifier))
                group_id_neg = -group_id_abs
                group_id_neg_100 = -1000000000000 - group_id_abs if group_id_abs < 1000000000000 else None
                
                entity = None
                async for dialog in self.client.iter_dialogs():
                    if (dialog.id == group_id_neg or 
                        dialog.id == -group_id_abs or
                        (group_id_neg_100 and dialog.id == group_id_neg_100)):
                        entity = dialog.entity
                        break
                
                if not entity:
                    return {
                        "success": False,
                        "group": group_identifier,
                        "error": f"Группа с ID {group_identifier} не найдена. Нельзя вступить в группу по ID без username."
                    }
                
                await self.client(JoinChannelRequest(entity))
            else:
                # Для username получаем entity и вступаем (без @ или с @)
                username = group_identifier.lstrip('@')
                entity = await self.client.get_entity(username)
                await self.client(JoinChannelRequest(entity))
            
            logger.info(f"Успешное вступление в группу: {group_identifier}")
            return {
                "success": True,
                "group": group_identifier
            }
        except UserAlreadyParticipantError:
            logger.info(f"Уже состоим в группе: {group_identifier}")
            return {
                "success": True,
                "group": group_identifier,
                "already_member": True
            }
        except InviteHashExpiredError:
            logger.error(f"Ссылка-приглашение истекла: {group_identifier}")
            return {
                "success": False,
                "group": group_identifier,
                "error": "Ссылка-приглашение истекла"
            }
        except UsernameNotOccupiedError:
            logger.error(f"Группа не найдена: {group_identifier}")
            return {
                "success": False,
                "group": group_identifier,
                "error": "Группа не найдена"
            }
        except FloodWaitError as e:
            logger.warning(f"FloodWait: нужно подождать {e.seconds} секунд")
            return {
                "success": False,
                "group": group_identifier,
                "error": f"Слишком много запросов. Подождите {e.seconds} секунд",
                "flood_wait": e.seconds
            }
        except Exception as e:
            logger.error(f"Ошибка вступления в группу {group_identifier}: {e}")
            return {
                "success": False,
                "group": group_identifier,
                "error": str(e)
            }
    
    def _get_message_link(self, entity, message_id: int) -> str:
        """
        Формирование ссылки на отправленное сообщение
        
        Args:
            entity: Объект чата/группы/канала
            message_id: ID отправленного сообщения
            
        Returns:
            Ссылка на сообщение
        """
        try:
            # Пытаемся получить username
            if hasattr(entity, 'username') and entity.username:
                return f"https://t.me/{entity.username}/{message_id}"
            
            # Если нет username, используем ID
            # Для групп/каналов ID обычно в формате -100xxxxxxxxxx
            # Для ссылки нужно убрать -100
            chat_id = entity.id
            
            # Преобразуем ID для ссылки
            if chat_id < 0:
                # Убираем -100 для каналов/супергрупп
                # Например: -1001234567890 -> 1234567890
                chat_id_abs = abs(chat_id)
                chat_id_str = str(chat_id_abs)
                if chat_id_str.startswith('100'):
                    # Убираем префикс '100'
                    chat_id_str = chat_id_str[3:]
                return f"https://t.me/c/{chat_id_str}/{message_id}"
            else:
                # Для обычных чатов (редко используется)
                return f"https://t.me/c/{chat_id}/{message_id}"
        except Exception as e:
            logger.warning(f"Не удалось сформировать ссылку на сообщение: {e}")
            return ""
    
    async def send_message(self, group_identifier: str, message: str) -> Dict[str, any]:
        """
        Отправка сообщения в группу
        
        Args:
            group_identifier: Username группы (формат: @username) или ID (числовой)
            message: Текст сообщения
            
        Returns:
            Словарь с результатом операции
        """
        try:
            entity = None
            # Если это числовой ID, получаем entity через диалоги
            # ID может быть сохранен без минуса, пробуем оба варианта
            if group_identifier.lstrip('-').isdigit():
                group_id_abs = abs(int(group_identifier))  # Абсолютное значение
                # Пробуем отрицательный ID (стандартный формат Telegram для групп)
                group_id_neg = -group_id_abs
                # Также пробуем с префиксом -100 для супергрупп/каналов
                group_id_neg_100 = -1000000000000 - group_id_abs if group_id_abs < 1000000000000 else None
                
                # Ищем группу в диалогах по ID (пробуем разные варианты)
                async for dialog in self.client.iter_dialogs():
                    if (dialog.id == group_id_neg or 
                        dialog.id == -group_id_abs or
                        (group_id_neg_100 and dialog.id == group_id_neg_100)):
                        entity = dialog.entity
                        break
                
                if not entity:
                    return {
                        "success": False,
                        "group": group_identifier,
                        "error": f"Группа с ID {group_identifier} не найдена в ваших диалогах. Убедитесь, что вы состоите в этой группе."
                    }
            else:
                # Это username, получаем entity по username (без @ или с @)
                username = group_identifier.lstrip('@')
                entity = await self.client.get_entity(username)
            
            sent = await self.client.send_message(entity, message)
            
            # Формируем ссылку на сообщение
            message_link = self._get_message_link(entity, sent.id)
            
            logger.info(f"Сообщение отправлено в {group_identifier}")
            return {
                "success": True,
                "group": group_identifier,
                "message_id": sent.id,
                "message_link": message_link
            }
        except ChatWriteForbiddenError:
            logger.error(f"Нет прав на отправку в {group_identifier}")
            return {
                "success": False,
                "group": group_identifier,
                "error": "Нет прав на отправку сообщений"
            }
        except UserBannedInChannelError:
            logger.error(f"Пользователь забанен в {group_identifier}")
            return {
                "success": False,
                "group": group_identifier,
                "error": "Пользователь забанен в группе"
            }
        except MessageTooLongError:
            logger.error(f"Сообщение слишком длинное для {group_identifier}")
            return {
                "success": False,
                "group": group_identifier,
                "error": "Сообщение слишком длинное"
            }
        except FloodWaitError as e:
            logger.warning(f"FloodWait: нужно подождать {e.seconds} секунд")
            return {
                "success": False,
                "group": group_identifier,
                "error": f"Слишком много запросов. Подождите {e.seconds} секунд",
                "flood_wait": e.seconds
            }
        except Exception as e:
            logger.error(f"Ошибка отправки в {group_identifier}: {e}")
            return {
                "success": False,
                "group": group_identifier,
                "error": str(e)
            }
    
    async def disconnect(self):
        """Отключение от Telegram"""
        if self.client.is_connected():
            try:
                await self.client.disconnect()
                self._is_connected = False
                logger.info("Отключение от Telegram")
            except Exception as e:
                # Игнорируем ошибки "database is locked" при отключении
                error_msg = str(e).lower()
                if "database is locked" in error_msg:
                    logger.debug("База данных заблокирована при отключении (не критично)")
                    self._is_connected = False
                else:
                    logger.warning(f"Ошибка при отключении: {e}")
                    self._is_connected = False
    
    def is_connected(self) -> bool:
        """Проверка подключения"""
        return self._is_connected and self.client.is_connected()

