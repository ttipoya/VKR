import io
import sys
import json
import sqlite3
import requests
from unittest.mock import patch, mock_open
from typing import Dict, Any, List, Optional
from datetime import datetime


class UniversalTestRunner:
    """Универсальный класс для тестирования студенческих работ"""

    def __init__(self, config_path: str, variant: int, student_id: Optional[int] = None,
                 lab_id: Optional[int] = None, db_path: str = "lab_checker.db"):
        """
        Инициализация тестировщика

        Args:
            config_path: путь к файлу конфигурации
            variant: номер варианта (1-30)
            student_id: ID студента для сохранения результатов (опционально)
            lab_id: ID лабораторной работы (опционально)
            db_path: путь к базе данных SQLite
        """
        self.config = self.load_config(config_path)
        self.variant = variant
        self.student_id = student_id
        self.lab_id = lab_id
        self.db_path = db_path
        self.variant_tests = self.get_variant_tests(variant)
        self.code = None
        self.results = []
        self.test_run_id = None

    def load_config(self, config_path: str) -> Dict[str, Any]:
        """Загрузка конфигурации из JSON файла"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            raise Exception(f"Файл конфигурации не найден: {config_path}")
        except json.JSONDecodeError:
            raise Exception(f"Ошибка в формате JSON файла: {config_path}")

    def get_variant_tests(self, variant: int) -> List[Dict[str, Any]]:
        """Получение всех тестов для конкретного варианта"""
        if 'variant_data' not in self.config:
            raise Exception("В конфигурации отсутствует поле 'variant_data'")

        for variant_item in self.config['variant_data']:
            if variant_item.get('variant') == variant:
                return variant_item.get('tests', [])

        raise Exception(f"Вариант {variant} не найден в конфигурации")

    def download_code(self, github_url: str = None) -> str:
        """Скачивание кода из GitHub"""
        url = github_url or self.config.get('github_url')
        if not url:
            raise Exception("URL не указан")

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            raise Exception(f"Ошибка скачивания кода: {e}")

    def set_code(self, code: str):
        """Установка кода для тестирования"""
        self.code = code

    def get_code_requirements(self) -> Dict[str, Any]:
        """
        Получение требований к коду из конфигурации.

        Returns:
            Словарь с требованиями:
            - forbidden_imports: список запрещенных импортов
            - required_structures: список требуемых структур (dict, list и т.д.)
            - custom_checks: список пользовательских проверок
        """
        # Дефолтные требования для лабораторной 1
        default_requirements = {
            'forbidden_imports': ['re'],
            'required_structures': ['dict'],
            'custom_checks': []
        }

        # Если в конфиге нет раздела requirements, используем дефолтные
        if 'requirements' not in self.config:
            return default_requirements

        requirements = self.config.get('requirements', {})

        # Мержим с дефолтными значениями (чтобы не потеря неуказанные поля)
        merged = default_requirements.copy()
        merged.update(requirements)

        return merged

    def validate_code_structure(self, code: str) -> List[str]:
        """
        Проверка структуры кода на основе требований из конфигурации.

        Проверяемые требования:
        - forbidden_imports: список запрещенных импортов
        - required_structures: список требуемых структур (dict, list и т.д.)

        Returns:
            Список нарушений (пустой список, если нарушений нет)
        """
        violations = []
        requirements = self.get_code_requirements()

        # Проверка запрещенных импортов
        forbidden_imports = requirements.get('forbidden_imports', [])
        if forbidden_imports:
            for forbidden_module in forbidden_imports:
                import_lines = []
                for line in code.split('\n'):
                    # Проверяем различные форматы импорта (import re, from re import, import re as alias)
                    if f'import {forbidden_module}' in line or f'from {forbidden_module} import' in line:
                        import_lines.append(line.strip())

                if import_lines:
                    violations.append(
                        f"Запрещено использовать библиотеку '{forbidden_module}'. Найдены импорты: {', '.join(import_lines)}")

        # Проверка требуемых структур
        required_structures = requirements.get('required_structures', [])
        if required_structures:
            for structure in required_structures:
                if structure == 'dict':
                    has_structure = self._check_for_dict(code)
                    if not has_structure:
                        violations.append(
                            "Не найдено использование словаря (dict). В задании требуется обязательное использование словарей.")

                elif structure == 'list':
                    has_structure = self._check_for_list(code)
                    if not has_structure:
                        violations.append(
                            "Не найдено использование списка (list). В задании требуется обязательное использование списков.")

        return violations

    def _check_for_dict(self, code: str) -> bool:
        """Проверка наличия словаря в коде"""
        import re as regex_check

        # Проверяем различные способы создания словарей
        dict_patterns = [
            r'{.*:.*}',  # {key: value}
            r'\bdict\s*\(',  # dict()
            r'\b{}\b',  # пустой словарь {}
        ]

        for pattern in dict_patterns:
            if regex_check.search(pattern, code):
                return True

        # Дополнительная проверка на наличие фигурных скобок вне строк
        lines = code.split('\n')
        in_string = False
        string_char = None

        for line in lines:
            i = 0
            while i < len(line):
                char = line[i]

                # Отслеживаем строки
                if char in '"\'' and (i == 0 or line[i - 1] != '\\'):
                    if not in_string:
                        in_string = True
                        string_char = char
                    elif char == string_char:
                        in_string = False

                # Ищем фигурные скобки вне строк
                if not in_string and char == '{':
                    next_char = line[i + 1] if i + 1 < len(line) else ''
                    if next_char != '}':
                        # Ищем двоеточие до закрывающей скобки
                        j = i + 1
                        bracket_count = 1
                        while j < len(line):
                            if line[j] == '{':
                                bracket_count += 1
                            elif line[j] == '}':
                                bracket_count -= 1
                                if bracket_count == 0:
                                    break
                            elif line[j] == ':' and bracket_count == 1:
                                return True
                            j += 1
                    else:
                        return True  # Пустой словарь {}

                i += 1

        return False

    def _check_for_list(self, code: str) -> bool:
        """Проверка наличия списка в коде"""
        import re as regex_check

        # Проверяем различные способы создания списков
        list_patterns = [
            r'\[.*\]',  # [item1, item2]
            r'\blist\s*\(',  # list()
        ]

        for pattern in list_patterns:
            if regex_check.search(pattern, code):
                return True

        # Дополнительная проверка на наличие квадратных скобок вне строк
        lines = code.split('\n')
        in_string = False
        string_char = None

        for line in lines:
            i = 0
            while i < len(line):
                char = line[i]

                # Отслеживаем строки
                if char in '"\'' and (i == 0 or line[i - 1] != '\\'):
                    if not in_string:
                        in_string = True
                        string_char = char
                    elif char == string_char:
                        in_string = False

                # Ищем квадратные скобки вне строк
                if not in_string and char == '[':
                    next_char = line[i + 1] if i + 1 < len(line) else ''
                    if next_char != ']':
                        return True  # Непустой список
                    else:
                        return True  # Пустой список []

                i += 1

        return False

    def execute_code(self, code: str, input_data: str) -> str:
        """Выполнение кода с заданным входным параметром"""
        mock_file = mock_open(read_data=input_data)

        with patch('builtins.open', mock_file):
            fake_stdout = io.StringIO()
            with patch('sys.stdout', fake_stdout):
                try:
                    # Создаем безопасное пространство имен
                    namespace = {}
                    exec(code, namespace)
                    return fake_stdout.getvalue()
                except Exception as e:
                    return f"ОШИБКА ВЫПОЛНЕНИЯ: {str(e)}"

    def run_single_test(self, test: Dict[str, Any], code: str = None) -> Dict[str, Any]:
        """
        Запуск одного теста

        Returns:
            Словарь с результатами теста
        """
        if code:
            self.code = code

        if not self.code:
            raise Exception("Код не загружен")

        input_data = test.get('input', '')
        expected = test.get('expected', '')
        test_name = test.get('name', 'Безымянный тест')
        points = test.get('points', 0)

        # Запуск кода
        output = self.execute_code(self.code, input_data)
        output_clean = output.strip()

        # Проверка результата
        passed = expected in output_clean

        return {
            'name': test_name,
            'input': input_data,
            'expected': expected,
            'actual': output_clean,
            'passed': passed,
            'points': points if passed else 0,
            'max_points': points
        }

    def run_all_tests(self, code: str = None) -> List[Dict[str, Any]]:
        """Запуск всех тестов для данного варианта"""
        if code:
            self.code = code
        elif not self.code:
            self.code = self.download_code()

        self.results = []

        # Проверка структуры кода перед выполнением тестов
        violations = self.validate_code_structure(self.code)

        # Если есть нарушения, создаем специальные результаты тестов
        if violations:
            violation_message = "\n".join(violations)
            for test in self.variant_tests:
                self.results.append({
                    'name': test.get('name', 'Безымянный тест'),
                    'input': test.get('input', ''),
                    'expected': test.get('expected', ''),
                    'actual': f"НАРУШЕНИЕ ТРЕБОВАНИЙ: {violation_message}",
                    'passed': False,
                    'points': 0,
                    'max_points': test.get('points', 0)
                })
        else:
            # Запускаем тесты только если нет нарушений
            for test in self.variant_tests:
                result = self.run_single_test(test)
                self.results.append(result)

        # Сохраняем результаты в базу данных
        self.save_results_to_db()

        return self.results

    def get_statistics(self) -> Dict[str, Any]:
        """Получение статистики по тестам"""
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r['passed'])
        total_points = sum(r['max_points'] for r in self.results)
        earned_points = sum(r['points'] for r in self.results)
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0

        return {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': total_tests - passed_tests,
            'total_points': total_points,
            'earned_points': earned_points,
            'success_rate': success_rate,
            'grade': self.calculate_grade(earned_points, total_points)
        }

    def calculate_grade(self, earned: int, total: int) -> str:
        """Вычисление оценки"""
        if total == 0:
            return "Н/Д"

        percentage = (earned / total) * 100

        if percentage >= 90:
            return "5 (Отлично)"
        elif percentage >= 75:
            return "4 (Хорошо)"
        elif percentage >= 60:
            return "3 (Удовлетворительно)"
        else:
            return "2 (Неудовлетворительно)"

    def get_detailed_report(self) -> str:
        """Получение подробного отчета о тестировании"""
        if not self.results:
            return "Тесты еще не запускались"

        stats = self.get_statistics()

        report = []
        report.append("=" * 70)
        report.append(f"ЛАБОРАТОРНАЯ РАБОТА №{self.config.get('lab_number')}")
        report.append(f"{self.config.get('title')}")
        report.append("=" * 70)
        report.append(f"Вариант: {self.variant}")
        report.append(f"Всего тестов: {stats['total_tests']}")
        report.append(f"Пройдено: {stats['passed_tests']}")
        report.append(f"Не пройдено: {stats['failed_tests']}")
        report.append(f"Баллы: {stats['earned_points']}/{stats['total_points']}")
        report.append(f"Успешность: {stats['success_rate']:.1f}%")
        report.append(f"Оценка: {stats['grade']}")
        report.append("-" * 70)

        # Детали по каждому тесту
        for i, result in enumerate(self.results, 1):
            status = "✅" if result['passed'] else "❌"
            report.append(f"\n{status} Тест {i}: {result['name']}")
            report.append(f"   Баллы: {result['points']}/{result['max_points']}")
            report.append(f"   Входные данные: {repr(result['input'])}")
            report.append(f"   Ожидалось: {result['expected']}")
            report.append(f"   Получено: {result['actual']}")

            if not result['passed']:
                report.append(f"   Причина: Ожидалось '{result['expected']}', получено '{result['actual']}'")

        report.append("\n" + "=" * 70)

        return "\n".join(report)

    def get_short_report(self) -> str:
        """Получение краткого отчета"""
        stats = self.get_statistics()

        return (f"Результаты: {stats['passed_tests']}/{stats['total_tests']} тестов пройдено, "
                f"баллы: {stats['earned_points']}/{stats['total_points']}, "
                f"оценка: {stats['grade']}")

    def save_results_to_db(self) -> bool:
        """
        Сохранение результатов тестирования в базу данных

        Returns:
            True если успешно, False если ошибка
        """
        if not self.student_id or not self.lab_id:
            print("DEBUG: student_id или lab_id не определены, сохранение в БД пропущено")
            return False

        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 1. Создаем запись о тестовом прогоне
            self._create_test_run(cursor)

            if not self.test_run_id:
                print("DEBUG: Не удалось создать запись о тестовом прогоне")
                return False

            # 2. Сохраняем результаты каждого теста
            for test_num, result in enumerate(self.results, 1):
                self._save_test_result(cursor, test_num, result)

            # 3. Обновляем общий статус прогона
            self._update_test_run_status(cursor)

            conn.commit()
            print(f"DEBUG: Результаты успешно сохранены в БД (test_run_id={self.test_run_id})")
            return True

        except Exception as e:
            print(f"DEBUG: Ошибка сохранения результатов в БД: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            if conn:
                conn.close()

    def _create_test_run(self, cursor: sqlite3.Cursor):
        """Создание записи о тестовом прогоне в таблице test_runs"""
        try:
            run_timestamp = datetime.now().isoformat()

            cursor.execute("""
                INSERT INTO test_runs (student_id, lab_id, run_timestamp, overall_status, execution_time_ms)
                VALUES (?, ?, ?, ?, ?)
            """, (
                self.student_id,
                self.lab_id,
                run_timestamp,
                "in_progress",
                0
            ))

            # Получаем ID новой записи
            self.test_run_id = cursor.lastrowid
            print(f"DEBUG: Создана запись test_run с ID={self.test_run_id}")

        except Exception as e:
            print(f"DEBUG: Ошибка при создании test_run: {e}")
            raise

    def _save_test_result(self, cursor: sqlite3.Cursor, test_num: int, result: Dict[str, Any]):
        """Сохранение результата одного теста в таблице test_results"""
        try:
            test_status = "passed" if result['passed'] else "failed"

            cursor.execute("""
                INSERT INTO test_results (run_id, test_number, input_data, expected_output, actual_output, test_status)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                self.test_run_id,
                test_num,
                result.get('input', ''),
                result.get('expected', ''),
                result.get('actual', ''),
                test_status
            ))

        except Exception as e:
            print(f"DEBUG: Ошибка при сохранении результата теста {test_num}: {e}")
            raise

    def _update_test_run_status(self, cursor: sqlite3.Cursor):
        """Обновление общего статуса прогона"""
        try:
            stats = self.get_statistics()

            # Определяем общий статус
            if stats['failed_tests'] == 0:
                overall_status = "passed"
            elif stats['passed_tests'] == 0:
                overall_status = "failed"
            else:
                overall_status = "partial"

            # Обновляем запись test_runs
            cursor.execute("""
                UPDATE test_runs
                SET overall_status = ?
                WHERE id = ?
            """, (overall_status, self.test_run_id))

            print(f"DEBUG: Статус test_run обновлен: {overall_status}")

        except Exception as e:
            print(f"DEBUG: Ошибка при обновлении статуса test_run: {e}")
            raise