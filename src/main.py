"""
Главный файл запуска приложения
"""
import asyncio
import sys
import os
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, filedialog
from threading import Thread
from typing import List

# Добавляем корневую директорию проекта в путь Python
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.ui.main_window import MainWindow
from src.ui.auth_window import AuthWindow
from src.ui.group_select_window import GroupSelectWindow
from src.ui.export_groups_window import ExportGroupsWindow
from src.telegram_client import TelegramClientWrapper
from src.group_manager import GroupManager
from src.message_sender import MessageSender
from src.scheduler import Scheduler
from src.config_manager import ConfigManager
from src.utils.delay_manager import DelayManager
from src.utils.logger import setup_logger

logger = setup_logger()


class Application:
    """Главный класс приложения"""
    
    def __init__(self):
        """Инициализация приложения"""
        self.root = tk.Tk()
        self.config = ConfigManager()
        self.main_window = MainWindow(self.root)
        
        # Инициализация компонентов
        self.telegram_client: TelegramClientWrapper = None
        self.group_manager = GroupManager()
        self.delay_manager = DelayManager(**self.config.get_delays())
        self._auto_auth_in_progress = False
        self.message_sender: MessageSender = None
        self.scheduler: Scheduler = None
        
        # Состояние
        self.is_authenticated = False
        self.auth_window: AuthWindow = None
        self.group_select_window: GroupSelectWindow = None
        self.export_groups_window: ExportGroupsWindow = None
        
        # Настройка callbacks
        self._setup_callbacks()
        
        # Загрузка сохраненных данных
        self._load_saved_data()
        
        # Настройка планировщика
        self._setup_scheduler()
    
    def _try_auto_auth(self):
        """Попытка автоматической авторизации при наличии сохраненной сессии"""
        # Защита от повторных вызовов
        if hasattr(self, '_auto_auth_in_progress') and self._auto_auth_in_progress:
            logger.debug("Автоматическая авторизация уже выполняется, пропускаем")
            return
        
        api_id = self.config.get_telegram_api_id()
        api_hash = self.config.get_telegram_api_hash()
        session_file = self.config.get_session_file()
        
        logger.info(f"Попытка автоматической авторизации. API ID: {api_id is not None}, API Hash: {api_hash is not None}")
        
        if not api_id or not api_hash:
            logger.debug("Нет сохраненных API credentials для автоматической авторизации")
            return  # Нет сохраненных credentials
        
        # Устанавливаем флаг, что авторизация в процессе
        self._auto_auth_in_progress = True
        
        # Проверяем наличие файла сессии
        from pathlib import Path
        session_path = Path(session_file)
        # Проверяем как сам файл, так и файл с расширением .session
        session_file_with_ext = f"{session_file}.session"
        session_path_with_ext = Path(session_file_with_ext)
        
        logger.debug(f"Проверка файла сессии: {session_file} (существует: {session_path.exists()})")
        logger.debug(f"Проверка файла сессии: {session_file_with_ext} (существует: {session_path_with_ext.exists()})")
        
        if not session_path.exists() and not session_path_with_ext.exists():
            logger.warning(f"Файл сессии не найден: {session_file} или {session_file_with_ext}")
            return  # Нет сохраненной сессии
        
        # Используем файл с расширением, если он существует
        if session_path_with_ext.exists():
            session_file = session_file_with_ext
            logger.debug(f"Используется файл сессии: {session_file}")
        elif session_path.exists():
            logger.debug(f"Используется файл сессии: {session_file}")
        
        logger.info("Попытка автоматической авторизации...")
        
        # Пытаемся подключиться автоматически
        try:
            self.telegram_client = TelegramClientWrapper(api_id, api_hash, session_file)
            # Запускаем проверку в фоне
            # Используем after для гарантии, что все готово
            def start_check():
                try:
                    logger.info("Запуск проверки сессии...")
                    asyncio.run_coroutine_threadsafe(
                        self._check_session_async(),
                        self.loop
                    )
                except Exception as e:
                    logger.error(f"Ошибка при запуске проверки сессии: {e}")
                    self._auto_auth_in_progress = False
            
            self.root.after(300, start_check)
        except Exception as e:
            logger.error(f"Ошибка при попытке автоматической авторизации: {e}")
            self._auto_auth_in_progress = False
    
    async def _check_session_async(self):
        """Асинхронная проверка сессии"""
        try:
            logger.info("Проверка сохраненной сессии...")
            connected = await self.telegram_client.connect()
            logger.info(f"Результат подключения: {connected}")
            if connected:
                # Сессия валидна, получаем информацию о пользователе
                try:
                    me = await self.telegram_client.client.get_me()
                    username = f"{me.first_name or ''} {me.last_name or ''}".strip() or me.phone
                    logger.info(f"Автоматическая авторизация успешна: {username}")
                    self._auto_auth_in_progress = False
                    self.root.after(0, lambda: self._on_auto_auth_success(username))
                except Exception as e:
                    logger.error(f"Ошибка при получении информации о пользователе: {e}")
                    try:
                        await self.telegram_client.disconnect()
                    except Exception as disc_error:
                        # Игнорируем ошибки при отключении, особенно "database is locked"
                        if "database is locked" not in str(disc_error).lower():
                            logger.debug(f"Ошибка при отключении: {disc_error}")
                    self.telegram_client = None
                    self._auto_auth_in_progress = False
            else:
                # Сессия невалидна, нужно авторизоваться заново
                logger.warning("Сохраненная сессия невалидна, требуется повторная авторизация")
                try:
                    await self.telegram_client.disconnect()
                except Exception as disc_error:
                    # Игнорируем ошибки при отключении, особенно "database is locked"
                    if "database is locked" not in str(disc_error).lower():
                        logger.debug(f"Ошибка при отключении: {disc_error}")
                self.telegram_client = None
                self._auto_auth_in_progress = False
        except Exception as e:
            error_msg = str(e).lower()
            if "database is locked" in error_msg:
                logger.warning("База данных сессии заблокирована. Возможно, запущен другой экземпляр программы.")
            else:
                logger.error(f"Ошибка при проверке сессии: {e}", exc_info=True)
            if self.telegram_client:
                try:
                    await self.telegram_client.disconnect()
                except Exception as disc_error:
                    # Игнорируем ошибки при отключении, особенно "database is locked"
                    if "database is locked" not in str(disc_error).lower():
                        logger.debug(f"Ошибка при отключении: {disc_error}")
                self.telegram_client = None
            self._auto_auth_in_progress = False
    
    def _on_auto_auth_success(self, username: str):
        """Обработка успешной автоматической авторизации"""
        self.is_authenticated = True
        self.main_window.set_auth_status(True, username)
        self.main_window.enable_send_button(True)
        
        # Инициализируем отправитель сообщений
        self.message_sender = MessageSender(self.telegram_client, self.delay_manager)
        self.message_sender.set_progress_callback(
            lambda progress, status: self.root.after(0, 
                lambda: self.main_window.set_progress(progress, status))
        )
        # Устанавливаем callback для вывода результатов в реальном времени
        self.message_sender.set_result_callback(
            lambda group, link_or_error, status: self.root.after(0,
                lambda g=group, l=link_or_error, s=status: self._handle_result_update(g, l, s))
        )
        
        logger.info(f"Автоматическая авторизация успешна: {username}")
        self.main_window.add_log(f"Авторизован: {username}", "INFO")
    
    def _setup_callbacks(self):
        """Настройка callbacks для UI"""
        self.main_window.on_auth_clicked = self._handle_auth_clicked
        self.main_window.on_send_clicked = self._handle_send_clicked
        self.main_window.on_load_groups_clicked = self._handle_load_groups
        self.main_window.on_select_groups_clicked = self._handle_select_groups
        self.main_window.on_scheduler_changed = self._handle_scheduler_changed
        self.main_window.on_scheduler_toggle = self._handle_scheduler_toggle
        # Callbacks для удаления и очистки групп
        self.main_window.on_delete_group = self._handle_delete_group
        self.main_window.on_clear_groups = self._handle_clear_groups
        self.main_window.on_delays_changed = self._handle_delays_changed
        self.main_window.on_export_groups_clicked = self._handle_export_groups
    
    def _load_saved_data(self):
        """Загрузка сохраненных данных"""
        # Загружаем текст сообщения
        message_text = self.config.get_message_text()
        if message_text:
            self.main_window.set_message_text(message_text)
        
        # Загружаем сохраненные группы
        saved_groups = self.config.get_selected_groups()
        logger.info(f"Попытка загрузить сохраненные группы: найдено {len(saved_groups)} групп")
        if saved_groups:
            for group in saved_groups:
                if self.group_manager.add_group(group):
                    self.main_window.add_group(group)
                    logger.debug(f"Загружена группа: {group}")
            logger.info(f"Загружено {len(saved_groups)} сохраненных групп")
        else:
            logger.debug("Сохраненные группы не найдены")
        
        # Загружаем настройки планировщика
        scheduler_config = self.config.get_scheduler_config()
        self.main_window.scheduler_mode.set(scheduler_config['mode'])
        if scheduler_config['mode'] == 'interval':
            self.main_window.interval_entry.delete(0, tk.END)
            self.main_window.interval_entry.insert(0, str(scheduler_config['interval_hours']))
        elif scheduler_config['mode'] == 'schedule':
            self.main_window.schedule_entry.delete(0, tk.END)
            self.main_window.schedule_entry.insert(0, ','.join(scheduler_config['schedule_times']))
        self.main_window.timezone_var.set(scheduler_config['timezone'])
        self.main_window._on_mode_changed()
        
        # Загружаем настройки задержек
        delays_config = self.config.get_delays()
        self.main_window.set_delays_config(
            delays_config['send_min_minutes'],
            delays_config['send_max_minutes']
        )
    
    def _setup_scheduler(self):
        """Настройка планировщика"""
        scheduler_config = self.config.get_scheduler_config()
        self.scheduler = Scheduler(timezone=scheduler_config['timezone'])
        # Устанавливаем callback, который будет запускать задачу в правильном event loop
        def schedule_callback():
            """Callback для планировщика - запускает задачу в правильном event loop"""
            try:
                future = asyncio.run_coroutine_threadsafe(
                    self._run_scheduled_send(),
                    self.loop
                )
                # Не ждем результата здесь, чтобы не блокировать планировщик
                return future
            except Exception as e:
                logger.error(f"Ошибка при запуске запланированной задачи: {e}")
                return None
        
        self.scheduler.set_task_callback(schedule_callback)
        
        if scheduler_config['mode'] == 'interval':
            self.scheduler.set_interval_mode(scheduler_config['interval_hours'])
        elif scheduler_config['mode'] == 'schedule':
            self.scheduler.set_schedule_mode(scheduler_config['schedule_times'])
        else:
            self.scheduler.set_immediate_mode()
    
    def _handle_auth_clicked(self):
        """Обработка нажатия кнопки авторизации"""
        if self.is_authenticated:
            self._logout()
        else:
            # Если уже идет автоматическая авторизация, не открываем окно
            if self.telegram_client and not self.is_authenticated:
                self.main_window.add_log("Ожидание автоматической авторизации...", "INFO")
                return
            self._show_auth_window()
    
    def _show_auth_window(self):
        """Показать окно авторизации"""
        if self.auth_window:
            return
        
        self.auth_window = AuthWindow(self.root)
        self.auth_window.on_auth_requested = self._handle_auth_request
        self.auth_window.on_code_submitted = self._handle_code_submit
        
        # Загружаем сохраненные credentials
        api_id = self.config.get_telegram_api_id()
        api_hash = self.config.get_telegram_api_hash()
        if api_id and api_hash:
            self.auth_window.set_api_credentials(api_id, api_hash)
        
        self.auth_window.window.protocol("WM_DELETE_WINDOW", self._close_auth_window)
    
    def _close_auth_window(self):
        """Закрыть окно авторизации"""
        if self.auth_window:
            self.auth_window.close()
            self.auth_window = None
    
    async def _handle_auth_request_async(self, api_id: int, api_hash: str, phone: str):
        """Асинхронная обработка запроса авторизации"""
        try:
            # Сохраняем credentials
            self.config.set_telegram_credentials(api_id, api_hash)
            
            # Создаем клиент
            session_file = self.config.get_session_file()
            self.telegram_client = TelegramClientWrapper(api_id, api_hash, session_file)
            
            # Пытаемся подключиться
            result = await self.telegram_client.authenticate(phone)
            
            if result.get("needs_code"):
                self.root.after(0, lambda: self.auth_window.enable_code_input())
                self.root.after(0, lambda: self.auth_window.set_status("Код отправлен. Проверьте Telegram"))
            elif result.get("authorized"):
                self.root.after(0, lambda: self._on_auth_success(result.get("user")))
            else:
                error = result.get("error", "Неизвестная ошибка")
                self.root.after(0, lambda: self.auth_window.set_status(error, error=True))
        except Exception as e:
            logger.error(f"Ошибка авторизации: {e}")
            self.root.after(0, lambda: self.auth_window.set_status(str(e), error=True))
    
    def _handle_auth_request(self, api_id: int, api_hash: str, phone: str):
        """Обработка запроса авторизации"""
        asyncio.run_coroutine_threadsafe(
            self._handle_auth_request_async(api_id, api_hash, phone),
            self.loop
        )
    
    async def _handle_code_submit_async(self, code: str, password: str = None):
        """Асинхронная обработка кода"""
        try:
            phone = self.auth_window.phone_entry.get().strip()
            result = await self.telegram_client.sign_in(phone, code, password)
            
            if result.get("success"):
                user = result.get("user")
                self.root.after(0, lambda: self._on_auth_success(user))
            elif result.get("needs_password"):
                self.root.after(0, lambda: self.auth_window.enable_password_input())
                self.root.after(0, lambda: self.auth_window.set_status("Требуется пароль 2FA"))
            else:
                error = result.get("error", "Неверный код")
                self.root.after(0, lambda: self.auth_window.set_status(error, error=True))
        except Exception as e:
            logger.error(f"Ошибка входа: {e}")
            self.root.after(0, lambda: self.auth_window.set_status(str(e), error=True))
    
    def _handle_code_submit(self, code: str, password: str = None):
        """Обработка отправки кода"""
        asyncio.run_coroutine_threadsafe(
            self._handle_code_submit_async(code, password),
            self.loop
        )
    
    def _on_auth_success(self, user):
        """Обработка успешной авторизации"""
        self.is_authenticated = True
        username = f"{user.first_name or ''} {user.last_name or ''}".strip() or user.phone
        self.main_window.set_auth_status(True, username)
        self.main_window.enable_send_button(True)
        self._close_auth_window()
        
        # Инициализируем отправитель сообщений
        self.message_sender = MessageSender(self.telegram_client, self.delay_manager)
        self.message_sender.set_progress_callback(
            lambda progress, status: self.root.after(0, 
                lambda: self.main_window.set_progress(progress, status))
        )
        # Устанавливаем callback для вывода результатов в реальном времени
        self.message_sender.set_result_callback(
            lambda group, link_or_error, status: self.root.after(0,
                lambda g=group, l=link_or_error, s=status: self._handle_result_update(g, l, s))
        )
        
        logger.info(f"Успешная авторизация: {username}")
    
    def _logout(self):
        """Выход из аккаунта"""
        if self.telegram_client:
            asyncio.run_coroutine_threadsafe(
                self.telegram_client.disconnect(),
                self.loop
            )
        self.is_authenticated = False
        self.main_window.set_auth_status(False)
        self.main_window.enable_send_button(False)
        self.telegram_client = None
        self.message_sender = None
    
    def _handle_load_groups(self, filepath: str):
        """Обработка загрузки групп из файла"""
        try:
            groups = self.group_manager.load_from_file(filepath)
            for group in groups:
                self.main_window.add_group(group)
            self.main_window.add_log(f"Загружено {len(groups)} групп из файла")
            self._save_groups()
        except Exception as e:
            logger.error(f"Ошибка загрузки групп: {e}")
            self.main_window.add_log(f"Ошибка загрузки: {e}", "ERROR")
    
    def _handle_select_groups(self):
        """Обработка выбора групп вручную"""
        if not self.is_authenticated:
            self.main_window.add_log("Сначала авторизуйтесь", "ERROR")
            messagebox.showerror("Ошибка", "Сначала авторизуйтесь в Telegram")
            return
        
        # Проверяем, существует ли окно и не уничтожено ли оно
        if self.group_select_window:
            try:
                # Проверяем, существует ли окно
                if self.group_select_window.window.winfo_exists():
                    # Окно существует, поднимаем его на передний план
                    self.group_select_window.window.lift()
                    self.group_select_window.window.focus_force()
                    return
            except tk.TclError:
                # Окно было уничтожено, но ссылка осталась
                self.group_select_window = None
        
        # Создаем новое окно
        self.group_select_window = GroupSelectWindow(self.root)
        self.group_select_window.on_groups_selected = self._handle_groups_selected
        self.group_select_window.on_load_dialogs = self._handle_load_dialogs
        self.group_select_window.window.protocol("WM_DELETE_WINDOW", self._close_group_select_window)
        
        # Загружаем диалоги при открытии окна
        self._handle_load_dialogs()
    
    def _close_group_select_window(self):
        """Закрыть окно выбора групп"""
        if self.group_select_window:
            try:
                self.group_select_window.window.destroy()
            except tk.TclError:
                # Окно уже уничтожено
                pass
            finally:
                # Всегда сбрасываем ссылку, чтобы можно было открыть окно снова
                self.group_select_window = None
                logger.debug("Окно выбора групп закрыто, ссылка сброшена")
    
    async def _load_dialogs_async(self):
        """Асинхронная загрузка диалогов"""
        try:
            # Загружаем все диалоги (используем большое число вместо None)
            dialogs = await self.telegram_client.get_dialogs(limit=10000)  # Большой лимит для загрузки всех
            # Фильтруем только группы и каналы
            groups = [d for d in dialogs if d.get("type") in ["group", "channel"]]
            self.root.after(0, lambda: self.group_select_window.set_dialogs(groups))
        except Exception as e:
            logger.error(f"Ошибка загрузки диалогов: {e}")
            self.root.after(0, lambda: self.group_select_window.set_status_error(f"Ошибка: {str(e)}"))
    
    def _handle_load_dialogs(self):
        """Обработка загрузки диалогов"""
        if not self.is_authenticated or not self.telegram_client:
            if self.group_select_window:
                self.group_select_window.set_status_error("Не авторизован")
            return
        
        asyncio.run_coroutine_threadsafe(
            self._load_dialogs_async(),
            self.loop
        )
    
    def _handle_groups_selected(self, groups: List[str]):
        """Обработка выбранных групп"""
        for group in groups:
            # Добавляем через group_manager для валидации
            if self.group_manager.add_group(group):
                self.main_window.add_group(group)
                self.main_window.add_log(f"Добавлена группа: {group}", "INFO")
            else:
                self.main_window.add_log(f"Не удалось добавить группу: {group}", "WARNING")
        self._save_groups()
    
    def _handle_delete_group(self, group: str):
        """Обработка удаления группы"""
        self.group_manager.remove_group(group)
        self._save_groups()
        logger.info(f"Удалена группа: {group}")
    
    def _handle_clear_groups(self):
        """Обработка очистки групп"""
        self.group_manager.clear_groups()
        self._save_groups()
        logger.info("Список групп очищен")
    
    def _save_groups(self):
        """Сохранение списка групп в конфигурацию"""
        groups = self.main_window.get_groups()
        logger.info(f"Сохранение {len(groups)} групп: {groups}")
        self.config.set_selected_groups(groups)
        logger.info(f"Группы сохранены в конфигурацию")
    
    def _handle_delays_changed(self):
        """Обработка изменения настроек задержек"""
        delays_config = self.main_window.get_delays_config()
        self.config.set_delays(
            send_min_minutes=delays_config['send_min_minutes'],
            send_max_minutes=delays_config['send_max_minutes']
        )
        # Обновляем delay_manager
        self.delay_manager.update_delays(
            send_min_minutes=delays_config['send_min_minutes'],
            send_max_minutes=delays_config['send_max_minutes']
        )
        logger.info(f"Настройки задержек обновлены: {delays_config['send_min_minutes']}-{delays_config['send_max_minutes']} минут")
    
    def _handle_export_groups(self):
        """Обработка экспорта групп"""
        if not self.is_authenticated:
            self.main_window.add_log("Сначала авторизуйтесь", "ERROR")
            messagebox.showerror("Ошибка", "Сначала авторизуйтесь в Telegram")
            return
        
        if self.export_groups_window:
            try:
                if self.export_groups_window.window.winfo_exists():
                    self.export_groups_window.window.lift()
                    self.export_groups_window.window.focus_force()
                    return
            except tk.TclError:
                self.export_groups_window = None
        
        self.export_groups_window = ExportGroupsWindow(self.root)
        self.export_groups_window.on_export_selected = self._handle_export_selected_groups
        self.export_groups_window.on_export_all = self._handle_export_all_groups
        self.export_groups_window.window.protocol("WM_DELETE_WINDOW", self._close_export_window)
    
    def _close_export_window(self):
        """Закрыть окно экспорта"""
        if self.export_groups_window:
            try:
                self.export_groups_window.window.destroy()
            except tk.TclError:
                pass
            finally:
                self.export_groups_window = None
    
    def _handle_export_selected_groups(self):
        """Экспорт выбранных групп"""
        groups = self.main_window.get_groups()
        if not groups:
            messagebox.showwarning("Предупреждение", "Нет выбранных групп для экспорта")
            return
        
        # Выбираем файл для сохранения
        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Текстовые файлы", "*.txt"), ("Все файлы", "*.*")],
            title="Сохранить группы"
        )
        
        if not filepath:
            return
        
        try:
            # Сохраняем группы в файл
            with open(filepath, 'w', encoding='utf-8') as f:
                for group in groups:
                    f.write(f"{group}\n")
            
            self.main_window.add_log(f"Экспортировано {len(groups)} групп в файл", "INFO")
            messagebox.showinfo("Успех", f"Экспортировано {len(groups)} групп в файл:\n{filepath}")
            logger.info(f"Экспортировано {len(groups)} групп в {filepath}")
        except Exception as e:
            logger.error(f"Ошибка экспорта групп: {e}")
            self.main_window.add_log(f"Ошибка экспорта: {e}", "ERROR")
            messagebox.showerror("Ошибка", f"Не удалось экспортировать группы:\n{str(e)}")
    
    def _handle_export_all_groups(self):
        """Экспорт всех групп из Telegram"""
        if not self.is_authenticated or not self.telegram_client:
            self.main_window.add_log("Сначала авторизуйтесь", "ERROR")
            messagebox.showerror("Ошибка", "Сначала авторизуйтесь в Telegram")
            return
        
        # Выбираем файл для сохранения
        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Текстовые файлы", "*.txt"), ("Все файлы", "*.*")],
            title="Сохранить все группы"
        )
        
        if not filepath:
            return
        
        # Загружаем все группы из Telegram
        self.main_window.add_log("Загрузка всех групп из Telegram...", "INFO")
        asyncio.run_coroutine_threadsafe(
            self._export_all_groups_async(filepath),
            self.loop
        )
    
    async def _export_all_groups_async(self, filepath: str):
        """Асинхронный экспорт всех групп"""
        try:
            # Получаем все диалоги
            dialogs = await self.telegram_client.get_dialogs(limit=1000)
            
            # Фильтруем только группы и каналы
            groups = []
            for dialog in dialogs:
                if dialog.get("type") in ["group", "channel"]:
                    # Формируем адрес группы
                    username = dialog.get("username")
                    if username:
                        groups.append(f"@{username}")
                    else:
                        # Если нет username, используем ID
                        groups.append(str(dialog.get("id")))
            
            # Удаляем дубликаты
            groups = list(dict.fromkeys(groups))
            
            # Сохраняем в файл
            with open(filepath, 'w', encoding='utf-8') as f:
                for group in groups:
                    f.write(f"{group}\n")
            
            self.root.after(0, lambda: self.main_window.add_log(
                f"Экспортировано {len(groups)} групп в файл", "INFO"))
            self.root.after(0, lambda: messagebox.showinfo(
                "Успех", f"Экспортировано {len(groups)} групп в файл:\n{filepath}"))
            logger.info(f"Экспортировано {len(groups)} групп в {filepath}")
        except Exception as e:
            logger.error(f"Ошибка экспорта всех групп: {e}")
            self.root.after(0, lambda: self.main_window.add_log(
                f"Ошибка экспорта: {e}", "ERROR"))
            self.root.after(0, lambda: messagebox.showerror(
                "Ошибка", f"Не удалось экспортировать группы:\n{str(e)}"))
    
    async def _run_send_async(self):
        """Асинхронная рассылка"""
        if not self.is_authenticated or not self.message_sender:
            return
        
        groups = self.main_window.get_groups()
        message = self.main_window.get_message_text()
        
        if not groups:
            self.root.after(0, lambda: self.main_window.add_log("Нет выбранных групп", "ERROR"))
            return
        
        if not message:
            self.root.after(0, lambda: self.main_window.add_log("Сообщение пустое", "ERROR"))
            return
        
        # Сохраняем сообщение
        self.config.set_message_text(message)
        
        # Рассылаем сообщения (внутри автоматически проверяется членство и вступление)
        self.root.after(0, lambda: self.main_window.add_log("Начало рассылки...", "INFO"))
        send_results = await self.message_sender.send_to_groups(groups, message)
        
        # Формируем детальный отчет
        report_parts = [f"Отправлено: {send_results['sent']}"]
        if send_results.get('joined', 0) > 0:
            report_parts.append(f"Вступили: {send_results['joined']}")
        if send_results.get('already_member', 0) > 0:
            report_parts.append(f"Уже состояли: {send_results['already_member']}")
        if send_results.get('no_permission', 0) > 0:
            report_parts.append(f"Нет прав: {send_results['no_permission']}")
        if send_results['failed'] > 0:
            report_parts.append(f"Ошибок: {send_results['failed']}")
        
        self.root.after(0, lambda: self.main_window.add_log(
            f"Рассылка завершена: {', '.join(report_parts)}", "INFO"))
        
        # Выводим детали по каждому сообщению
        for detail in send_results.get('details', []):
            if detail.get('action') == 'send':
                group = detail.get('group', '')
                if detail.get('success'):
                    message_link = detail.get('message_link', '')
                    if message_link:
                        self.root.after(0, lambda g=group, link=message_link: 
                            self.main_window.add_log(f"✓ {g}: {link}", "SUCCESS"))
                    else:
                        self.root.after(0, lambda g=group: 
                            self.main_window.add_log(f"✓ {g}: сообщение отправлено", "SUCCESS"))
                else:
                    error = detail.get('error', 'Неизвестная ошибка')
                    self.root.after(0, lambda g=group, e=error: 
                        self.main_window.add_log(f"✗ {g}: {e}", "ERROR"))
    
    def _handle_result_update(self, group: str, link_or_error: str, status: str):
        """
        Обработка результата отправки сообщения в реальном времени
        
        Args:
            group: Название группы
            link_or_error: Ссылка на сообщение (при успехе) или описание ошибки (при ошибке)
            status: Статус ("SUCCESS" или "ERROR")
        """
        if status == "SUCCESS":
            if link_or_error:
                self.main_window.add_log(f"✓ {group}: {link_or_error}", "SUCCESS")
            else:
                self.main_window.add_log(f"✓ {group}: сообщение отправлено", "SUCCESS")
        else:
            self.main_window.add_log(f"✗ {group}: {link_or_error}", "ERROR")
    
    def _handle_send_clicked(self):
        """Обработка нажатия кнопки рассылки"""
        if not self.is_authenticated:
            self.main_window.add_log("Сначала авторизуйтесь", "ERROR")
            return
        
        asyncio.run_coroutine_threadsafe(
            self._run_send_async(),
            self.loop
        )
    
    async def _run_scheduled_send(self):
        """Выполнение запланированной рассылки"""
        await self._run_send_async()
    
    def _handle_scheduler_changed(self):
        """Обработка изменения настроек планировщика"""
        config = self.main_window.get_scheduler_config()
        # Сохраняем настройки
        self.config.set_scheduler_config(
            enabled=False,  # Не включаем автоматически
            mode=config['mode'],
            interval_hours=config.get('interval_hours'),
            schedule_times=config.get('schedule_times'),
            timezone=config['timezone']
        )
    
    def _handle_scheduler_toggle(self):
        """Обработка включения/выключения планировщика"""
        if self.scheduler.is_enabled():
            # Выключаем
            try:
                self.scheduler.stop()
                self.config.set_scheduler_config(
                    enabled=False,
                    mode=self.scheduler.get_mode(),
                    interval_hours=self.scheduler._interval_hours,
                    schedule_times=self.scheduler._schedule_times,
                    timezone=self.scheduler.timezone.zone
                )
                self.main_window.set_scheduler_status(False)
                self.main_window.add_log("Планировщик выключен", "INFO")
            except Exception as e:
                logger.error(f"Ошибка при выключении планировщика: {e}")
                self.main_window.add_log(f"Ошибка при выключении: {e}", "ERROR")
        else:
            # Включаем
            # Проверяем авторизацию
            if not self.is_authenticated:
                self.main_window.add_log("Сначала авторизуйтесь", "ERROR")
                messagebox.showerror("Ошибка", "Сначала авторизуйтесь в Telegram")
                return
            
            # Проверяем наличие групп
            groups = self.main_window.get_groups()
            if not groups:
                self.main_window.add_log("Добавьте группы для рассылки", "ERROR")
                messagebox.showerror("Ошибка", "Добавьте хотя бы одну группу для рассылки")
                return
            
            # Проверяем наличие сообщения
            message = self.main_window.get_message_text()
            if not message:
                self.main_window.add_log("Введите текст сообщения", "ERROR")
                messagebox.showerror("Ошибка", "Введите текст сообщения для рассылки")
                return
            
            try:
                config = self.main_window.get_scheduler_config()
                
                if config['mode'] == 'immediate':
                    self.main_window.add_log("Для немедленной рассылки используйте кнопку 'Начать рассылку'", "WARNING")
                    messagebox.showinfo("Информация", 
                                      "Для немедленной рассылки используйте кнопку 'Начать рассылку'.\n"
                                      "Выберите режим 'Интервал' или 'Расписание' для планировщика.")
                    return
                
                if config['mode'] == 'interval':
                    interval = config.get('interval_hours', 3)
                    if not interval or interval <= 0:
                        self.main_window.add_log("Укажите интервал в часах", "ERROR")
                        messagebox.showerror("Ошибка", "Укажите интервал в часах (например, 3)")
                        return
                    self.scheduler.set_interval_mode(interval)
                    
                elif config['mode'] == 'schedule':
                    times = config.get('schedule_times', [])
                    if not times:
                        self.main_window.add_log("Укажите времена для рассылки", "ERROR")
                        messagebox.showerror("Ошибка", 
                                           "Укажите времена для рассылки через запятую\n"
                                           "(например: 9,12,14,19)")
                        return
                    self.scheduler.set_schedule_mode(times)
                else:
                    self.main_window.add_log("Выберите режим планировщика", "ERROR")
                    return
                
                self.scheduler.set_timezone(config['timezone'])
                self.scheduler.start()
                
                self.config.set_scheduler_config(
                    enabled=True,
                    mode=config['mode'],
                    interval_hours=config.get('interval_hours'),
                    schedule_times=config.get('schedule_times'),
                    timezone=config['timezone']
                )
                
                next_run = self.scheduler.get_next_run_time()
                if next_run:
                    next_run_str = next_run.strftime("%Y-%m-%d %H:%M:%S")
                    self.main_window.set_scheduler_status(True, next_run_str)
                    self.main_window.add_log(f"Планировщик включен. Следующая рассылка: {next_run_str}", "INFO")
                else:
                    self.main_window.set_scheduler_status(True, "Скоро")
                    self.main_window.add_log("Планировщик включен", "INFO")
                    
            except Exception as e:
                logger.error(f"Ошибка при включении планировщика: {e}")
                self.main_window.add_log(f"Ошибка при включении планировщика: {e}", "ERROR")
                messagebox.showerror("Ошибка", f"Не удалось включить планировщик:\n{str(e)}")
    
    def run(self):
        """Запуск приложения"""
        # Создаем event loop в отдельном потоке
        self.loop = asyncio.new_event_loop()
        
        def run_loop():
            asyncio.set_event_loop(self.loop)
            self.loop.run_forever()
        
        thread = Thread(target=run_loop, daemon=True)
        thread.start()
        
        # Ждем немного, чтобы loop точно запустился
        import time
        time.sleep(0.3)
        
        # Попытка автоматической авторизации при запуске (после запуска event loop)
        # Используем after для гарантии, что GUI уже инициализирован
        self.root.after(100, self._try_auto_auth)
        
        # Запускаем GUI
        self.root.mainloop()
        
        # Очистка
        if self.scheduler:
            self.scheduler.stop()
        if self.telegram_client:
            asyncio.run_coroutine_threadsafe(
                self.telegram_client.disconnect(),
                self.loop
            )
        self.loop.call_soon_threadsafe(self.loop.stop)


if __name__ == "__main__":
    app = Application()
    app.run()

