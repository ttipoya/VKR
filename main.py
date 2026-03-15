import io
import json
import os
import sys
import subprocess
import threading
import tempfile
import sqlite3
import customtkinter as ctk
from typing import Any, Optional, List, Tuple
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from test_runner import UniversalTestRunner
import pandas as pd
import gspread
import requests
from customtkinter import CTkFrame, CTkButton
from google.oauth2.service_account import Credentials
from theme_config import COLORS, FONTS, SPACING, STATUS_COLORS, SQLITE_TABLE_CONFIG

# Настройка темы
ctk.set_appearance_mode("white")
ctk.set_default_color_theme("blue")


class TestListWindow(ctk.CTkToplevel):
    def __init__(self, parent, student_data, row):
        super().__init__(parent)

        # ИСПРАВЛЕНО: проверяем длину student_data и правильно присваиваем значения
        self.student_name = student_data[0] if len(student_data) > 0 else "Неизвестно"
        self.student_group = student_data[1] if len(student_data) > 1 else "Неизвестно"
        self.row = row  # Сохраняем исходный номер строки
        self.lab_data = student_data[2]
        self.lab_url = student_data[3]

        # Получаем ID студента из таблицы students
        self.variant = self.get_student_variant_from_db()

        self.code = None
        self.test_runner = None
        self.connection = None

        print(f"DEBUG: student_data = {student_data}")  # Для отладки
        print(f"DEBUG: lab_data type = {type(self.lab_data)}")
        print(f"DEBUG: lab_url = {self.lab_url}")
        print(f"DEBUG: variant = {self.variant}")  # ID из базы данных

        self.setup_ui()

    def setup_ui(self):
        self.title(f"🧪 Тестирование: {self.student_name}")
        self.geometry("1200x800")
        
        # Основной фрейм
        main_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_panel"])
        main_frame.pack(fill="both", expand=True, padx=0, pady=0)

        # === ИНФОРМАЦИОННАЯ ПАНЕЛЬ ===
        info_frame = ctk.CTkFrame(main_frame, fg_color=COLORS["primary"], corner_radius=0)
        info_frame.pack(fill="x", padx=0, pady=0)

        info_label = ctk.CTkLabel(
            info_frame,
            text="� Информация о студенте",
            font=FONTS["header"],
            text_color=COLORS["text_light"]
        )
        info_label.pack(anchor="w", padx=SPACING["padding_large"], pady=(SPACING["padding"], SPACING["padding_small"]))

        # Данные студента
        inner_info = ctk.CTkFrame(info_frame, fg_color=COLORS["primary"])
        inner_info.pack(fill="x", padx=SPACING["padding_large"], pady=(0, SPACING["padding"]))

        student_text = f"👤 {self.student_name} | 👥 {self.student_group} | 🔢 Вариант {self.variant}"
        student_label = ctk.CTkLabel(
            inner_info,
            text=student_text,
            font=FONTS["regular"],
            text_color=COLORS["text_light"]
        )
        student_label.pack(anchor="w")

        # === ОСНОВНОЙ КОНТЕНТ ===
        content_frame = ctk.CTkFrame(main_frame, fg_color=COLORS["bg_panel"])
        content_frame.pack(fill="both", expand=True, padx=SPACING["padding"], pady=SPACING["padding"])

        # === ЛЕВАЯ КОЛОНКА (КОД) ===
        left_column = ctk.CTkFrame(content_frame, fg_color=COLORS["bg_panel"])
        left_column.pack(side="left", fill="both", expand=True, padx=(0, SPACING["padding_small"]))

        code_header = ctk.CTkLabel(
            left_column,
            text="💻 Код программы",
            font=FONTS["subheader"],
            text_color=COLORS["primary"]
        )
        code_header.pack(anchor="w", pady=(0, SPACING["padding_small"]))

        code_frame = ctk.CTkFrame(left_column, fg_color=COLORS["bg_light"], corner_radius=SPACING["border_radius"])
        code_frame.pack(fill="both", expand=True)

        # Текстовое поле для кода
        self.code_text = scrolledtext.ScrolledText(
            code_frame,
            wrap=tk.NONE,
            font=FONTS["monospace"],
            height=20,
            bg=COLORS["bg_panel"],
            fg=COLORS["text_primary"],
            insertbackground=COLORS["primary"]
        )
        self.code_text.pack(fill="both", expand=True, padx=SPACING["padding_small"], pady=SPACING["padding_small"])

        # === ПРАВАЯ КОЛОНКА (РЕЗУЛЬТАТЫ И КНОПКИ) ===
        right_column = ctk.CTkFrame(content_frame, fg_color=COLORS["bg_panel"])
        right_column.pack(side="right", fill="both", expand=True, padx=(SPACING["padding_small"], 0))

        # Результаты
        result_header = ctk.CTkLabel(
            right_column,
            text="🧪 Результаты тестирования",
            font=FONTS["subheader"],
            text_color=COLORS["primary"]
        )
        result_header.pack(anchor="w", pady=(0, SPACING["padding_small"]))

        result_frame = ctk.CTkFrame(right_column, fg_color=COLORS["bg_light"], corner_radius=SPACING["border_radius"])
        result_frame.pack(fill="both", expand=True, pady=(0, SPACING["padding"]))

        # Скроллируемый контейнер для результатов
        result_scroll_frame = ctk.CTkFrame(result_frame, fg_color=COLORS["bg_light"], corner_radius=0)
        result_scroll_frame.pack(fill="both", expand=True)

        # Canvas для прокрутки
        result_canvas = tk.Canvas(result_scroll_frame, bg=COLORS["bg_light"], highlightthickness=0, relief=tk.FLAT)
        scrollbar = ctk.CTkScrollbar(result_scroll_frame, orientation="vertical", command=result_canvas.yview)
        scrollable_frame = ctk.CTkFrame(result_canvas, fg_color=COLORS["bg_light"])

        scrollable_frame.bind(
            "<Configure>",
            lambda e: result_canvas.configure(scrollregion=result_canvas.bbox("all"))
        )

        result_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        result_canvas.configure(yscrollcommand=scrollbar.set)

        def on_wheel(e):
            result_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")

        result_canvas.bind_all("<MouseWheel>", on_wheel)

        result_canvas.pack(side="left", fill="both", expand=True, padx=SPACING["padding_small"], pady=SPACING["padding_small"])
        scrollbar.pack(side="right", fill="y")

        self.result_container = scrollable_frame

        # === ПАНЕЛЬ КНОПОК ===
        button_frame = ctk.CTkFrame(right_column, fg_color=COLORS["bg_panel"])
        button_frame.pack(fill="x", pady=(0, SPACING["padding_small"]))

        self.download_btn = ctk.CTkButton(
            button_frame,
            text="📥 Загрузить",
            command=self.download_code,
            fg_color=COLORS["secondary"],
            hover_color=COLORS["primary_dark"],
            text_color=COLORS["text_light"],
            font=FONTS["regular"],
            corner_radius=SPACING["border_radius"]
        )
        self.download_btn.pack(side="left", padx=SPACING["padding_small"], pady=SPACING["padding_small"])

        self.run_btn = ctk.CTkButton(
            button_frame,
            text="▶ Запустить",
            command=self.run_tests,
            fg_color=COLORS["success"],
            hover_color=COLORS["primary_dark"],
            text_color=COLORS["text_light"],
            font=FONTS["regular"],
            corner_radius=SPACING["border_radius"],
            state="disabled"
        )
        self.run_btn.pack(side="left", padx=SPACING["padding_small"], pady=SPACING["padding_small"])

        self.clear_btn = ctk.CTkButton(
            button_frame,
            text="🗑 Очистить",
            command=self.clear_results,
            fg_color=COLORS["warning"],
            hover_color=COLORS["primary_dark"],
            text_color=COLORS["text_light"],
            font=FONTS["regular"],
            corner_radius=SPACING["border_radius"]
        )
        self.clear_btn.pack(side="left", padx=SPACING["padding_small"], pady=SPACING["padding_small"])

        close_btn = ctk.CTkButton(
            button_frame,
            text="✕ Закрыть",
            command=self.destroy,
            fg_color=COLORS["error"],
            hover_color=COLORS["primary_dark"],
            text_color=COLORS["text_light"],
            font=FONTS["regular"],
            corner_radius=SPACING["border_radius"],
            width=80
        )
        close_btn.pack(side="right", padx=SPACING["padding_small"], pady=SPACING["padding_small"])

        # === СТАТУС БАР ===
        self.status_var = tk.StringVar()
        self.status_var.set("✅ Готов к работе")
        status_bar = ctk.CTkLabel(
            self,
            textvariable=self.status_var,
            font=FONTS["regular"],
            text_color=COLORS["text_light"],
            fg_color=COLORS["primary"],
            padx=SPACING["padding"],
            pady=SPACING["padding_small"]
        )
        status_bar.pack(side="bottom", fill="x")

    def get_student_variant_from_db(self):
        """
        Получает ID студента из таблицы students в SQLite
        Ищет студента по имени и группе
        """
        db_path = "lab_checker.db"
        try:
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # Пытаемся найти студента по имени и группе
                query = """
                    SELECT id FROM students 
                    WHERE full_name = ? AND group_name = ?
                    LIMIT 1
                """
                cursor.execute(query, (self.student_name, self.student_group))
                result = cursor.fetchone()
                
                conn.close()
                
                if result:
                    print(f"DEBUG: Найдено ID студента из БД: {result[0]}")
                    return result[0]
                else:
                    print(f"DEBUG: Студент '{self.student_name}' в группе '{self.student_group}' не найден в БД, используем номер строки: {self.row}")
                    return self.row
            else:
                print(f"DEBUG: Файл БД {db_path} не найден, используем номер строки: {self.row}")
                return self.row
        except Exception as e:
            print(f"DEBUG: Ошибка при получении ID студента: {e}")
            return self.row

    def download_code(self):
        """Загрузка кода с GitHub"""
        self.status_var.set("Загрузка кода с GitHub...")
        self._clear_result_container()
        self._add_result_message("⏳ Загрузка кода с GitHub...", "info")

        # Запускаем в отдельном потоке
        thread = threading.Thread(target=self._download_code_thread)
        thread.daemon = True
        thread.start()

    def _download_code_thread(self):
        """Поток для загрузки кода с поддержкой разных типов GitHub ссылок"""
        try:
            # Получаем URL
            github_url = self._extract_github_url()

            if not github_url:
                self.after(0, self._update_download_result, False, "URL не указан")
                return

            # Преобразуем в raw ссылку, если нужно
            raw_url = self._convert_to_raw_url(github_url)

            if not raw_url:
                self.after(0, self._update_download_result, False, "Не удалось преобразовать ссылку в raw формат")
                return

            print(f"DEBUG: Загрузка с URL: {raw_url}")  # Для отладки

            # Загружаем код
            response = requests.get(raw_url, timeout=10)
            response.raise_for_status()
            self.code = response.text

            self.after(0, self._update_download_result, True, "Код успешно загружен!")

        except requests.RequestException as e:
            self.after(0, self._update_download_result, False, f"Ошибка загрузки: {str(e)}")
        except Exception as e:
            self.after(0, self._update_download_result, False, f"Неизвестная ошибка: {str(e)}")

    def _extract_github_url(self):
        """Извлекает URL из различных источников данных"""
        github_url = None

        # Проверяем lab_url
        if hasattr(self, 'lab_url') and self.lab_url:
            github_url = self.lab_url
        # Проверяем lab_data (словарь)
        elif isinstance(self.lab_data, dict):
            github_url = (self.lab_data.get('github_url') or
                          self.lab_data.get('url') or
                          self.lab_data.get('repo_url'))
        # Проверяем lab_data (строка)
        elif isinstance(self.lab_data, str):
            github_url = self.lab_data
        # Проверяем lab_data (число)
        elif isinstance(self.lab_data, (int, float)):
            github_url = str(self.lab_data)

        return github_url

    def _convert_to_raw_url(self, url):
        """
        Преобразует различные типы GitHub ссылок в raw формат
        Поддерживает:
        - Ссылка на конкретный файл (github.com/user/repo/blob/main/file.py)
        - Ссылка на репозиторий (github.com/user/repo)
        - Ссылка на raw (raw.githubusercontent.com)
        - Ссылка на gist
        """
        if not url:
            return None

        # Если это уже raw ссылка, возвращаем как есть
        if 'raw.githubusercontent.com' in url:
            return url

        # Если это gist
        if 'gist.github.com' in url:
            return self._convert_gist_to_raw(url)

        # Обрабатываем обычные GitHub ссылки
        if 'github.com' in url:
            return self._convert_github_to_raw(url)

        # Если это не GitHub, возвращаем исходный URL (может быть прямая ссылка на файл)
        return url

    def _convert_github_to_raw(self, url):
        """Преобразует github.com ссылку в raw.githubusercontent.com"""
        try:
            # Убираем слеш в конце, если есть
            url = url.rstrip('/')

            # Парсим URL
            # Пример: https://github.com/user/repo/blob/main/file.py
            parts = url.split('github.com/')
            if len(parts) < 2:
                return None

            path = parts[1]

            # Если это ссылка на репозиторий без указания файла
            if path.count('/') == 1:  # user/repo
                # Ищем main.py или другой основной файл
                return self._find_main_file_in_repo(url)

            # Если это ссылка на конкретный файл
            if '/blob/' in path:
                # Заменяем blob на raw
                raw_path = path.replace('/blob/', '/')
                return f"https://raw.githubusercontent.com/{raw_path}"

            # Если это ссылка на ветку/папку
            if '/tree/' in path:
                # Пытаемся найти файл в этой папке
                return self._find_file_in_folder(url)

            return None

        except Exception as e:
            print(f"Ошибка преобразования GitHub URL: {e}")
            return None

    def _find_main_file_in_repo(self, repo_url):
        """
        Пытается найти основной файл в репозитории
        Проверяет: main.py, program.py, lab.py, и т.д.
        """
        try:
            # Получаем содержимое репозитория через GitHub API
            api_url = repo_url.replace('github.com', 'api.github.com/repos')

            # Пробуем разные варианты имени файла
            possible_files = [
                'main.py',
                'program.py',
                'lab.py',
                'solution.py',
                'task.py',
                'index.py',
                'app.py',
                'script.py',
                f'variant_{self.variant}.py',
                f'task_{self.variant}.py'
            ]

            # Пробуем получить список файлов через API
            headers = {'Accept': 'application/vnd.github.v3+json'}
            response = requests.get(api_url + '/contents/', headers=headers, timeout=5)

            if response.status_code == 200:
                contents = response.json()
                # Ищем подходящий файл
                for item in contents:
                    if item['type'] == 'file' and item['name'] in possible_files:
                        # Нашли нужный файл, возвращаем его raw URL
                        return item['download_url']

                # Если не нашли по имени, берем первый .py файл
                for item in contents:
                    if item['type'] == 'file' and item['name'].endswith('.py'):
                        return item['download_url']

            # Если API не сработал, пробуем стандартные пути
            base_raw_url = repo_url.replace('github.com', 'raw.githubusercontent.com')

            # Пробуем разные ветки и пути
            branches = ['main', 'master']
            for branch in branches:
                for file in possible_files:
                    test_url = f"{base_raw_url}/{branch}/{file}"
                    response = requests.head(test_url, timeout=3)
                    if response.status_code == 200:
                        return test_url

            return None

        except Exception as e:
            print(f"Ошибка поиска файла в репозитории: {e}")
            return None

    def _find_file_in_folder(self, folder_url):
        """Пытается найти файл в указанной папке репозитория"""
        try:
            # Преобразуем URL папки в API запрос
            api_url = folder_url.replace('github.com', 'api.github.com/repos')
            api_url = api_url.replace('/tree/', '/contents/')

            response = requests.get(api_url, headers={'Accept': 'application/vnd.github.v3+json'}, timeout=5)

            if response.status_code == 200:
                contents = response.json()
                # Ищем .py файлы
                py_files = [item for item in contents if item['type'] == 'file' and item['name'].endswith('.py')]

                if py_files:
                    # Берем первый .py файл
                    return py_files[0]['download_url']

            return None

        except Exception as e:
            print(f"Ошибка поиска файла в папке: {e}")
            return None

    def _convert_gist_to_raw(self, gist_url):
        """Преобразует gist.github.com ссылку в raw"""
        try:
            # Пример: https://gist.github.com/user/123456789
            parts = gist_url.split('gist.github.com/')
            if len(parts) < 2:
                return None

            gist_path = parts[1]
            gist_id = gist_path.split('/')[-1]

            # Получаем информацию о gist через API
            api_url = f"https://api.github.com/gists/{gist_id}"
            response = requests.get(api_url, timeout=5)

            if response.status_code == 200:
                gist_data = response.json()
                files = gist_data.get('files', {})

                # Ищем .py файлы
                for file_name, file_info in files.items():
                    if file_name.endswith('.py'):
                        return file_info.get('raw_url')

                # Если нет .py, берем первый файл
                if files:
                    first_file = list(files.values())[0]
                    return first_file.get('raw_url')

            return None

        except Exception as e:
            print(f"Ошибка преобразования gist: {e}")
            return None

    def _update_download_result(self, success, message):
        """Обновление интерфейса после загрузки"""
        if success:
            self.code_text.delete(1.0, tk.END)
            if self.code:
                self.code_text.insert(tk.END, self.code)
            self._add_result_message(f"✅ {message}", "success")
            self.run_btn.configure(state="normal")
            self.status_var.set("Код загружен")
        else:
            self._add_result_message(f"❌ {message}", "error")
            self.status_var.set("Ошибка загрузки")

    def run_tests(self):
        """Запуск тестирования"""
        # Проверяем наличие кода
        if not self.code and not self.code_text.get(1.0, tk.END).strip():
            messagebox.showwarning("Предупреждение", "Сначала загрузите код!")
            return

        # Используем код из поля ввода, если он изменен
        current_code = self.code_text.get(1.0, tk.END).strip()
        if current_code != self.code:
            self.code = current_code

        self.status_var.set("Запуск тестов...")
        self._clear_result_container()
        self._add_result_message("⏳ Запуск тестов...", "info")

        # Блокируем кнопки
        self.run_btn.configure(state="disabled")
        self.download_btn.configure(state="disabled")

        # Запускаем в отдельном потоке
        thread = threading.Thread(target=self._run_tests_thread)
        thread.daemon = True
        thread.start()

    def _clear_result_container(self):
        """Очистка контейнера результатов"""
        for widget in self.result_container.winfo_children():
            widget.destroy()

    def _add_result_message(self, message, msg_type="info"):
        """Добавление сообщения в контейнер результатов"""
        msg_frame = ctk.CTkFrame(self.result_container, fg_color=COLORS["bg_panel"], corner_radius=SPACING["border_radius"])
        msg_frame.pack(fill="x", padx=SPACING["padding_small"], pady=SPACING["padding_small"])

        color = COLORS["info"] if msg_type == "info" else (COLORS["success"] if msg_type == "success" else COLORS["error"])
        msg_label = ctk.CTkLabel(
            msg_frame,
            text=message,
            font=FONTS["regular"],
            text_color=color,
            wraplength=350,
            justify="center"
        )
        msg_label.pack(padx=SPACING["padding"], pady=SPACING["padding"])

    def _run_tests_thread(self):
        """Поток для выполнения тестов"""
        try:
            # Получаем путь к конфигу из БД по номеру лабораторной
            config_path = self.load_config_path()

            print(f"DEBUG: Загружен конфиг: {config_path}")

            # Загружаем и проверяем конфиг
            config = self.load_and_validate_config(config_path)

            if not config:
                self.after(0, self._show_test_error, f"Не удалось загрузить конфиг {config_path}")
                return

            # Получаем lab_id из конфига
            lab_number = config.get('lab_number')
            lab_id = self.get_lab_id_from_db(lab_number) if lab_number else None

            # Создаем тест-раннер с информацией о студенте и лабе
            self.test_runner = UniversalTestRunner(
                config_path, 
                self.variant,
                student_id=self.variant,  # ID студента совпадает с вариантом
                lab_id=lab_id
            )
            
            # Проверяем, что код загружен
            if self.code is None or not self.code.strip():
                self.after(0, self._show_test_error, "Код не загружен. Сначала загрузите код с GitHub!")
                return
                
            self.test_runner.set_code(self.code)

            # Запускаем тесты
            results = self.test_runner.run_all_tests()

            # ДОБАВЛЕНО: Выводим отладочную информацию о результатах
            print(f"DEBUG: Результаты тестов ({len(results)} шт.):")
            for i, result in enumerate(results):
                print(f"  Тест {i + 1}: {result.get('name')}")
                print(f"    Входные данные: {repr(result.get('input'))}")
                print(f"    Ожидалось: {repr(result.get('expected'))}")
                print(f"    Получено: {repr(result.get('actual'))}")
                print(f"    Результат: {'✅' if result.get('passed') else '❌'}")

            # Получаем детальный отчет
            summary = self.test_runner.get_detailed_report()

            self.after(0, self._update_test_result, results, summary)

        except Exception as e:
            print(f"DEBUG: Ошибка в _run_tests_thread: {e}")
            import traceback
            traceback.print_exc()
            self.after(0, self._show_test_error, str(e))

    def load_config_path(self):
        """Загрузка пути к конфигу из базы данных по номеру лабораторной работы"""
        try:
            config_path = 'config.json'  # Значение по умолчанию

            # Получаем номер лабораторной работы
            lab_number = None

            # Пробуем получить номер лабораторной из разных источников
            if isinstance(self.lab_data, dict):
                lab_number = self.lab_data.get('lab_number') or self.lab_data.get('lab')
            elif isinstance(self.lab_data, (int, str)):
                lab_number = int(self.lab_data) if str(self.lab_data).isdigit() else None

            # Если не нашли в lab_data, пробуем из названия
            if not lab_number and hasattr(self, 'student_name'):
                print(f"DEBUG: Номер лабораторной не найден в данных")

            print(f"DEBUG: Номер лабораторной: {lab_number}, Вариант: {self.variant}")

            # Подключаемся к базе данных
            db_path = "lab_checker.db"
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()

                # Получаем список таблиц
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = [table[0] for table in cursor.fetchall()]
                print(f"DEBUG: Таблицы в БД: {tables}")

                if 'labs' in tables:
                    # Получаем структуру таблицы labs
                    cursor.execute("PRAGMA table_info(labs)")
                    columns = cursor.fetchall()
                    print(f"DEBUG: Колонки таблицы labs: {columns}")

                    # Ищем колонки
                    id_col = None
                    lab_num_col = None
                    config_col = None

                    for col in columns:
                        col_name = col[1].lower()
                        if 'lab' in col_name and ('num' in col_name or 'number' in col_name or 'id' in col_name):
                            lab_num_col = col[0]  # индекс колонки с номером лабораторной
                        elif 'config' in col_name or 'path' in col_name:
                            config_col = col[0]  # индекс колонки с путём к конфигу
                        elif 'id' in col_name and lab_num_col is None:
                            id_col = col[0]  # индекс ID колонки

                    # Если нашли колонку с номером лабораторной
                    if lab_num_col is not None and config_col is not None:
                        # Ищем по номеру лабораторной
                        query = f"SELECT * FROM labs WHERE {columns[lab_num_col][1]} = ?"
                        cursor.execute(query, (lab_number,))
                        row = cursor.fetchone()

                        if row and len(row) > config_col:
                            config_path = row[config_col]
                            print(f"DEBUG: Найден конфиг по номеру лабораторной {lab_number}: {config_path}")
                        else:
                            print(f"DEBUG: Лабораторная работа №{lab_number} не найдена в БД")

                            # Показываем все доступные лабораторные
                            cursor.execute(f"SELECT {columns[lab_num_col][1]}, {columns[config_col][1]} FROM labs")
                            all_labs = cursor.fetchall()
                            print(f"DEBUG: Доступные лабораторные в БД: {all_labs}")

                    # Если не нашли по номеру, пробуем по ID
                    elif id_col is not None and config_col is not None:
                        cursor.execute(f"SELECT * FROM labs WHERE {columns[id_col][1]} = ?", (lab_number,))
                        row = cursor.fetchone()
                        if row and len(row) > config_col:
                            config_path = row[config_col]
                            print(f"DEBUG: Найден конфиг по ID {lab_number}: {config_path}")

                    # Если ничего не нашли, берём первую запись
                    elif config_col is not None:
                        cursor.execute(f"SELECT * FROM labs LIMIT 1")
                        row = cursor.fetchone()
                        if row and len(row) > config_col:
                            config_path = row[config_col]
                            print(f"DEBUG: Использую первый конфиг из БД: {config_path}")

                conn.close()
            else:
                print(f"DEBUG: Файл БД {db_path} не найден")

            # Проверяем существование файла конфига
            if not os.path.exists(config_path):
                print(f"DEBUG: Конфиг {config_path} не найден, ищу альтернативы")

                # Формируем имя конфига на основе лабораторной и варианта
                if lab_number:
                    alternative_paths = [
                        f"lab{lab_number}_config_{self.variant}.json",
                        f"lab_{lab_number}.json",
                        f"variant_{self.variant}.json",
                        f"lab{lab_number}.json",
                        "config.json"
                    ]
                else:
                    alternative_paths = [
                        f"variant_{self.variant}.json",
                        f"lab_config.json",
                        "config.json"
                    ]

                for alt_path in alternative_paths:
                    if os.path.exists(alt_path):
                        config_path = alt_path
                        print(f"DEBUG: Использую альтернативный конфиг: {config_path}")
                        break

            print(f"DEBUG: Итоговый путь к конфигу: {config_path}")
            return config_path

        except Exception as e:
            print(f"Ошибка при загрузке пути к конфигу: {e}")
            import traceback
            traceback.print_exc()
            return 'config.json'

    def load_and_validate_config(self, config_path):
        """Загружает конфиг и проверяет наличие данных для варианта"""
        try:
            import json

            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # Проверяем, есть ли данные для нашего варианта
            variant_found = False
            if 'variant_data' in config:
                for variant_item in config['variant_data']:
                    if variant_item.get('variant') == self.variant:
                        variant_found = True
                        print(f"DEBUG: Найдены данные для варианта {self.variant}")
                        break

            if not variant_found:
                print(f"ПРЕДУПРЕЖДЕНИЕ: Вариант {self.variant} не найден в конфиге {config_path}")
                # Показываем доступные варианты
                available_variants = [item.get('variant') for item in config.get('variant_data', [])]
                print(f"DEBUG: Доступные варианты в конфиге: {available_variants}")

            return config

        except Exception as e:
            print(f"Ошибка загрузки конфига {config_path}: {e}")
            return None

    def get_lab_id_from_db(self, lab_number: int):
        """
        Получает ID лабораторной работы из базы данных по номеру лабы
        """
        db_path = "lab_checker.db"
        try:
            if not os.path.exists(db_path):
                print(f"DEBUG: БД {db_path} не найдена, lab_id не установлен")
                return None

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT id FROM labs WHERE lab_number = ?", (lab_number,))
            result = cursor.fetchone()

            conn.close()

            if result:
                print(f"DEBUG: Найден lab_id={result[0]} для lab_number={lab_number}")
                return result[0]
            else:
                print(f"DEBUG: Лаба с номером {lab_number} не найдена в БД")
                return None

        except Exception as e:
            print(f"DEBUG: Ошибка при получении lab_id: {e}")
            return None

    def _update_test_result(self, result, summary):
        """Обновление интерфейса с результатами тестов"""
        # Очищаем старые результаты
        for widget in self.result_container.winfo_children():
            widget.destroy()

        stats = self.test_runner.get_statistics() if self.test_runner else {}
        total = stats.get('total_tests', 0)
        passed = stats.get('passed_tests', 0)
        failed = total - passed if total > 0 else 0

        # === КАРТОЧКА СТАТИСТИКИ ===
        stats_frame = ctk.CTkFrame(self.result_container, fg_color=COLORS["primary"], corner_radius=SPACING["border_radius"])
        stats_frame.pack(fill="x", padx=SPACING["padding_small"], pady=SPACING["padding_small"])

        stats_title = ctk.CTkLabel(
            stats_frame,
            text="📊 СТАТИСТИКА",
            font=FONTS["subheader"],
            text_color=COLORS["text_light"]
        )
        stats_title.pack(anchor="w", padx=SPACING["padding"], pady=(SPACING["padding"], SPACING["padding_small"]))

        # Строки статистики
        stats_text = f"✅ Пройдено: {passed}/{total} тестов  •  📈 Прогресс: {(passed/total*100 if total else 0):.1f}%"
        stats_label = ctk.CTkLabel(
            stats_frame,
            text=stats_text,
            font=FONTS["regular"],
            text_color=COLORS["text_light"]
        )
        stats_label.pack(anchor="w", padx=SPACING["padding"], pady=(0, SPACING["padding_small"]))

        if failed > 0:
            error_text = f"❌ Не пройдено: {failed} тестов"
            error_label = ctk.CTkLabel(
                stats_frame,
                text=error_text,
                font=FONTS["regular"],
                text_color="#ffcdd2"
            )
            error_label.pack(anchor="w", padx=SPACING["padding"], pady=(0, SPACING["padding"]))
        else:
            stats_frame.pack_configure(pady=(SPACING["padding_small"], SPACING["padding"]))

        # === КАРТОЧКИ ТЕСТОВ ===
        for i, test_result in enumerate(result, 1):
            is_passed = test_result.get('passed', False)
            bg_color = COLORS["bg_panel"] if is_passed else "#ffebee"
            border_color = STATUS_COLORS["passed"]["fg"] if is_passed else STATUS_COLORS["failed"]["fg"]

            test_frame = ctk.CTkFrame(self.result_container, fg_color=bg_color, corner_radius=SPACING["border_radius"])
            test_frame.pack(fill="x", padx=SPACING["padding_small"], pady=SPACING["padding_small"])

            # Заголовок теста
            test_name = test_result.get('name', f'Тест {i}')
            status_icon = "✅" if is_passed else "❌"
            status_text = "ПРОЙДЕН" if is_passed else "НЕ ПРОЙДЕН"

            header_frame = ctk.CTkFrame(test_frame, fg_color=bg_color)
            header_frame.pack(fill="x", padx=SPACING["padding"], pady=(SPACING["padding"], SPACING["padding_small"]))

            test_label = ctk.CTkLabel(
                header_frame,
                text=f"{status_icon} Test #{i}: {test_name}",
                font=FONTS["title"],
                text_color=border_color
            )
            test_label.pack(anchor="w", side="left")

            status_label = ctk.CTkLabel(
                header_frame,
                text=status_text,
                font=FONTS["small"],
                text_color=border_color
            )
            status_label.pack(anchor="e", side="right")

            # Разделитель
            sep = ctk.CTkFrame(test_frame, fg_color=border_color, height=1)
            sep.pack(fill="x", padx=SPACING["padding"])

            # Данные теста
            data_frame = ctk.CTkFrame(test_frame, fg_color=bg_color)
            data_frame.pack(fill="x", padx=SPACING["padding"], pady=SPACING["padding"])

            # Input
            input_label = ctk.CTkLabel(
                data_frame,
                text=f"📥 Input: {repr(test_result.get('input', 'N/A'))}",
                font=FONTS["monospace_small"],
                text_color=COLORS["text_primary"],
                wraplength=350,
                justify="left"
            )
            input_label.pack(anchor="w", pady=SPACING["padding_small"])

            # Expected
            expected_label = ctk.CTkLabel(
                data_frame,
                text=f"✓ Expected: {repr(test_result.get('expected', 'N/A'))}",
                font=FONTS["monospace_small"],
                text_color=COLORS["text_primary"],
                wraplength=350,
                justify="left"
            )
            expected_label.pack(anchor="w", pady=SPACING["padding_small"])

            # Actual
            actual_label = ctk.CTkLabel(
                data_frame,
                text=f"📤 Actual: {repr(test_result.get('actual', 'N/A'))}",
                font=FONTS["monospace_small"],
                text_color=border_color,
                wraplength=350,
                justify="left"
            )
            actual_label.pack(anchor="w", pady=SPACING["padding_small"])

            # Error (если есть)
            error_msg = test_result.get('error', '')
            if error_msg:
                error_label = ctk.CTkLabel(
                    data_frame,
                    text=f"⚠️ Error: {error_msg}",
                    font=FONTS["small"],
                    text_color=STATUS_COLORS["failed"]["fg"],
                    wraplength=350,
                    justify="left"
                )
                error_label.pack(anchor="w", pady=SPACING["padding_small"])

        # === ФИНАЛЬНАЯ КАРТОЧКА ===
        if total > 0:
            final_frame = ctk.CTkFrame(self.result_container, fg_color=COLORS["success"] if passed == total else COLORS["error"], corner_radius=SPACING["border_radius"])
            final_frame.pack(fill="x", padx=SPACING["padding_small"], pady=SPACING["padding"])

            if passed == total:
                final_label = ctk.CTkLabel(
                    final_frame,
                    text="🎉 ВСЕ ТЕСТЫ УСПЕШНО ПРОЙДЕНЫ!",
                    font=FONTS["header"],
                    text_color=COLORS["text_light"]
                )
            else:
                final_label = ctk.CTkLabel(
                    final_frame,
                    text=f"⚠️ ОБНАРУЖЕНО {failed} ОШИБОК(И)",
                    font=FONTS["header"],
                    text_color=COLORS["text_light"]
                )
            final_label.pack(padx=SPACING["padding"], pady=SPACING["padding"])

        # Обновляем статус
        if stats.get('passed_tests', 0) == stats.get('total_tests', 0):
            self.status_var.set("✅ Все тесты пройдены")
        else:
            self.status_var.set("❌ Есть ошибки в тестах")

        # Разблокируем кнопки
        self.run_btn.configure(state="normal")
        self.download_btn.configure(state="normal")

    def _show_test_error(self, error_msg):
        """Показ ошибки тестирования"""
        self._clear_result_container()
        self._add_result_message(f"❌ Ошибка: {error_msg}", "error")
        self.status_var.set("Ошибка выполнения тестов")

        # Разблокируем кнопки
        self.run_btn.configure(state="normal")
        self.download_btn.configure(state="normal")

    def clear_results(self):
        """Очистка результатов"""
        self._clear_result_container()
        self.status_var.set("Результаты очищены")


class StudentDetailWindow(ctk.CTkToplevel):
    """Окно с информацией о студенте и его сданных лабораторных работах"""

    def __init__(self, parent, student_name: str, student_group: str, db_path: str = "lab_checker.db"):
        super().__init__(parent)
        
        self.title(f"📋 Информация о студенте: {student_name}")
        self.geometry("600x500")
        
        self.student_name = student_name
        self.student_group = student_group
        self.db_path = db_path
        
        # Основной фрейм
        main_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_panel"])
        main_frame.pack(fill="both", expand=True, padx=0, pady=0)
        
        # Информационная панель
        info_frame = ctk.CTkFrame(main_frame, fg_color=COLORS["primary"], corner_radius=0)
        info_frame.pack(fill="x", padx=0, pady=0)
        
        info_label = ctk.CTkLabel(
            info_frame,
            text=f"👤 {student_name} | 👥 {student_group}",
            font=FONTS["header"],
            text_color=COLORS["text_light"]
        )
        info_label.pack(anchor="w", padx=SPACING["padding_large"], pady=SPACING["padding"])
        
        # Контейнер для таблицы лаб
        content_frame = ctk.CTkFrame(main_frame, fg_color=COLORS["bg_panel"])
        content_frame.pack(fill="both", expand=True, padx=SPACING["padding"], pady=SPACING["padding"])
        
        title_label = ctk.CTkLabel(
            content_frame,
            text="Сданные лабораторные работы:",
            font=FONTS["subheader"],
            text_color=COLORS["primary"]
        )
        title_label.pack(anchor="w", pady=(0, SPACING["padding"]))
        
        # Таблица с лабами
        table_frame = ctk.CTkFrame(content_frame, fg_color=COLORS["bg_light"], corner_radius=SPACING["border_radius"])
        table_frame.pack(fill="both", expand=True)
        
        # Canvas с скроллбаром
        canvas = tk.Canvas(table_frame, bg=COLORS["bg_light"], highlightthickness=0)
        scrollbar = ctk.CTkScrollbar(table_frame, orientation="vertical", command=canvas.yview)
        scrollable_frame = ctk.CTkFrame(canvas, fg_color=COLORS["bg_light"])
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Заполняем таблицу данными из БД
        self._populate_labs_table(scrollable_frame)
        
        canvas.pack(side="left", fill="both", expand=True, padx=SPACING["padding_small"], pady=SPACING["padding_small"])
        scrollbar.pack(side="right", fill="y", padx=(0, SPACING["padding_small"]), pady=SPACING["padding_small"])

    def _populate_labs_table(self, container):
        """Заполняет таблицу информацией о сданных лабах студента"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Получаем ID студента
            cursor.execute("SELECT id FROM students WHERE full_name = ? AND group_name = ?", 
                          (self.student_name, self.student_group))
            student_result = cursor.fetchone()
            
            if not student_result:
                label = ctk.CTkLabel(container, text="Студент не найден в БД", text_color=COLORS["error"])
                label.pack(padx=SPACING["padding"], pady=SPACING["padding"])
                conn.close()
                return
            
            student_id = student_result[0]
            
            # Получаем все лабораторные работы
            cursor.execute("SELECT id, lab_number, title FROM labs ORDER BY lab_number")
            labs = cursor.fetchall()
            
            # Получаем статусы сданных работ для этого студента
            cursor.execute("""
                SELECT lab_id, overall_status FROM test_runs 
                WHERE student_id = ?
                ORDER BY run_timestamp DESC
            """, (student_id,))
            
            test_runs = cursor.fetchall()
            
            # Создаем словарь со статусами (берем последний статус для каждой лабы)
            lab_status = {}
            for lab_id, status in test_runs:
                if lab_id not in lab_status:
                    lab_status[lab_id] = status
            
            conn.close()
            
            # Выводим таблицу
            for lab_id, lab_num, title in labs:
                row_frame = ctk.CTkFrame(container, fg_color=COLORS["bg_secondary"], corner_radius=SPACING["border_radius"])
                row_frame.pack(fill="x", padx=SPACING["padding_small"], pady=SPACING["padding_small"])
                
                # Номер лабы
                lab_label = ctk.CTkLabel(
                    row_frame,
                    text=f"Лаб. №{lab_num}: {title}",
                    font=FONTS["regular"],
                    text_color=COLORS["text_primary"]
                )
                lab_label.pack(side="left", padx=SPACING["padding"], pady=SPACING["padding_small"])
                
                # Статус
                status = lab_status.get(lab_id, "not_submitted")
                status_text = "✅ Сдана" if status == "passed" else "⚠️ Частично" if status == "partial" else "❌ Не сдана"
                status_color = COLORS["success"] if status == "passed" else COLORS["warning"] if status == "partial" else COLORS["error"]
                
                status_label = ctk.CTkLabel(
                    row_frame,
                    text=status_text,
                    font=FONTS["regular"],
                    text_color=status_color
                )
                status_label.pack(side="right", padx=SPACING["padding"], pady=SPACING["padding_small"])
        
        except Exception as e:
            print(f"Ошибка при загрузке информации о лабах: {e}")
            error_label = ctk.CTkLabel(container, text=f"Ошибка: {str(e)}", text_color=COLORS["error"])
            error_label.pack(padx=SPACING["padding"], pady=SPACING["padding"])


class GroupDetailWindow(ctk.CTkToplevel):
    """Окно со всеми студентами группы и таблицей лабораторных работ"""

    def __init__(self, parent, group_name: str, db_path: str = "lab_checker.db"):
        super().__init__(parent)
        
        self.title(f"👥 Группа: {group_name}")
        self.geometry("1000x600")
        
        self.group_name = group_name
        self.db_path = db_path
        
        # Основной фрейм
        main_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_panel"])
        main_frame.pack(fill="both", expand=True, padx=0, pady=0)
        
        # Информационная панель
        info_frame = ctk.CTkFrame(main_frame, fg_color=COLORS["primary"], corner_radius=0)
        info_frame.pack(fill="x", padx=0, pady=0)
        
        info_label = ctk.CTkLabel(
            info_frame,
            text=f"👥 Группа: {group_name}",
            font=FONTS["header"],
            text_color=COLORS["text_light"]
        )
        info_label.pack(anchor="w", padx=SPACING["padding_large"], pady=SPACING["padding"])
        
        # Контейнер для таблицы
        content_frame = ctk.CTkFrame(main_frame, fg_color=COLORS["bg_panel"])
        content_frame.pack(fill="both", expand=True, padx=SPACING["padding"], pady=SPACING["padding"])
        
        # Canvas с скроллбаром
        canvas = tk.Canvas(content_frame, bg=COLORS["bg_panel"], highlightthickness=0)
        v_scrollbar = ctk.CTkScrollbar(content_frame, orientation="vertical", command=canvas.yview)
        h_scrollbar = ctk.CTkScrollbar(content_frame, orientation="horizontal", command=canvas.xview)
        scrollable_frame = ctk.CTkFrame(canvas, fg_color=COLORS["bg_panel"])
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Заполняем таблицу
        self._populate_group_table(scrollable_frame)
        
        canvas.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        content_frame.grid_rowconfigure(0, weight=1)
        content_frame.grid_columnconfigure(0, weight=1)

    def _populate_group_table(self, container):
        """Заполняет таблицу студентов группы и их лаб"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Получаем всех студентов группы
            cursor.execute("SELECT id, full_name FROM students WHERE group_name = ? ORDER BY full_name", 
                          (self.group_name,))
            students = cursor.fetchall()
            
            # Получаем все лабораторные работы
            cursor.execute("SELECT id, lab_number, title FROM labs ORDER BY lab_number")
            labs = cursor.fetchall()
            
            conn.close()
            
            # Заголовок таблицы - ФИ студента
            header_frame = ctk.CTkFrame(container, fg_color=COLORS["primary"], corner_radius=0)
            header_frame.pack(fill="x", padx=0, pady=0)
            
            name_label = ctk.CTkLabel(
                header_frame,
                text="ФИ Студента",
                font=FONTS["title"],
                text_color=COLORS["text_light"],
                width=250
            )
            name_label.pack(side="left", padx=SPACING["padding"], pady=SPACING["padding_small"])
            
            # Заголовки лаб
            for lab_id, lab_num, title in labs:
                lab_label = ctk.CTkLabel(
                    header_frame,
                    text=f"Л{lab_num}",
                    font=FONTS["title"],
                    text_color=COLORS["text_light"],
                    width=50
                )
                lab_label.pack(side="left", padx=SPACING["padding_small"], pady=SPACING["padding_small"])
            
            # Строки студентов
            for student_id, student_name in students:
                row_frame = ctk.CTkFrame(container, fg_color=COLORS["bg_secondary"], corner_radius=SPACING["border_radius"])
                row_frame.pack(fill="x", padx=SPACING["padding_small"], pady=SPACING["padding_small"])
                
                # ФИ студента
                name_label = ctk.CTkLabel(
                    row_frame,
                    text=student_name,
                    font=FONTS["regular"],
                    text_color=COLORS["text_primary"],
                    width=250
                )
                name_label.pack(side="left", padx=SPACING["padding"], pady=SPACING["padding_small"])
                
                # Статусы лаб
                for lab_id, _, _ in labs:
                    status = self._get_lab_status(student_id, lab_id)
                    status_text = "✅" if status == "passed" else "⚠️" if status == "partial" else "❌"
                    status_color = COLORS["success"] if status == "passed" else COLORS["warning"] if status == "partial" else COLORS["error"]
                    
                    status_label = ctk.CTkLabel(
                        row_frame,
                        text=status_text,
                        font=FONTS["regular"],
                        text_color=status_color,
                        width=50
                    )
                    status_label.pack(side="left", padx=SPACING["padding_small"], pady=SPACING["padding_small"])
        
        except Exception as e:
            print(f"Ошибка при загрузке информации о группе: {e}")
            error_label = ctk.CTkLabel(container, text=f"Ошибка: {str(e)}", text_color=COLORS["error"])
            error_label.pack(padx=SPACING["padding"], pady=SPACING["padding"])

    def _get_lab_status(self, student_id: int, lab_id: int):
        """Получает статус сдачи лабы студентом"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT overall_status FROM test_runs 
                WHERE student_id = ? AND lab_id = ?
                ORDER BY run_timestamp DESC
                LIMIT 1
            """, (student_id, lab_id))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return result[0]
            return "not_submitted"
        
        except Exception as e:
            print(f"Ошибка при получении статуса лабы: {e}")
            return "not_submitted"


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
                cell_text = str(self.data[row][col])
                cell = ctk.CTkLabel(
                    self.table_frame,
                    text=cell_text,
                    corner_radius=5
                )
                cell.grid(row=row, column=col, sticky="nsew", padx=1, pady=1)

                # Делаем ячейки кликабельными для первой и второй колонок
                if col == 0:  # Первая колонка - студент
                    cell.bind("<Button-1>", lambda e, r=row, c=col: self.on_cell_click(r, c, "student"))
                    cell.configure(cursor="hand2", fg_color=COLORS["info"])
                elif col == 1:  # Вторая колонка - группа
                    cell.bind("<Button-1>", lambda e, r=row, c=col: self.on_cell_click(r, c, "group"))
                    cell.configure(cursor="hand2", fg_color=COLORS["info"])

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
        # Исправлено: передаем правильные параметры
        test_window = TestListWindow(self, self.data[row], row)
        test_window.focus()

    def on_cell_click(self, row, col, cell_type):
        """
        Обработчик клика на ячейку таблицы

        Args:
            row: номер строки (с учетом заголовка)
            col: номер колонки
            cell_type: тип ячейки ("student" или "group")
        """
        if row < 1 or row >= len(self.data):
            return

        row_data = self.data[row]

        if cell_type == "student" and len(row_data) > 1:
            # Получаем имя студента и группу
            student_name = str(row_data[0])
            student_group = str(row_data[1]) if len(row_data) > 1 else "Неизвестно"

            # Открываем окно с информацией о студенте
            detail_window = StudentDetailWindow(self, student_name, student_group)
            detail_window.focus()

        elif cell_type == "group" and len(row_data) > 1:
            # Получаем группу
            group_name = str(row_data[1])

            # Открываем окно с информацией о группе
            group_window = GroupDetailWindow(self, group_name)
            group_window.focus()


class SQLite_data(ctk.CTkFrame):
    def __init__(self, master: Any, db_path: str = "lab_checker.db", **kwargs):
        super().__init__(master, **kwargs)

        self.db_path = db_path

        # Заголовок
        self.label = ctk.CTkLabel(self, text="🗄️ Данные из базы SQLite", font=FONTS["header"], text_color=COLORS["text_primary"])
        self.label.pack(pady=10)

        # Создаем вкладки
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(expand=True, fill="both", padx=10, pady=10)

        # Добавляем вкладки
        tables = ["students", "labs", "test_runs", "test_results"]

        for table in tables:
            self.tabview.add(table)
            self._setup_table_view(table)

        # Загружаем данные
        self.load_data()

    def _setup_table_view(self, table_name: str):
        """Подготавливаем контейнер для таблицы"""
        tab = self.tabview.tab(table_name)
        
        # Контейнер с прокруткой
        scroll_frame = ctk.CTkFrame(tab)
        scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Canvas
        canvas = tk.Canvas(scroll_frame, bg=COLORS["bg_panel"], highlightthickness=0, relief=tk.FLAT)
        
        # Скроллбар
        scrollbar = ctk.CTkScrollbar(scroll_frame, orientation="vertical", command=canvas.yview)
        
        # Контент фрейм
        content_frame = tk.Frame(canvas, bg=COLORS["bg_panel"])
        content_window = canvas.create_window((0, 0), window=content_frame, anchor="nw")
        
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # На изменение размера
        def on_configure():
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig(content_window, width=canvas.winfo_width())
        
        content_frame.bind("<Configure>", lambda e: on_configure())
        
        # Прокрутка колесом
        def on_wheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
        canvas.bind_all("<MouseWheel>", on_wheel)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Сохраняем ссылки
        setattr(self, f"content_frame_{table_name}", content_frame)
        setattr(self, f"canvas_{table_name}", canvas)

    def load_data(self):
        """Загружает данные из базы"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            tables = ["students", "labs", "test_runs", "test_results"]

            for table in tables:
                content_frame = getattr(self, f"content_frame_{table}", None)
                if content_frame is None:
                    continue

                # Очищаем предыдущие виджеты
                for widget in content_frame.winfo_children():
                    widget.destroy()

                try:
                    cursor.execute(f"SELECT * FROM {table}")
                    rows = cursor.fetchall()

                    # Получаем названия колонок
                    cursor.execute(f"PRAGMA table_info({table})")
                    columns = cursor.fetchall()
                    column_names = [col[1] for col in columns]

                    if not rows:
                        empty_label = tk.Label(
                            content_frame,
                            text="📭 Нет данных в таблице",
                            font=FONTS["regular"],
                            fg=COLORS["text_secondary"],
                            bg=COLORS["bg_panel"]
                        )
                        empty_label.pack(padx=10, pady=20)
                        continue

                    # Заголовок таблицы
                    header_frame = tk.Frame(content_frame, bg=COLORS["primary"], height=35)
                    header_frame.pack(fill="x", padx=2, pady=2)
                    header_frame.pack_propagate(False)

                    for col_name in column_names:
                        col_label = tk.Label(
                            header_frame,
                            text=col_name,
                            font=FONTS["title"],
                            fg=COLORS["text_light"],
                            bg=COLORS["primary"],
                            padx=5
                        )
                        col_label.pack(side="left", fill="both", expand=True, padx=1)

                    # Данные таблицы
                    for row_idx, row in enumerate(rows):
                        bg_color = SQLITE_TABLE_CONFIG["row_color_1"] if row_idx % 2 == 0 else SQLITE_TABLE_CONFIG["row_color_2"]
                        
                        row_frame = tk.Frame(content_frame, bg=bg_color, height=30)
                        row_frame.pack(fill="x", padx=2, pady=1)
                        row_frame.pack_propagate(False)

                        for cell_value in row:
                            display_value = str(cell_value) if cell_value is not None else "NULL"
                            cell_fg = COLORS["text_primary"] if cell_value is not None else COLORS["text_secondary"]
                            
                            cell_label = tk.Label(
                                row_frame,
                                text=display_value[:30],
                                font=FONTS["monospace_small"],
                                fg=cell_fg,
                                bg=bg_color,
                                padx=5
                            )
                            cell_label.pack(side="left", fill="both", expand=True, padx=1)

                    # Статистика
                    stats_label = tk.Label(
                        content_frame,
                        text=f"📊 {len(rows)} записей | {len(column_names)} колонок",
                        font=FONTS["small"],
                        fg=COLORS["text_secondary"],
                        bg=COLORS["bg_light"],
                        pady=5
                    )
                    stats_label.pack(fill="x", padx=2, pady=(5, 2))

                except sqlite3.OperationalError:
                    error_label = tk.Label(
                        content_frame,
                        text=f"❌ Таблица '{table}' не найдена",
                        font=FONTS["regular"],
                        fg=COLORS["error"],
                        bg=COLORS["bg_panel"]
                    )
                    error_label.pack(padx=10, pady=20)

            conn.close()

        except Exception as e:
            print(f"Ошибка загрузки SQLite: {e}")


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
        self.control_frame.pack(fill="x", padx=10, pady=(10, 0))

        self.radio_frame_table = ctk.CTkFrame(self.control_frame, height=50)
        self.radio_frame_table.pack(fill="x", padx=10, pady=10)

        self.selected_option_table = ctk.StringVar(value="google")

        self.refresh_btn = ctk.CTkButton(
            self.control_frame,
            text="Обновить данные",
            command=self.load_data
        )
        self.refresh_btn.pack(side="left", padx=5)

        self.google_btn = ctk.CTkRadioButton(
            self.radio_frame_table,
            text="Таблица Google Sheets",
            variable=self.selected_option_table,
            value="google",
            command=self.switch_frame_table
        )
        self.google_btn.pack(side="left", padx=20)

        self.sqlite_btn = ctk.CTkRadioButton(
            self.radio_frame_table,
            text="База данных SQLite",
            variable=self.selected_option_table,
            value="sqlite",
            command=self.switch_frame_table
        )
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
            print(f"DEBUG: Начало загрузки данных. Тип подключения: {self.connection_data.get('type')}")
            
            if self.connection_data["type"] == "public":
                print(f"DEBUG: Загрузка публичной таблицы. URL: {self.connection_data['url'][:50]}...")
                data = self.get_public_sheet_csv(self.connection_data['url'])
            else:
                print(f"DEBUG: Загрузка приватной таблицы. URL: {self.connection_data['url'][:50]}...")
                data = self.get_private_sheet_data(
                    self.connection_data['url'],
                    self.connection_data["config_file"]
                )

            # Обновление UI ТОЛЬКО через after()
            self.after(0, self._update_ui_with_data, data)

        except KeyError as e:
            error_msg = f"Ошибка конфигурации: отсутствует ключ {str(e)}"
            print(f"KeyError: {error_msg}")
            self.after(0, lambda: self.status_label.configure(text=error_msg))
        except FileNotFoundError as e:
            error_msg = f"Файл не найден: {str(e)}"
            print(f"FileNotFoundError: {error_msg}")
            self.after(0, lambda: self.status_label.configure(text=error_msg))
        except Exception as e:
            error_msg = f"Ошибка загрузки: {type(e).__name__} - {str(e)}"
            print(f"Exception: {error_msg}")
            import traceback
            traceback.print_exc()
            self.after(0, lambda: self.status_label.configure(text=error_msg))

    def _update_ui_with_data(self, data):
        if data:
            self.google_table_frame.update_data(data)
            self.status_label.configure(text=f"Загружено {len(data)} строк")
        else:
            self.status_label.configure(text="Ошибка загрузки данных")

    def fix_encoding(self, text):
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

    def get_public_sheet_csv(self, connection_data, sheet_gid=0):
        try:
            # Исправлено: извлечение ID из URL
            if '/d/' in connection_data:
                # Берем все что между /d/ и следующим /
                parts = connection_data.split('/d/')
                if len(parts) > 1:
                    # Берем часть после /d/ и до следующего / или конца строки
                    id_part = parts[1].split('/')[0]
                    # Также отсекаем возможные параметры после ?
                    id_part = id_part.split('?')[0]
            else:
                # Если это просто ID
                id_part = connection_data

            if not id_part:
                raise ValueError("Не удалось извлечь ID таблицы из URL")
            
            print(f"DEBUG: Извлеченный ID таблицы: {id_part}")

            # URL для экспорта в CSV
            url = f"https://docs.google.com/spreadsheets/d/{id_part}/export?format=csv&gid={sheet_gid}"
            print(f"DEBUG: URL запроса: {url}")

            # Получаем CSV с таймаутом
            print("DEBUG: Отправка запроса на Google Sheets...")
            response = requests.get(url, timeout=15)
            print(f"DEBUG: Статус ответа: {response.status_code}")
            response.raise_for_status()

            # Проверяем, что ответ не пуст
            if not response.text:
                raise ValueError("Таблица пуста или недоступна")

            # Читаем CSV в DataFrame
            print("DEBUG: Парсинг CSV...")
            df = pd.read_csv(io.StringIO(response.text))
            print(f"DEBUG: Загружено {len(df)} строк, {len(df.columns)} колонок")

            # Применяем исправление кодировки для строковых колонок
            for col in df.select_dtypes(include=['object']).columns:
                df[col] = df[col].apply(self.fix_encoding)

            # Преобразуем в список с заголовками
            headers = df.columns.tolist()
            data_rows = df.values.tolist()
            result = [headers] + data_rows
            print(f"DEBUG: Данные успешно обработаны")
            return result

        except requests.exceptions.Timeout:
            error_msg = "Истекло время ожидания при подключении к Google Sheets (таймаут)"
            print(f"Timeout: {error_msg}")
            raise Exception(error_msg)
        except requests.exceptions.ConnectionError:
            error_msg = "Ошибка подключения: проверьте интернет-соединение"
            print(f"ConnectionError: {error_msg}")
            raise Exception(error_msg)
        except requests.exceptions.HTTPError as e:
            error_msg = f"Ошибка HTTP {e.response.status_code}: таблица не найдена или не доступна"
            print(f"HTTPError: {error_msg}")
            raise Exception(error_msg)
        except pd.errors.EmptyDataError:
            error_msg = "Таблица пуста (нет данных для загрузки)"
            print(f"EmptyDataError: {error_msg}")
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"Ошибка при получении данных: {type(e).__name__} - {str(e)}"
            print(f"Exception: {error_msg}")
            import traceback
            traceback.print_exc()
            raise Exception(error_msg)

    def get_private_sheet_data(self, connection_data, credentials_file, range_name="A1:Z1000"):
        try:
            print(f"DEBUG: Загрузка приватной таблицы с файлом конфигурации: {credentials_file}")
            
            if not os.path.exists(credentials_file):
                raise FileNotFoundError(f"Файл конфигурации не найден: {credentials_file}")
            
            print("DEBUG: Файл конфигурации найден, авторизация...")
            scope = ["https://spreadsheets.google.com/feeds",
                     "https://www.googleapis.com/auth/drive"]
            creds = Credentials.from_service_account_file(
                credentials_file,
                scopes=scope
            )
            print("DEBUG: Авторизация успешна")
            
            client = gspread.authorize(creds)
            print(f"DEBUG: Подключение к таблице: {connection_data[:50]}...")
            sheet = client.open_by_url(connection_data)
            print(f"DEBUG: Таблица открыта: {sheet.title}")

            worksheet = sheet.get_worksheet(0)
            print("DEBUG: Получение данных...")
            data = worksheet.get_all_values()
            print(f"DEBUG: Загружено {len(data)} строк")
            return data

        except FileNotFoundError as e:
            error_msg = f"Файл не найден: {str(e)}"
            print(f"FileNotFoundError: {error_msg}")
            raise Exception(error_msg)
        except gspread.exceptions.SpreadsheetNotFound:
            error_msg = "Таблица не найдена (возможно, доступ ограничен)"
            print(f"SpreadsheetNotFound: {error_msg}")
            raise Exception(error_msg)
        except gspread.exceptions.APIError as e:
            error_msg = f"Ошибка API Google: {str(e)}"
            print(f"APIError: {error_msg}")
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"Ошибка при получении данных: {type(e).__name__} - {str(e)}"
            print(f"Exception: {error_msg}")
            import traceback
            traceback.print_exc()
            raise Exception(error_msg)


# Добавлена точка входа
if __name__ == "__main__":
    # Пример connection_data
    connection_data = {
        "type": "public",  # или "private"
        "url": "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit",
        "config_file": "credentials.json"  # для private режима
    }

    app = GoogleSheetsViewer(connection_data)
    app.mainloop()