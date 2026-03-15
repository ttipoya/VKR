import customtkinter as ctk
from tkinter import messagebox, filedialog
import os
import json
import threading
from main import GoogleSheetsViewer# Прямой импорт main.py

# Настройка темы
ctk.set_appearance_mode("white")
ctk.set_default_color_theme("blue")


class Selector(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Выбор доступа к таблице")
        self.geometry("600x650")  # Увеличил высоту для кнопки авто-подключения

        # Блокировка для предотвращения множественных подключений
        self.connecting = False

        # Создаем основные виджеты
        self.create_widgets()

        # Переменные для хранения данных подключения
        self.selected_file = None

    def create_widgets(self):
        """Создание всех виджетов"""

        # Заголовок
        label = ctk.CTkLabel(self, text="Выбор доступа к таблице", font=("Helvetica", 20))
        label.pack(pady=20)

        # Фрейм для радио-кнопок
        radio_frame = ctk.CTkFrame(self)
        radio_frame.pack(pady=10, padx=20, fill="x")

        self.selected_option = ctk.StringVar(value="not")

        # Радио-кнопки
        ctk.CTkRadioButton(
            radio_frame,
            text="Публичная таблица",
            variable=self.selected_option,
            value="public",
            command=self.switch_frame
        ).pack(padx=20, pady=10)

        ctk.CTkRadioButton(
            radio_frame,
            text="Закрытая таблица",
            variable=self.selected_option,
            value="private",
            command=self.switch_frame
        ).pack(padx=20, pady=10)

        # Фрейм для контента (будет меняться)
        self.content_frame = ctk.CTkFrame(self)
        self.content_frame.pack(pady=20, padx=20, fill="both", expand=True)

        # Создаем фреймы для разных режимов
        self.create_public_frame()
        self.create_private_frame()
        self.create_not_frame()

        # Показываем начальный фрейм
        self.switch_frame()

        # Фрейм для кнопок
        button_frame = ctk.CTkFrame(self)
        button_frame.pack(pady=10)

        # Кнопка подключения
        self.button_connect = ctk.CTkButton(
            button_frame,
            text="Подключиться",
            command=self.connections,
            width=200,
            height=40
        )
        self.button_connect.pack(pady=5)

        # Кнопка авто-подключения
        self.button_auto = ctk.CTkButton(
            button_frame,
            text="Авто-подключение (тестовые данные)",
            command=self.auto_connect,
            width=200,
            height=40,
            fg_color="green",
            hover_color="darkgreen"
        )
        self.button_auto.pack(pady=5)

        # Индикатор загрузки (изначально скрыт)
        self.progressbar = ctk.CTkProgressBar(self, mode='indeterminate')

    def create_public_frame(self):

        self.public_frame = ctk.CTkFrame(self.content_frame)

        ctk.CTkLabel(
            self.public_frame,
            text="Введите ссылку для публичной таблицы",
            font=("Arial", 16, "bold")
        ).pack(pady=10)

        self.entry_public = ctk.CTkEntry(
            self.public_frame,
            placeholder_text="Введите ссылку на таблицу"
        )
        self.entry_public.pack(pady=10, padx=20, fill="x")

        # Валидация URL
        self.entry_public.bind('<KeyRelease>', self.validate_public_url)
        self.public_url_valid = False

    def create_private_frame(self):
        """Создание фрейма для приватной таблицы"""
        self.private_frame = ctk.CTkFrame(self.content_frame)

        ctk.CTkLabel(
            self.private_frame,
            text="Выберите JSON файл конфигурации и введите ссылку",
            font=("Arial", 16, "bold")
        ).pack(pady=10)

        # Кнопка выбора файла
        ctk.CTkButton(
            self.private_frame,
            text="Выбрать JSON файл",
            command=self.select_json_file,
            width=200,
            height=40
        ).pack(pady=20)

        # Метка для отображения выбранного файла
        self.label_file = ctk.CTkLabel(
            self.private_frame,
            text="Файл не выбран",
            wraplength=400
        )
        self.label_file.pack(pady=20)

        # Поле для ввода URL
        self.entry_private = ctk.CTkEntry(
            self.private_frame,
            placeholder_text="Введите ссылку на таблицу"
        )
        self.entry_private.pack(pady=10, padx=20, fill="x")

        # Валидация URL
        self.entry_private.bind('<KeyRelease>', self.validate_private_url)
        self.private_url_valid = False

    def create_not_frame(self):
        """Создание фрейма для невыбранного режима"""
        self.not_frame = ctk.CTkFrame(self.content_frame)
        ctk.CTkLabel(
            self.not_frame,
            text="Выберите способ подключения",
            font=("Arial", 20, "bold")
        ).pack(expand=True)

    def switch_frame(self):
        """Переключение между фреймами"""
        selected = self.selected_option.get()

        # Скрываем все фреймы
        for frame in [self.public_frame, self.private_frame, self.not_frame]:
            frame.pack_forget()

        # Показываем нужный фрейм
        if selected == "public":
            self.public_frame.pack(fill="both", expand=True)
        elif selected == "private":
            self.private_frame.pack(fill="both", expand=True)
        else:
            self.not_frame.pack(fill="both", expand=True)

    def select_json_file(self):
        """Выбор JSON файла"""
        filename = filedialog.askopenfilename(
            title="Выберите файл конфигурации Google Sheets",
            filetypes=[("JSON файлы", "*.json"), ("Все файлы", "*.*")]
        )

        if filename:
            # Проверяем JSON файл
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    json.load(f)

                self.label_file.configure(
                    text=f"✓ Файл: {os.path.basename(filename)}",
                    text_color="green"
                )
                self.selected_file = filename

            except Exception as e:
                self.label_file.configure(
                    text=f"✗ Ошибка в файле: {str(e)[:50]}",
                    text_color="red"
                )
                self.selected_file = None

    def validate_public_url(self, event=None):
        """Валидация URL для публичной таблицы"""
        url = self.entry_public.get().strip()
        if url.startswith(('https://docs.google.com/spreadsheets/', 'http://docs.google.com/spreadsheets/')):
            self.public_url_valid = True
            self.entry_public.configure(border_color="green")
        else:
            self.public_url_valid = False
            self.entry_public.configure(border_color="red" if url else "gray")

    def validate_private_url(self, event=None):
        """Валидация URL для приватной таблицы"""
        url = self.entry_private.get().strip()
        if url.startswith(('https://docs.google.com/spreadsheets/', 'http://docs.google.com/spreadsheets/')):
            self.private_url_valid = True
            self.entry_private.configure(border_color="green")
        else:
            self.private_url_valid = False
            self.entry_private.configure(border_color="red" if url else "gray")

    def auto_connect(self):
        """Автоматическое подключение с тестовыми данными"""
        if self.connecting:
            return

        # Проверяем существование файла
        test_file = "test-487108-30e6e9a93d0c.json"
        if not os.path.exists(test_file):
            messagebox.showerror("Ошибка",
                                 f"Файл {test_file} не найден в текущей директории!\n\n"
                                 "Убедитесь, что файл находится в той же папке, что и программа.")
            return

        # Устанавливаем режим "private" и заполняем данные
        self.selected_option.set("private")
        self.switch_frame()

        # Заполняем URL
        test_url = "https://docs.google.com/spreadsheets/d/1VSrb2VxUOlRdpbMzDWNJqdGomyPvT0_MbSQmBh7kMco/edit?gid=0#gid=0"
        self.entry_private.delete(0, "end")
        self.entry_private.insert(0, test_url)
        self.validate_private_url()

        # Устанавливаем файл
        self.selected_file = test_file
        self.label_file.configure(
            text=f"✓ Файл: {test_file}",
            text_color="green"
        )

        # Автоматически запускаем подключение
        self.connections()

    def connections(self):
        """Подключение к таблице"""
        if self.connecting:
            return

        self.connecting = True
        self.button_connect.configure(state="disabled", text="Подключение...")
        self.button_auto.configure(state="disabled")

        # Показываем прогрессбар
        self.progressbar.pack(pady=5)
        self.progressbar.start()

        # Выполняем подключение
        self._do_connection()

    def _do_connection(self):
        """Выполнение подключения"""
        try:
            selected = self.selected_option.get()

            if selected == "public":
                if not self.public_url_valid:
                    self._show_error("Введите корректную ссылку на публичную таблицу")
                    return

                table_url = self.entry_public.get().strip()

                # Создаем данные подключения
                connection_data = {
                    'type': 'public',
                    'url': table_url,
                    'config_file': None
                }

                # Запускаем главное окно
                self._launch_main(connection_data)

            elif selected == "private":
                if not self.private_url_valid:
                    self._show_error("Введите корректную ссылку на таблицу")
                    return

                if not self.selected_file:
                    self._show_error("Выберите JSON файл конфигурации")
                    return

                table_url = self.entry_private.get().strip()

                # Создаем данные подключения
                connection_data = {
                    'type': 'private',
                    'url': table_url,
                    'config_file': self.selected_file
                }

                # Запускаем главное окно
                self._launch_main(connection_data)

            else:
                self._show_error("Выберите способ подключения")
                return

        except Exception as e:
            self._show_error(f"Ошибка: {str(e)}")

    def _show_error(self, message):
        """Показать ошибку"""
        messagebox.showwarning("Предупреждение", message)
        self._reset_ui()

    def _launch_main(self, connection_data):
        """Запуск главного окна (прямой импорт)"""
        try:
            # Останавливаем прогрессбар
            self.progressbar.stop()
            self.progressbar.pack_forget()

            # Создаем экземпляр главного окна
            main_app = GoogleSheetsViewer(connection_data)

            # Закрываем текущее окно
            self.withdraw()  # Скрываем, но не уничтожаем

            # Запускаем главное окно
            main_app.mainloop()

            # После закрытия главного окна показываем selector снова
            self.deiconify()

            # Сбрасываем состояние UI
            self._reset_ui()

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть главное окно: {str(e)}")
            self._reset_ui()

    def _reset_ui(self):
        """Сброс UI после завершения/ошибки"""
        self.connecting = False
        self.button_connect.configure(state="normal", text="Подключиться")
        self.button_auto.configure(state="normal")
        self.progressbar.stop()
        self.progressbar.pack_forget()


if __name__ == "__main__":
    app = Selector()
    app.mainloop()