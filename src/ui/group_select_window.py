"""
Окно выбора групп вручную
"""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Dict, Optional, Callable
from src.utils.logger import setup_logger

logger = setup_logger()


class GroupSelectWindow:
    """Окно для выбора групп из списка диалогов"""
    
    def __init__(self, parent: tk.Tk):
        """
        Инициализация окна выбора групп
        
        Args:
            parent: Родительское окно
        """
        self.window = tk.Toplevel(parent)
        self.window.title("Выбор групп")
        self.window.geometry("600x500")
        self.window.transient(parent)
        self.window.grab_set()
        
        # Callbacks
        self.on_groups_selected: Optional[Callable] = None
        self.on_load_dialogs: Optional[Callable] = None
        
        # Данные
        self.dialogs: List[Dict] = []
        self.selected_groups: List[str] = []
        self._selected_keys: set = set()  # Сохраняем ключи выбранных групп
        
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
        
        # Список групп с чекбоксами
        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Canvas для прокрутки
        canvas = tk.Canvas(list_frame, yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=canvas.yview)
        
        # Фрейм для чекбоксов внутри canvas
        self.checkboxes_frame = ttk.Frame(canvas)
        canvas_window = canvas.create_window((0, 0), window=self.checkboxes_frame, anchor="nw")
        
        def configure_scroll_region(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
        
        def configure_canvas_width(event):
            canvas_width = event.width
            canvas.itemconfig(canvas_window, width=canvas_width)
        
        self.checkboxes_frame.bind("<Configure>", configure_scroll_region)
        canvas.bind("<Configure>", configure_canvas_width)
        
        self.canvas = canvas
        self.checkboxes_frame_inner = self.checkboxes_frame
        
        # Кнопки выбора
        select_buttons_frame = ttk.Frame(main_frame)
        select_buttons_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(select_buttons_frame, text="Выбрать все", 
                  command=self._select_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(select_buttons_frame, text="Снять выбор", 
                  command=self._deselect_all).pack(side=tk.LEFT, padx=5)
        
        # Статус
        self.status_label = ttk.Label(main_frame, text="Нажмите 'Обновить список' для загрузки групп", 
                                     foreground="gray")
        self.status_label.pack(pady=5)
        
        # Кнопки действий
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X, pady=10)
        
        self.ok_button = ttk.Button(buttons_frame, text="Добавить выбранные", 
                                   command=self._on_ok, state=tk.DISABLED)
        self.ok_button.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        ttk.Button(buttons_frame, text="Отмена", 
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
        self._update_list()
        self.status_label.config(text=f"Загружено групп: {len(dialogs)}", foreground="green")
        self.refresh_button.config(state=tk.NORMAL)
    
    def _update_list(self, search_text: str = ""):
        """Обновление списка групп"""
        # Сохраняем текущее состояние выбранных групп перед обновлением
        if hasattr(self, 'checkbox_vars'):
            self._selected_keys = {
                key for key, var in self.checkbox_vars.items() 
                if var.get()
            }
        else:
            self._selected_keys = set()
        
        # Очищаем существующие чекбоксы
        for widget in self.checkboxes_frame_inner.winfo_children():
            widget.destroy()
        
        # Фильтруем по поисковому запросу
        filtered_dialogs = self.dialogs
        if search_text:
            search_lower = search_text.lower()
            filtered_dialogs = [
                d for d in self.dialogs
                if search_lower in d.get("name", "").lower() or 
                   (d.get("username") and search_lower in d.get("username", "").lower())
            ]
        
        # Создаем чекбоксы для каждой группы
        self.checkbox_vars = {}
        for dialog in filtered_dialogs:
            key = dialog.get("username") or dialog.get("id")
            var = tk.BooleanVar()
            
            # Восстанавливаем состояние выбора, если группа была выбрана ранее
            if key in self._selected_keys:
                var.set(True)
            
            self.checkbox_vars[key] = var
            
            checkbox_frame = ttk.Frame(self.checkboxes_frame_inner)
            checkbox_frame.pack(fill=tk.X, pady=2)
            
            # Формируем текст для чекбокса
            name = dialog.get('name', 'Без названия')
            username = dialog.get('username')
            dialog_id = dialog.get('id')
            if username:
                checkbox_text = f"{name} (@{username})"
            else:
                checkbox_text = f"{name} [ID: {dialog_id}]"
            
            checkbox = ttk.Checkbutton(
                checkbox_frame,
                text=checkbox_text,
                variable=var,
                command=self._update_ok_button
            )
            checkbox.pack(side=tk.LEFT, anchor=tk.W)
            
            # Показываем тип
            type_label = ttk.Label(checkbox_frame, 
                                  text=f"[{dialog.get('type', 'group')}]",
                                  foreground="gray",
                                  font=("Arial", 8))
            type_label.pack(side=tk.RIGHT, padx=5)
        
        if not filtered_dialogs:
            ttk.Label(self.checkboxes_frame_inner, 
                     text="Группы не найдены",
                     foreground="gray").pack(pady=20)
        
        # Обновляем scroll region
        self.checkboxes_frame_inner.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def _on_search(self, event=None):
        """Обработка поиска"""
        search_text = self.search_entry.get()
        self._update_list(search_text)
    
    def _select_all(self):
        """Выбрать все группы"""
        for var in self.checkbox_vars.values():
            var.set(True)
        self._update_ok_button()
    
    def _deselect_all(self):
        """Снять выбор со всех групп"""
        for var in self.checkbox_vars.values():
            var.set(False)
        self._update_ok_button()
    
    def _update_ok_button(self):
        """Обновление состояния кнопки OK"""
        selected_count = sum(1 for var in self.checkbox_vars.values() if var.get())
        if selected_count > 0:
            self.ok_button.config(state=tk.NORMAL, 
                                text=f"Добавить выбранные ({selected_count})")
        else:
            self.ok_button.config(state=tk.DISABLED, text="Добавить выбранные")
    
    def _on_ok(self):
        """Обработка нажатия OK"""
        selected = []
        for dialog in self.dialogs:
            key = dialog.get("username") or dialog.get("id")
            if key in self.checkbox_vars and self.checkbox_vars[key].get():
                # Формируем адрес группы - используем username или ID
                if dialog.get("username"):
                    selected.append(f"@{dialog['username']}")
                else:
                    # Если нет username, используем ID
                    selected.append(str(dialog.get("id")))
        
        if selected and self.on_groups_selected:
            self.on_groups_selected(selected)
            # Закрываем окно - callback должен сбросить ссылку
            self.window.destroy()
        elif not selected:
            messagebox.showwarning("Предупреждение", "Выберите хотя бы одну группу")
    
    def set_status_error(self, message: str):
        """Установить статус ошибки"""
        self.status_label.config(text=message, foreground="red")
        self.refresh_button.config(state=tk.NORMAL)

