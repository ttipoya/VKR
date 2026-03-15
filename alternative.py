import io
import sys
from turtle import pd

import subprocess
import threading
import tempfile

import sqlite3

import customtkinter as ctk
from typing import Any, Optional, List, Tuple
from CTkTable import *

import pandas as pd
import gspread
import requests
from customtkinter import CTkFrame, CTkButton

from google.oauth2.service_account import Credentials

# Настройка темы
ctk.set_appearance_mode("white")
ctk.set_default_color_theme("blue")

class TestListWindow(ctk.CTkToplevel):
    def __init__(self, parent, student_data):
        super().__init__(parent)

        self.title("Запуск тестов")
        self.geometry("700x500")

        self.student_data = student_data
        self.github_url = student_data[3]  # ссылка из таблицы

        title = ctk.CTkLabel(
            self,
            text=f"Тестирование: {student_data[0]}",
            font=("Arial", 16, "bold")
        )
        title.pack(pady=10)

        self.run_button = ctk.CTkButton(
            self,
            text="Запустить тесты",
            command=self.start_tests
        )
        self.run_button.pack(pady=5)

        self.output_box = ctk.CTkTextbox(self)
        self.output_box.pack(fill="both", expand=True, padx=10, pady=10)

    def start_tests(self):
        self.run_button.configure(state="disabled")
        self.output_box.delete("1.0", "end")
        self.output_box.insert("end", "Запуск тестов...\n")

        thread = threading.Thread(target=self.run_pytest)
        thread.daemon = True
        thread.start()

    def run_pytest(self):
        try:
            # Запуск pytest с передачей URL
            result = subprocess.run(
                [
                    sys.executable,  # запускаем тем же python
                    "-m",
                    "pytest",
                    "test_list.py",
                    "-v",
                    "-s",
                    "--github-url",
                    self.github_url  # БЕЗ =
                ],
                capture_output=True,
                text=True
            )

            output = result.stdout + "\n" + result.stderr

            self.after(0, self.show_result, output)

        except Exception as e:
            self.after(0, self.show_result, f"Ошибка запуска: {e}")

    def show_result(self, output):
        self.output_box.insert("end", output)
        self.run_button.configure(state="normal")

class Table(ctk.CTkFrame):
    """Фрейм, содержащий таблицу и элементы управления"""

    def __init__(self, master: Any, data=None, **kwargs):
        super().__init__(master, **kwargs)

        self.action_buttons = {}
        self.data = data or []

        # Заголовок (опционально)
        self.label = ctk.CTkLabel(self, text="Данные таблицы", font=('Arial', 16, 'bold'))
        self.label.pack(pady=(10, 5))

        # Фрейм для таблицы с прокруткой
        self.table_container = ctk.CTkFrame(self)
        self.table_container.pack(expand=True, fill="both", padx=10, pady=10)
        # Создаем таблицу
        self.create_table()

    def create_table(self):
        if hasattr(self, "table_frame"):
            self.table_frame.destroy()

        self.table_frame = ctk.CTkFrame(self.table_container)
        self.table_frame.pack(expand=True, fill="both")

        if not self.data:
            return

        rows = len(self.data)
        cols = len(self.data[0])

        # Заголовки
        for col in range(cols):
            header = ctk.CTkLabel(
                self.table_frame,
                text=self.data[0][col],
                fg_color="#CD5C5C",
                text_color="white",
                corner_radius=5
            )
            header.grid(row=0, column=col, sticky="nsew", padx=1, pady=1)

        action_header = ctk.CTkLabel(
            self.table_frame,
            text="Действие",
            fg_color="#CD5C5C",
            text_color="white",
            corner_radius=5
        )
        action_header.grid(row=0, column=cols, sticky="nsew", padx=1, pady=1)

        # Данные + кнопки
        for row in range(1, rows):
            for col in range(cols):
                cell = ctk.CTkLabel(
                    self.table_frame,
                    text=self.data[row][col],
                    corner_radius=5
                )
                cell.grid(row=row, column=col, sticky="nsew", padx=1, pady=1)

            btn = ctk.CTkButton(
                self.table_frame,
                text="Тест",
                width=80,
                command=lambda r=row: self.on_test_click(r)
            )
            btn.grid(row=row, column=cols, padx=1, pady=1)

        # Авто-растяжение колонок
        for col in range(cols + 1):
            self.table_frame.grid_columnconfigure(col, weight=1)
    def update_data(self, new_data):

        self.data = new_data
        self.create_table()

    def on_test_click(self, row):
        student_data = self.data[row]
        TestListWindow(self, student_data)

class SQLite_data(ctk.CTkFrame):
    def __init__(self, master: Any, db_path: str = "lab_checker.db", **kwargs):
        super().__init__(master, **kwargs)

        self.db_path = db_path

        # Заголовок
        self.label = ctk.CTkLabel(self, text="Данные из базы SQLite", font=("Arial", 16))
        self.label.pack(pady=10)

        # Создаем вкладки
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(expand=True, fill="both", padx=10, pady=10)

        # Добавляем вкладки
        tables = ["students", "labs", "test_runs", "test_results"]

        for table in tables:
            self.tabview.add(table)
            listbox = ctk.CTkTextbox(self.tabview.tab(table))
            listbox.pack(expand=True, fill="both", padx=5, pady=5)
            setattr(self, f"list_{table}", listbox)

        # Загружаем данные
        self.load_data()

    def load_data(self):
        """Загружает данные из базы"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        tables = ["students", "labs", "test_runs", "test_results"]

        for table in tables:
            cursor.execute(f"SELECT * FROM {table}")
            rows = cursor.fetchall()

            listbox = getattr(self, f"list_{table}")
            listbox.delete("1.0", "end")

            for row in rows:
                listbox.insert("end", f"{row}\n")

        conn.close()

class GoogleSheetsViewer(ctk.CTk):
    def __init__(self, connection_data):
        super().__init__()

        self.title("Google Sheets Viewer")
        self.geometry("800x600")

        self.connection_data = connection_data

        # Создаем интерфейс
        self.create_widgets()

        # Загружаем данные
        self.load_data()

    def create_widgets(self):
        """Создает элементы интерфейса"""
        # Верхняя панель с кнопками
        self.control_frame = ctk.CTkFrame(self, height=50)
        self.control_frame.pack(fill="y", padx=10, pady=(10, 0))

        self.radio_frame_table = ctk.CTkFrame(self.control_frame, height=50)
        self.radio_frame_table.pack(fill="y", padx=10, pady=10)

        self.selected_option_table = ctk.StringVar(value="google")

        self.refresh_btn = ctk.CTkButton(
            self.control_frame,
            text="Обновить данные",
            command=self.load_data
        )
        self.refresh_btn.pack(side="left", padx=5)

        self.google_btn = ctk.CTkRadioButton(self.radio_frame_table,text = "Таблица Google Sheets",
                                             variable=self.selected_option_table, value= "google", command=self.switch_frame_table)
        self.google_btn.pack(side="left", padx=20)

        self.sqlite_btn = ctk.CTkRadioButton(self.radio_frame_table, text="База данных SQLite",
                                             variable=self.selected_option_table, value="sqlite", command=self.switch_frame_table)
        self.sqlite_btn.pack(side="right", padx=20)

        self.status_label = ctk.CTkLabel(
            self.control_frame,
            text="Готов к работе"
        )
        self.status_label.pack(side="right", padx=5)

        self.create_table_google()
        self.create_table_sqlite()

        self.switch_frame_table()

    def create_table_google(self):
        self.google_table_frame = Table(self)

    def create_table_sqlite(self):
        self.sqlite_table_frame = SQLite_data(self)

    def switch_frame_table(self):

        selected_table = self.selected_option_table.get()

        # Скрываем все фреймы
        for frame in [self.google_table_frame, self.sqlite_table_frame]:
            frame.pack_forget()

        # Показываем нужный фрейм
        if selected_table == "google":
            self.google_table_frame.pack(fill="both", expand=True)
        elif selected_table == "sqlite":
            self.sqlite_table_frame.pack(fill="both", expand=True)

    def load_data(self):
        self.status_label.configure(text="Загрузка данных...")
        thread = threading.Thread(target=self._load_data_thread)
        thread.daemon = True
        thread.start()

    def _load_data_thread(self):
        try:
            if self.connection_data["type"] == "public":
                data = self.get_public_sheet_csv(self.connection_data['url'])
            else:
                data = self.get_private_sheet_data(
                    self.connection_data['url'],
                    self.connection_data["config_file"]
                )

            # Обновление UI ТОЛЬКО через after()
            self.after(0, self._update_ui_with_data, data)

        except Exception as e:
            self.after(0, self.status_label.configure, {"text": f"Ошибка: {str(e)}"})

    def _update_ui_with_data(self, data):
        if data:
            self.google_table_frame.update_data(data)
            self.status_label.configure(text=f"Загружено {len(data)} строк")
        else:
            self.status_label.configure(text="Ошибка загрузки данных")

    def fix_encoding(self,text):

        if isinstance(text, str):
            try:

                return text.encode('cp1251').decode('utf-8')
            except:
                try:
                    # Альтернативный вариант
                    return text.encode('latin-1').decode('utf-8')
                except:
                    return text
        return text

    def get_public_sheet_csv(self,connection_data, sheet_gid=0):

        if '/d/' in connection_data:
            # Берем все что между /d/ и следующим /
            parts = connection_data.split('/d/')
            if len(parts) > 1:
                # Берем часть после /d/ и до следующего / или конца строки
                id_part = parts[1].split('/')[0]
                # Также отсекаем возможные параметры после ?
                id_part = id_part.split('?')[0]
        try:
            # URL для экспорта в CSV
            url =  url = f"https://docs.google.com/spreadsheets/d/{id_part}/export?format=csv&gid={sheet_gid}"

            # Получаем CSV
            response = requests.get(url)
            response.raise_for_status()

            # Читаем CSV в DataFrame

            df = pd.read_csv(io.StringIO(response.text))

            for col in df.select_dtypes(include=[]).columns:
                df[col] = df[col].apply(self.fix_encoding)

            array_with_headers = df.values.tolist()
            return array_with_headers

        except Exception as e:
            print(f"Ошибка при получении данных: {e}")
            return None


    def get_private_sheet_data(self,connection_data, credentials_file, range_name="A1:Z1000"):

        try:
            scope = ["https://spreadsheets.google.com/feeds",
                     "https://www.googleapis.com/auth/drive"]
            creds = Credentials.from_service_account_file(
                credentials_file,
                scopes=scope
            )
            self.client = gspread.authorize(creds)
            self.sheet = self.client.open_by_url(connection_data)

            worksheet = self.sheet.get_worksheet(0)
            data = worksheet.get_all_values()
            return data

        except Exception as e:
            print(f"Ошибка при получении данных: {e}")
            return None

