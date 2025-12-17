"""
Окно экспорта групп
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Optional, Callable
from src.utils.logger import setup_logger

logger = setup_logger()


class ExportGroupsWindow:
    """Окно для выбора режима экспорта групп"""
    
    def __init__(self, parent: tk.Tk):
        """
        Инициализация окна экспорта
        
        Args:
            parent: Родительское окно
        """
        self.window = tk.Toplevel(parent)
        self.window.title("Экспорт групп")
        self.window.geometry("400x200")
        self.window.transient(parent)
        self.window.grab_set()
        
        # Callbacks
        self.on_export_selected: Optional[Callable] = None
        self.on_export_all: Optional[Callable] = None
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Создание виджетов"""
        main_frame = ttk.Frame(self.window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="Выберите режим экспорта:", 
                 font=("Arial", 10, "bold")).pack(pady=10)
        
        # Кнопки выбора режима
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X, pady=20)
        
        ttk.Button(buttons_frame, text="Экспортировать выбранные группы", 
                  command=self._on_export_selected,
                  width=30).pack(fill=tk.X, pady=5)
        
        ttk.Button(buttons_frame, text="Экспортировать все группы из Telegram", 
                  command=self._on_export_all,
                  width=30).pack(fill=tk.X, pady=5)
        
        # Кнопка отмены
        ttk.Button(main_frame, text="Отмена", 
                  command=self.window.destroy).pack(pady=10)
    
    def _on_export_selected(self):
        """Экспорт выбранных групп"""
        if self.on_export_selected:
            self.on_export_selected()
        self.window.destroy()
    
    def _on_export_all(self):
        """Экспорт всех групп"""
        if self.on_export_all:
            self.on_export_all()
        self.window.destroy()
    
    def close(self):
        """Закрыть окно"""
        self.window.destroy()

