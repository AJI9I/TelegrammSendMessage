"""
Главное окно приложения
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from typing import Optional, Callable
import asyncio
from datetime import datetime
from src.utils.logger import setup_logger

logger = setup_logger()


class MainWindow:
    """Главное окно приложения"""
    
    def __init__(self, root: tk.Tk):
        """
        Инициализация главного окна
        
        Args:
            root: Корневое окно tkinter
        """
        self.root = root
        self.root.title("TeggammMessage - Рассылка сообщений в Telegram")
        self.root.geometry("900x700")
        
        # Callbacks
        self.on_auth_clicked: Optional[Callable] = None
        self.on_send_clicked: Optional[Callable] = None
        self.on_load_groups_clicked: Optional[Callable] = None
        self.on_select_groups_clicked: Optional[Callable] = None
        self.on_scheduler_changed: Optional[Callable] = None
        self.on_scheduler_toggle: Optional[Callable] = None
        self.on_delete_group: Optional[Callable] = None
        self.on_clear_groups: Optional[Callable] = None
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Создание виджетов интерфейса"""
        # Верхняя панель
        top_frame = ttk.Frame(self.root, padding="10")
        top_frame.pack(fill=tk.X)
        
        # Статус авторизации
        self.auth_status_label = ttk.Label(top_frame, text="Не авторизован", foreground="red")
        self.auth_status_label.pack(side=tk.LEFT)
        
        self.auth_button = ttk.Button(top_frame, text="Авторизация", command=self._on_auth_clicked)
        self.auth_button.pack(side=tk.RIGHT)
        
        # Разделитель
        ttk.Separator(self.root, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)
        
        # Левая панель
        left_frame = ttk.Frame(self.root, padding="10")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Сообщение
        ttk.Label(left_frame, text="Текст сообщения:").pack(anchor=tk.W)
        self.message_text = scrolledtext.ScrolledText(left_frame, height=10, width=50, wrap=tk.WORD)
        self.message_text.pack(fill=tk.BOTH, expand=True, pady=(5, 10))
        
        # Включаем стандартные горячие клавиши для текстового поля
        self.message_text.bind('<Control-v>', lambda e: self._paste_text(self.message_text))
        self.message_text.bind('<Control-V>', lambda e: self._paste_text(self.message_text))
        # Контекстное меню для вставки
        self._create_text_context_menu(self.message_text)
        
        # Счетчик символов
        self.char_count_label = ttk.Label(left_frame, text="Символов: 0")
        self.char_count_label.pack(anchor=tk.W)
        self.message_text.bind('<KeyRelease>', self._update_char_count)
        
        # Планировщик
        scheduler_frame = ttk.LabelFrame(left_frame, text="Планировщик рассылок", padding="10")
        scheduler_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Режим планировщика
        mode_frame = ttk.Frame(scheduler_frame)
        mode_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(mode_frame, text="Режим:").pack(side=tk.LEFT)
        self.scheduler_mode = tk.StringVar(value="immediate")
        ttk.Radiobutton(mode_frame, text="Немедленно", variable=self.scheduler_mode, 
                       value="immediate", command=self._on_mode_changed).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(mode_frame, text="Интервал", variable=self.scheduler_mode, 
                       value="interval", command=self._on_mode_changed).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(mode_frame, text="Расписание", variable=self.scheduler_mode, 
                       value="schedule", command=self._on_mode_changed).pack(side=tk.LEFT, padx=5)
        
        # Настройки интервала
        self.interval_frame = ttk.Frame(scheduler_frame)
        self.interval_frame.pack(fill=tk.X, pady=5)
        ttk.Label(self.interval_frame, text="Каждые").pack(side=tk.LEFT)
        self.interval_entry = ttk.Entry(self.interval_frame, width=5)
        self.interval_entry.pack(side=tk.LEFT, padx=5)
        self.interval_entry.insert(0, "3")
        # Включаем горячие клавиши для вставки
        self.interval_entry.bind('<Control-v>', lambda e: self._paste_entry(self.interval_entry))
        self.interval_entry.bind('<Control-V>', lambda e: self._paste_entry(self.interval_entry))
        ttk.Label(self.interval_frame, text="часов").pack(side=tk.LEFT)
        self.interval_frame.pack_forget()  # Скрываем по умолчанию
        
        # Настройки расписания
        self.schedule_frame = ttk.Frame(scheduler_frame)
        self.schedule_frame.pack(fill=tk.X, pady=5)
        ttk.Label(self.schedule_frame, text="Времена (через запятую):").pack(side=tk.LEFT)
        self.schedule_entry = ttk.Entry(self.schedule_frame, width=30)
        self.schedule_entry.pack(side=tk.LEFT, padx=5)
        self.schedule_entry.insert(0, "9,12,14,19")
        # Включаем горячие клавиши для вставки
        self.schedule_entry.bind('<Control-v>', lambda e: self._paste_entry(self.schedule_entry))
        self.schedule_entry.bind('<Control-V>', lambda e: self._paste_entry(self.schedule_entry))
        self.schedule_frame.pack_forget()  # Скрываем по умолчанию
        
        # Часовой пояс
        timezone_frame = ttk.Frame(scheduler_frame)
        timezone_frame.pack(fill=tk.X, pady=5)
        ttk.Label(timezone_frame, text="Часовой пояс:").pack(side=tk.LEFT)
        self.timezone_var = tk.StringVar(value="UTC")
        timezone_combo = ttk.Combobox(timezone_frame, textvariable=self.timezone_var, 
                                     values=["UTC", "Europe/Moscow", "Europe/Kiev", "Asia/Almaty"],
                                     width=20, state="readonly")
        timezone_combo.pack(side=tk.LEFT, padx=5)
        
        # Кнопка включения планировщика
        self.scheduler_toggle_button = ttk.Button(scheduler_frame, text="Включить планировщик",
                                                  command=self._on_scheduler_toggle)
        self.scheduler_toggle_button.pack(pady=5)
        
        # Следующая рассылка
        self.next_run_label = ttk.Label(scheduler_frame, text="Следующая рассылка: -", 
                                        foreground="gray")
        self.next_run_label.pack(pady=5)
        
        # Правая панель
        right_frame = ttk.Frame(self.root, padding="10")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Группы
        ttk.Label(right_frame, text="Выбранные группы:").pack(anchor=tk.W)
        
        groups_list_frame = ttk.Frame(right_frame)
        groups_list_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 10))
        
        # Список групп
        self.groups_listbox = tk.Listbox(groups_list_frame, height=15)
        self.groups_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(groups_list_frame, orient=tk.VERTICAL, 
                                 command=self.groups_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.groups_listbox.config(yscrollcommand=scrollbar.set)
        
        # Кнопки управления группами
        groups_buttons_frame = ttk.Frame(right_frame)
        groups_buttons_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(groups_buttons_frame, text="Загрузить из файла", 
                  command=self._on_load_groups_clicked).pack(fill=tk.X, pady=2)
        ttk.Button(groups_buttons_frame, text="Выбрать вручную", 
                  command=self._on_select_groups_clicked).pack(fill=tk.X, pady=2)
        ttk.Button(groups_buttons_frame, text="Удалить выбранную", 
                  command=self._remove_selected_group).pack(fill=tk.X, pady=2)
        ttk.Button(groups_buttons_frame, text="Очистить список", 
                  command=self._clear_groups).pack(fill=tk.X, pady=2)
        
        # Кнопка рассылки
        self.send_button = ttk.Button(right_frame, text="Начать рассылку", 
                                      command=self._on_send_clicked, state=tk.DISABLED)
        self.send_button.pack(fill=tk.X, pady=10)
        
        # Прогресс
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(right_frame, variable=self.progress_var, 
                                           maximum=100, length=300)
        self.progress_bar.pack(fill=tk.X, pady=5)
        
        self.status_label = ttk.Label(right_frame, text="Готов", foreground="gray")
        self.status_label.pack(pady=5)
        
        # Логи
        ttk.Label(right_frame, text="Логи:").pack(anchor=tk.W, pady=(10, 0))
        self.log_text = scrolledtext.ScrolledText(right_frame, height=8, width=40, 
                                                  state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True, pady=5)
    
    def _update_char_count(self, event=None):
        """Обновление счетчика символов"""
        count = len(self.message_text.get("1.0", tk.END)) - 1  # -1 для символа новой строки
        self.char_count_label.config(text=f"Символов: {count}")
    
    def _paste_text(self, widget):
        """Вставка текста в текстовое поле"""
        try:
            text = self.root.clipboard_get()
            widget.insert(tk.INSERT, text)
            self._update_char_count()
            return "break"  # Предотвращаем стандартную обработку
        except tk.TclError:
            pass
    
    def _paste_entry(self, widget):
        """Вставка текста в поле ввода"""
        try:
            text = self.root.clipboard_get()
            widget.insert(tk.INSERT, text)
            return "break"  # Предотвращаем стандартную обработку
        except tk.TclError:
            pass
    
    def _create_text_context_menu(self, widget):
        """Создание контекстного меню для текстового поля"""
        context_menu = tk.Menu(self.root, tearoff=0)
        context_menu.add_command(label="Вставить", command=lambda: self._paste_text(widget))
        context_menu.add_separator()
        context_menu.add_command(label="Вырезать", command=lambda: widget.event_generate("<<Cut>>"))
        context_menu.add_command(label="Копировать", command=lambda: widget.event_generate("<<Copy>>"))
        
        def show_context_menu(event):
            try:
                context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                context_menu.grab_release()
        
        widget.bind("<Button-3>", show_context_menu)  # Правая кнопка мыши
        widget.bind("<Button-2>", show_context_menu)  # Средняя кнопка мыши (для Mac)
    
    def _on_mode_changed(self):
        """Обработка изменения режима планировщика"""
        mode = self.scheduler_mode.get()
        if mode == "interval":
            self.interval_frame.pack(fill=tk.X, pady=5)
            self.schedule_frame.pack_forget()
        elif mode == "schedule":
            self.schedule_frame.pack(fill=tk.X, pady=5)
            self.interval_frame.pack_forget()
        else:
            self.interval_frame.pack_forget()
            self.schedule_frame.pack_forget()
        
        if self.on_scheduler_changed:
            self.on_scheduler_changed()
    
    def _on_scheduler_toggle(self):
        """Обработка включения/выключения планировщика"""
        if self.on_scheduler_toggle:
            self.on_scheduler_toggle()
    
    def _on_auth_clicked(self):
        """Обработка нажатия кнопки авторизации"""
        if self.on_auth_clicked:
            self.on_auth_clicked()
    
    def _on_send_clicked(self):
        """Обработка нажатия кнопки рассылки"""
        if self.on_send_clicked:
            self.on_send_clicked()
    
    def _on_load_groups_clicked(self):
        """Обработка загрузки групп из файла"""
        if self.on_load_groups_clicked:
            filepath = filedialog.askopenfilename(
                title="Выберите файл с группами",
                filetypes=[("Текстовые файлы", "*.txt"), ("Все файлы", "*.*")]
            )
            if filepath:
                self.on_load_groups_clicked(filepath)
    
    def _on_select_groups_clicked(self):
        """Обработка выбора групп вручную"""
        if self.on_select_groups_clicked:
            self.on_select_groups_clicked()
    
    def _remove_selected_group(self):
        """Удаление выбранной группы из списка"""
        selection = self.groups_listbox.curselection()
        if selection:
            index = selection[0]
            group = self.groups_listbox.get(index)
            self.groups_listbox.delete(index)
            # Вызываем callback для сохранения
            if self.on_delete_group:
                self.on_delete_group(group)
    
    def _clear_groups(self):
        """Очистка списка групп"""
        if messagebox.askyesno("Подтверждение", "Очистить список групп?"):
            self.groups_listbox.delete(0, tk.END)
            # Вызываем callback для сохранения
            if self.on_clear_groups:
                self.on_clear_groups()
    
    # Методы для обновления интерфейса
    def set_auth_status(self, authorized: bool, username: str = None):
        """Установка статуса авторизации"""
        if authorized:
            text = f"Авторизован: {username}" if username else "Авторизован"
            self.auth_status_label.config(text=text, foreground="green")
            self.auth_button.config(text="Выйти")
        else:
            self.auth_status_label.config(text="Не авторизован", foreground="red")
            self.auth_button.config(text="Авторизация")
    
    def get_message_text(self) -> str:
        """Получить текст сообщения"""
        return self.message_text.get("1.0", tk.END).strip()
    
    def set_message_text(self, text: str):
        """Установить текст сообщения"""
        self.message_text.delete("1.0", tk.END)
        self.message_text.insert("1.0", text)
        self._update_char_count()
    
    def add_group(self, group: str):
        """Добавить группу в список"""
        self.groups_listbox.insert(tk.END, group)
    
    def get_groups(self) -> list:
        """Получить список групп"""
        return list(self.groups_listbox.get(0, tk.END))
    
    def clear_groups(self):
        """Очистить список групп"""
        self.groups_listbox.delete(0, tk.END)
    
    def set_progress(self, value: float, status: str = None):
        """Установить прогресс"""
        self.progress_var.set(value)
        if status:
            self.status_label.config(text=status)
    
    def add_log(self, message: str, level: str = "INFO"):
        """Добавить запись в лог"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"[{timestamp}] {level}: {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    def get_scheduler_config(self) -> dict:
        """Получить настройки планировщика"""
        mode = self.scheduler_mode.get()
        config = {
            "mode": mode,
            "timezone": self.timezone_var.get()
        }
        
        if mode == "interval":
            try:
                config["interval_hours"] = int(self.interval_entry.get())
            except ValueError:
                config["interval_hours"] = 3
        elif mode == "schedule":
            times_str = self.schedule_entry.get()
            config["schedule_times"] = [t.strip() for t in times_str.split(',') if t.strip()]
        
        return config
    
    def set_scheduler_status(self, enabled: bool, next_run: str = None):
        """Установить статус планировщика"""
        if enabled:
            self.scheduler_toggle_button.config(text="Выключить планировщик")
            if next_run:
                self.next_run_label.config(text=f"Следующая рассылка: {next_run}", 
                                          foreground="green")
            else:
                self.next_run_label.config(text="Следующая рассылка: -", foreground="gray")
        else:
            self.scheduler_toggle_button.config(text="Включить планировщик")
            self.next_run_label.config(text="Следующая рассылка: -", foreground="gray")
    
    def enable_send_button(self, enabled: bool = True):
        """Включить/выключить кнопку рассылки"""
        self.send_button.config(state=tk.NORMAL if enabled else tk.DISABLED)

