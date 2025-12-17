"""
Окно авторизации в Telegram
"""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Callable
from src.utils.logger import setup_logger

logger = setup_logger()


class AuthWindow:
    """Окно авторизации"""
    
    def __init__(self, parent: tk.Tk):
        """
        Инициализация окна авторизации
        
        Args:
            parent: Родительское окно
        """
        self.window = tk.Toplevel(parent)
        self.window.title("Авторизация в Telegram")
        self.window.geometry("500x400")
        self.window.transient(parent)
        self.window.grab_set()
        
        # Callbacks
        self.on_auth_requested: Optional[Callable] = None
        self.on_code_submitted: Optional[Callable] = None
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Создание виджетов"""
        main_frame = ttk.Frame(self.window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # API credentials
        creds_frame = ttk.LabelFrame(main_frame, text="API Credentials", padding="10")
        creds_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(creds_frame, text="API ID:").pack(anchor=tk.W)
        self.api_id_entry = ttk.Entry(creds_frame, width=40)
        self.api_id_entry.pack(fill=tk.X, pady=5)
        # Включаем горячие клавиши для вставки
        self.api_id_entry.bind('<Control-v>', lambda e: self._paste_entry(self.api_id_entry))
        self.api_id_entry.bind('<Control-V>', lambda e: self._paste_entry(self.api_id_entry))
        # Контекстное меню
        self._create_entry_context_menu(self.api_id_entry)
        
        ttk.Label(creds_frame, text="API Hash:").pack(anchor=tk.W, pady=(10, 0))
        self.api_hash_entry = ttk.Entry(creds_frame, width=40, show="*")
        self.api_hash_entry.pack(fill=tk.X, pady=5)
        # Включаем горячие клавиши для вставки
        self.api_hash_entry.bind('<Control-v>', lambda e: self._paste_entry(self.api_hash_entry))
        self.api_hash_entry.bind('<Control-V>', lambda e: self._paste_entry(self.api_hash_entry))
        # Контекстное меню
        self._create_entry_context_menu(self.api_hash_entry)
        
        ttk.Label(creds_frame, text="Получить на https://my.telegram.org", 
                 foreground="blue", cursor="hand2").pack(anchor=tk.W, pady=5)
        
        # Номер телефона
        phone_frame = ttk.LabelFrame(main_frame, text="Номер телефона", padding="10")
        phone_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(phone_frame, text="Номер телефона (с кодом страны):").pack(anchor=tk.W)
        self.phone_entry = ttk.Entry(phone_frame, width=40)
        self.phone_entry.pack(fill=tk.X, pady=5)
        # Включаем горячие клавиши для вставки
        self.phone_entry.bind('<Control-v>', lambda e: self._paste_entry(self.phone_entry))
        self.phone_entry.bind('<Control-V>', lambda e: self._paste_entry(self.phone_entry))
        # Контекстное меню
        self._create_entry_context_menu(self.phone_entry)
        ttk.Label(phone_frame, text="Пример: +79991234567", 
                 foreground="gray").pack(anchor=tk.W)
        
        # Код подтверждения
        code_frame = ttk.LabelFrame(main_frame, text="Код подтверждения", padding="10")
        code_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(code_frame, text="Код из Telegram:").pack(anchor=tk.W)
        self.code_entry = ttk.Entry(code_frame, width=40)
        self.code_entry.pack(fill=tk.X, pady=5)
        self.code_entry.config(state=tk.DISABLED)
        # Включаем горячие клавиши для вставки (когда поле будет активно)
        self.code_entry.bind('<Control-v>', lambda e: self._paste_entry(self.code_entry))
        self.code_entry.bind('<Control-V>', lambda e: self._paste_entry(self.code_entry))
        
        # Пароль 2FA
        password_frame = ttk.LabelFrame(main_frame, text="Пароль 2FA (если требуется)", 
                                        padding="10")
        password_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(password_frame, text="Пароль:").pack(anchor=tk.W)
        self.password_entry = ttk.Entry(password_frame, width=40, show="*")
        self.password_entry.pack(fill=tk.X, pady=5)
        self.password_entry.config(state=tk.DISABLED)
        # Включаем горячие клавиши для вставки (когда поле будет активно)
        self.password_entry.bind('<Control-v>', lambda e: self._paste_entry(self.password_entry))
        self.password_entry.bind('<Control-V>', lambda e: self._paste_entry(self.password_entry))
        
        # Кнопки
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X, pady=20)
        
        # Кнопка отправки кода
        self.send_code_button = ttk.Button(buttons_frame, text="1. Отправить код", 
                                          command=self._on_send_code)
        self.send_code_button.pack(fill=tk.X, pady=5, padx=5)
        
        # Кнопка входа (всегда видна, но отключена до отправки кода)
        self.sign_in_button = ttk.Button(buttons_frame, text="2. Войти с кодом", 
                                        command=self._on_sign_in, state=tk.DISABLED)
        self.sign_in_button.pack(fill=tk.X, pady=5, padx=5)
        
        # Кнопка отмены
        cancel_button = ttk.Button(buttons_frame, text="Отмена", 
                  command=self.window.destroy)
        cancel_button.pack(side=tk.BOTTOM, pady=5, padx=5)
        
        # Статус
        self.status_label = ttk.Label(main_frame, text="", foreground="gray")
        self.status_label.pack(pady=10)
    
    def _on_send_code(self):
        """Обработка отправки кода"""
        api_id = self.api_id_entry.get().strip()
        api_hash = self.api_hash_entry.get().strip()
        phone = self.phone_entry.get().strip()
        
        if not api_id or not api_hash:
            messagebox.showerror("Ошибка", "Введите API ID и API Hash")
            return
        
        if not phone:
            messagebox.showerror("Ошибка", "Введите номер телефона")
            return
        
        try:
            api_id_int = int(api_id)
        except ValueError:
            messagebox.showerror("Ошибка", "API ID должен быть числом")
            return
        
        if self.on_auth_requested:
            self.on_auth_requested(api_id_int, api_hash, phone)
    
    def _on_sign_in(self):
        """Обработка входа"""
        code = self.code_entry.get().strip()
        password = self.password_entry.get().strip() or None
        
        if not code:
            messagebox.showerror("Ошибка", "Введите код подтверждения")
            return
        
        if self.on_code_submitted:
            self.on_code_submitted(code, password)
    
    def set_status(self, message: str, error: bool = False):
        """Установить статус"""
        self.status_label.config(text=message, 
                               foreground="red" if error else "green")
    
    def enable_code_input(self):
        """Включить ввод кода"""
        self.code_entry.config(state=tk.NORMAL)
        self.send_code_button.config(state=tk.DISABLED, text="Код отправлен")
        # Активируем кнопку "Войти" (она уже видна)
        self.sign_in_button.config(state=tk.NORMAL)
        # Фокусируемся на поле кода
        self.code_entry.focus()
    
    def enable_password_input(self):
        """Включить ввод пароля 2FA"""
        self.password_entry.config(state=tk.NORMAL)
    
    def get_api_credentials(self) -> tuple:
        """Получить API credentials"""
        api_id = self.api_id_entry.get().strip()
        api_hash = self.api_hash_entry.get().strip()
        try:
            return (int(api_id), api_hash)
        except ValueError:
            return (None, None)
    
    def set_api_credentials(self, api_id: int, api_hash: str):
        """Установить API credentials"""
        self.api_id_entry.delete(0, tk.END)
        self.api_id_entry.insert(0, str(api_id))
        self.api_hash_entry.delete(0, tk.END)
        self.api_hash_entry.insert(0, api_hash)
    
    def _paste_entry(self, widget):
        """Вставка текста в поле ввода"""
        try:
            text = self.window.clipboard_get()
            widget.insert(tk.INSERT, text)
            return "break"  # Предотвращаем стандартную обработку
        except tk.TclError:
            pass
    
    def _create_entry_context_menu(self, widget):
        """Создание контекстного меню для поля ввода"""
        context_menu = tk.Menu(self.window, tearoff=0)
        context_menu.add_command(label="Вставить", command=lambda: self._paste_entry(widget))
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
    
    def close(self):
        """Закрыть окно"""
        self.window.destroy()

