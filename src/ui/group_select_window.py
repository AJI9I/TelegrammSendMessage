"""
Окно выбора групп вручную
"""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Dict, Optional, Callable
from src.utils.logger import setup_logger

logger = setup_logger()


class GroupSelectWindow:
    """Окно для выбора групп из списка диалогов с двумя списками"""
    
    def __init__(self, parent: tk.Tk):
        """
        Инициализация окна выбора групп
        
        Args:
            parent: Родительское окно
        """
        self.window = tk.Toplevel(parent)
        self.window.title("Выбор групп")
        self.window.geometry("900x600")
        self.window.transient(parent)
        self.window.grab_set()
        
        # Callbacks
        self.on_groups_selected: Optional[Callable] = None
        self.on_load_dialogs: Optional[Callable] = None
        
        # Данные
        self.dialogs: List[Dict] = []
        self.available_groups: List[Dict] = []  # Доступные группы
        self.selected_groups: List[Dict] = []   # Выбранные группы
        self._display_to_dialog: Dict[str, Dict] = {}  # Словарь для сопоставления текста с данными
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Создание виджетов"""
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Заголовок и кнопка обновления
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(header_frame, text="Выберите группы для рассылки:", 
                 font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        
        self.refresh_button = ttk.Button(header_frame, text="Обновить список", 
                                         command=self._on_refresh)
        self.refresh_button.pack(side=tk.RIGHT, padx=5)
        
        # Поиск
        search_frame = ttk.Frame(main_frame)
        search_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(search_frame, text="Поиск:").pack(side=tk.LEFT, padx=5)
        self.search_entry = ttk.Entry(search_frame)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.search_entry.bind('<KeyRelease>', self._on_search)
        
        # Контейнер для двух списков
        lists_container = ttk.Frame(main_frame)
        lists_container.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Левый список - Доступные группы
        left_frame = ttk.LabelFrame(lists_container, text="Доступные группы", padding="5")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # Scrollbar для левого списка
        left_scrollbar = ttk.Scrollbar(left_frame)
        left_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.available_listbox = tk.Listbox(left_frame, yscrollcommand=left_scrollbar.set,
                                            selectmode=tk.EXTENDED)
        self.available_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        left_scrollbar.config(command=self.available_listbox.yview)
        
        self.available_listbox.bind('<Double-Button-1>', lambda e: self._add_selected())
        
        # Кнопки переноса
        buttons_frame = ttk.Frame(lists_container)
        buttons_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        ttk.Button(buttons_frame, text="→", width=4, 
                  command=self._add_selected).pack(pady=5)
        ttk.Button(buttons_frame, text="←", width=4, 
                  command=self._remove_selected).pack(pady=5)
        ttk.Button(buttons_frame, text="→→", width=4, 
                  command=self._add_all).pack(pady=5)
        ttk.Button(buttons_frame, text="←←", width=4, 
                  command=self._remove_all).pack(pady=5)
        
        # Правый список - Выбранные группы
        right_frame = ttk.LabelFrame(lists_container, text="Выбранные группы", padding="5")
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # Scrollbar для правого списка
        right_scrollbar = ttk.Scrollbar(right_frame)
        right_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.selected_listbox = tk.Listbox(right_frame, yscrollcommand=right_scrollbar.set,
                                           selectmode=tk.EXTENDED)
        self.selected_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        right_scrollbar.config(command=self.selected_listbox.yview)
        
        self.selected_listbox.bind('<Double-Button-1>', lambda e: self._remove_selected())
        
        # Статус
        self.status_label = ttk.Label(main_frame, text="Нажмите 'Обновить список' для загрузки групп", 
                                     foreground="gray")
        self.status_label.pack(pady=5)
        
        # Кнопки действий
        buttons_frame_bottom = ttk.Frame(main_frame)
        buttons_frame_bottom.pack(fill=tk.X, pady=10)
        
        self.ok_button = ttk.Button(buttons_frame_bottom, text="Добавить выбранные", 
                                   command=self._on_ok, state=tk.DISABLED)
        self.ok_button.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        ttk.Button(buttons_frame_bottom, text="Отмена", 
                  command=self.window.destroy).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
    
    def _on_refresh(self):
        """Обновление списка диалогов"""
        self.status_label.config(text="Загрузка групп...", foreground="blue")
        self.refresh_button.config(state=tk.DISABLED)
        
        if self.on_load_dialogs:
            self.on_load_dialogs()
    
    def set_dialogs(self, dialogs: List[Dict]):
        """
        Установка списка диалогов
        
        Args:
            dialogs: Список диалогов
        """
        self.dialogs = dialogs
        # Показываем все группы и каналы (можно отправлять и по ID, и по username)
        self.available_groups = [
            d for d in dialogs 
            if d.get("type") in ["group", "channel"]
        ]
        self._update_lists()
        total_count = len(self.available_groups)
        self.status_label.config(
            text=f"Загружено групп: {total_count}", 
            foreground="green"
        )
        self.refresh_button.config(state=tk.NORMAL)
    
    def _update_lists(self, search_text: str = ""):
        """Обновление обоих списков"""
        # Очищаем списки и словарь
        self.available_listbox.delete(0, tk.END)
        self.selected_listbox.delete(0, tk.END)
        self._display_to_dialog.clear()
        
        # Получаем ключи выбранных групп
        selected_keys = {self._get_group_key(g) for g in self.selected_groups}
        
        # Фильтруем доступные группы
        filtered_available = self.available_groups
        if search_text:
            search_lower = search_text.lower()
            filtered_available = [
                d for d in self.available_groups
                if search_lower in d.get("name", "").lower() or 
                   (d.get("username") and search_lower in d.get("username", "").lower()) or
                   (str(d.get("id", "")) in search_text)  # Поиск по ID
            ]
        
        # Добавляем доступные группы (кроме уже выбранных)
        for dialog in filtered_available:
            key = self._get_group_key(dialog)
            if key not in selected_keys:
                display_text = self._format_group_display(dialog)
                self.available_listbox.insert(tk.END, display_text)
                # Сохраняем соответствие текста и данных
                self._display_to_dialog[display_text] = dialog
        
        # Добавляем выбранные группы
        for dialog in self.selected_groups:
            display_text = self._format_group_display(dialog)
            self.selected_listbox.insert(tk.END, display_text)
            # Сохраняем соответствие текста и данных
            self._display_to_dialog[display_text] = dialog
        
        self._update_ok_button()
    
    def _format_group_display(self, dialog: Dict) -> str:
        """Форматирование текста для отображения группы"""
        name = dialog.get('name', 'Без названия')
        username = dialog.get('username', '')
        dialog_type = dialog.get('type', 'group')
        
        if username:
            return f"{name} (@{username}) [{dialog_type}]"
        else:
            dialog_id = dialog.get('id', '')
            return f"{name} [ID: {dialog_id}] [{dialog_type}]"
    
    def _get_group_key(self, dialog: Dict) -> str:
        """Получить уникальный ключ группы"""
        return dialog.get("username") or str(dialog.get("id", ""))
    
    def _on_search(self, event=None):
        """Обработка поиска"""
        search_text = self.search_entry.get()
        self._update_lists(search_text)
    
    def _add_selected(self):
        """Добавить выбранные группы из доступных в выбранные"""
        selected_indices = self.available_listbox.curselection()
        if not selected_indices:
            return
        
        # Получаем выбранные группы
        selected_dialogs = []
        for idx in selected_indices:
            text = self.available_listbox.get(idx)
            if text in self._display_to_dialog:
                dialog = self._display_to_dialog[text]
                selected_dialogs.append(dialog)
        
        # Добавляем в выбранные (если еще не добавлены)
        for dialog in selected_dialogs:
            key = self._get_group_key(dialog)
            if not any(self._get_group_key(g) == key for g in self.selected_groups):
                self.selected_groups.append(dialog)
        
        self._update_lists(self.search_entry.get())
    
    def _remove_selected(self):
        """Удалить выбранные группы из выбранных"""
        selected_indices = self.selected_listbox.curselection()
        if not selected_indices:
            return
        
        # Получаем ключи выбранных групп
        selected_keys = set()
        for idx in selected_indices:
            text = self.selected_listbox.get(idx)
            if text in self._display_to_dialog:
                dialog = self._display_to_dialog[text]
                selected_keys.add(self._get_group_key(dialog))
        
        # Удаляем из выбранных
        self.selected_groups = [
            g for g in self.selected_groups 
            if self._get_group_key(g) not in selected_keys
        ]
        
        self._update_lists(self.search_entry.get())
    
    def _add_all(self):
        """Добавить все доступные группы в выбранные"""
        # Получаем все доступные группы
        available_keys = {self._get_group_key(g) for g in self.available_groups}
        selected_keys = {self._get_group_key(g) for g in self.selected_groups}
        
        # Добавляем те, которых еще нет в выбранных
        for dialog in self.available_groups:
            key = self._get_group_key(dialog)
            if key not in selected_keys:
                self.selected_groups.append(dialog)
        
        self._update_lists(self.search_entry.get())
    
    def _remove_all(self):
        """Удалить все группы из выбранных"""
        self.selected_groups.clear()
        self._update_lists(self.search_entry.get())
    
    def _update_ok_button(self):
        """Обновление состояния кнопки OK"""
        selected_count = len(self.selected_groups)
        if selected_count > 0:
            self.ok_button.config(state=tk.NORMAL, 
                                text=f"Добавить выбранные ({selected_count})")
        else:
            self.ok_button.config(state=tk.DISABLED, text="Добавить выбранные")
    
    def _on_ok(self):
        """Обработка нажатия OK"""
        if not self.selected_groups:
            messagebox.showwarning("Предупреждение", "Выберите хотя бы одну группу")
            return
        
        # Формируем список адресов групп
        # Формат: username без @, ID без знака минус (абсолютное значение)
        selected = []
        for dialog in self.selected_groups:
            if dialog.get("username"):
                # Username без @
                selected.append(dialog['username'])
            else:
                # ID без знака минус (абсолютное значение)
                group_id = dialog.get("id")
                if group_id:
                    selected.append(str(abs(int(group_id))))
        
        if selected and self.on_groups_selected:
            self.on_groups_selected(selected)
            # Закрываем окно - callback должен сбросить ссылку
            self.window.destroy()
    
    def set_status_error(self, message: str):
        """Установить статус ошибки"""
        self.status_label.config(text=message, foreground="red")
        self.refresh_button.config(state=tk.NORMAL)
