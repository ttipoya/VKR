import pytest
import requests
import io
import sys
from unittest.mock import patch, mock_open

# URL с raw-версией файла из GitHub
GITHUB_RAW_URL = "https://raw.githubusercontent.com/ttipoya/lab/refs/heads/main/lab1.py"


def download_code_from_github(url):
    """Скачивает код из GitHub"""
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        pytest.fail(f"Не удалось скачать код из GitHub: {e}")


# Скачиваем код один раз для всех тестов
@pytest.fixture(scope="session")
def original_code(github_url):
    code = download_code_from_github(github_url)
    if not code:
        pytest.fail("Не удалось получить код из GitHub")
    return code


def run_code_with_input(code, input_data):

    mock_file = mock_open(read_data=input_data)

    with patch('builtins.open', mock_file):
        # Создаем объект для перехвата stdout
        fake_stdout = io.StringIO()
        with patch('sys.stdout', fake_stdout):
            try:
                # Выполняем код
                exec(code)
                return fake_stdout.getvalue()
            except Exception as e:
                return f"Ошибка выполнения: {e}"


# Тесты для проверки условия: числа должны иметь три последние цифры A16
def test_file_empty(original_code):
    """Тест на пустой файл"""
    output = run_code_with_input(original_code, "")
    assert "Файл пуст или не тот" in output


def test_no_matching_numbers(original_code):
    """Тест на отсутствие подходящих чисел (нет чисел с тремя последними цифрами A16)"""
    output = run_code_with_input(original_code, "123 456 789 AB1 2AB 1A6 A1B ")
    print(f"Вывод: {repr(output)}")
    assert "Нужных чисел не найдено" in output


def test_single_matching_number(original_code):
    """Тест с одним подходящим числом (три последние цифры - A16)"""
    output = run_code_with_input(original_code, "12A16 456 789 ")
    print(f"Вывод: {repr(output)}")
    # Должно найти 12A16
    assert "один два A один шесть" in output or "12A16" in output


def test_multiple_matching_numbers(original_code):
    """Тест с несколькими подходящими числами - должно вывести максимальное"""
    # Все числа имеют три последние цифры A16
    # В hex: 1A16 (6680), 2A16 (10776), 3A16 (14872), 4A16 (18968)
    output = run_code_with_input(original_code, "1A16 2A16 3A16 4A16 ")
    print(f"Вывод для multiple: {repr(output)}")
    # Максимальное - 4A16
    assert "четыре A один шесть" in output or "4A16" in output


def test_numbers_with_A16_at_end(original_code):
    """Тест: числа должны иметь A16 именно на последних трёх позициях"""
    # Подходят только числа, у которых последние 3 цифры = A16
    # A16 в середине: 12A163 (последние 3 цифры = 163, не подходит)
    # A16 в начале: A1645 (последние 3 цифры = 645, не подходит)
    # A16 в конце: 45A16 (последние 3 цифры = A16, подходит)
    output = run_code_with_input(original_code, "12A163 A1645 45A16 ")
    print(f"Вывод для positions: {repr(output)}")
    # Должно найти только 45A16
    assert "четыре пять A один шесть" in output or "45A16" in output


def test_find_maximum_correctly(original_code):
    """Тест на правильное нахождение максимума среди чисел с окончанием A16"""
    # Все числа имеют три последние цифры A16
    # В hex: 1A16 (6680), 2A16 (10776), 3A16 (14872), 4A16 (18968), 5A16 (23064)
    output = run_code_with_input(original_code, "1A16 2A16 3A16 4A16 5A16 ")
    print(f"Вывод для max: {repr(output)}")
    # Максимальное - 5A16
    assert "пять A один шесть" in output or "5A16" in output


def test_maximum_not_last(original_code):
    """Тест: максимальное число не последнее в списке"""
    output = run_code_with_input(original_code, "1A16 5A16 2A16 3A16 4A16 ")
    print(f"Вывод для max_not_last: {repr(output)}")
    # Максимальное - 5A16
    assert "пять A один шесть" in output or "5A16" in output


def test_with_hex_digits_AF(original_code):
    """Тест с hex-цифрами A-F перед A16"""
    # Все числа имеют три последние цифры A16
    # В hex: 1A16, B2A16, C5A16, D7A16, E9A16
    output = run_code_with_input(original_code, "1A16 B2A16 C5A16 D7A16 E9A16 ")
    print(f"Вывод для hex_AF: {repr(output)}")
    # Максимальное - E9A16
    assert "E девять A один шесть" in output or "E9A16" in output


def test_with_various_lengths(original_code):
    """Тест с числами разной длины, оканчивающимися на A16"""
    # Все числа имеют три последние цифры A16
    # A16 (само число из 3 цифр)
    # 1A16 (4 цифры)
    # 12A16 (5 цифр)
    # 123A16 (6 цифр)
    # 1234A16 (7 цифр)
    output = run_code_with_input(original_code, "A16 1A16 12A16 123A16 1234A16 ")
    print(f"Вывод для lengths: {repr(output)}")
    # Максимальное - 1234A16
    assert "один два три четыре A один шесть" in output or "1234A16" in output


def test_A16_itself(original_code):
    """Тест с самим числом A16 (трёхзначное число)"""
    output = run_code_with_input(original_code, "A16 ")
    print(f"Вывод для A16_itself: {repr(output)}")
    # Должно найти A16 (само число из 3 цифр)
    assert "A один шесть" in output or "A16" in output


def test_A16_with_prefix(original_code):
    """Тест с A16 и различными префиксами"""
    output = run_code_with_input(original_code, "12A16 34A16 56A16 78A16 90A16 ")
    print(f"Вывод для prefix: {repr(output)}")
    # Максимальное - 90A16 (в hex 90A16 = 592150)
    assert "девять ноль A один шесть" in output or "90A16" in output


def test_numbers_with_same_prefix(original_code):
    """Тест с числами, имеющими одинаковый префикс перед A16"""
    output = run_code_with_input(original_code, "1A16 2A16 3A16 4A16 5A16 6A16 7A16 8A16 9A16 ")
    print(f"Вывод для same_prefix: {repr(output)}")
    # Максимальное - 9A16
    assert "девять A один шесть" in output or "9A16" in output


def test_mixed_valid_invalid(original_code):
    """Тест со смешанными данными (валидные и невалидные числа)"""
    # Подходят только числа с тремя последними цифрами A16:
    # 45A16, 9A16, 23A16 (у всех последние 3 цифры = A16)
    # Не подходят: 123 (нет A), 1A2 (последние 3 цифры = 1A2), 789, ABC, A1B
    output = run_code_with_input(original_code, "123 1A2 45A16 789 ABC A1B 9A16 23A16 ")
    print(f"Вывод для mixed: {repr(output)}")
    # Максимальное среди подходящих - 45A16
    # (45A16 > 9A16 > 23A16 в hex: 45A16=28438, 9A16=24616, 23A16=14506)
    assert "четыре пять A один шесть" in output or "45A16" in output


def test_boundary_cases(original_code):
    """Тест граничных случаев"""
    # Минимальное подходящее число (само A16)
    output = run_code_with_input(original_code, "A16 A26 A36 A46 A56 ")
    print(f"Вывод для boundary_min: {repr(output)}")
    # Только A16 подходит (у A26 последние 3 цифры = A26)
    assert "A один шесть" in output or "A16" in output

    # Максимальное подходящее число с цифрами перед A16
    output = run_code_with_input(original_code, "FA16 FFA16 FFFA16 ")
    print(f"Вывод для boundary_max: {repr(output)}")
    # Максимальное - FFFA16
    assert "F F F A один шесть" in output or "FFFA16" in output


def test_no_false_positives(original_code):
    """Тест на отсутствие ложных срабатываний"""
    # Ни одно из этих чисел не должно подойти, т.к. последние 3 цифры не равны A16
    test_inputs = [
        "A1", "A6", "16", "A1A", "A61", "A166", "16A", "A16A", "16A1",
        "12A", "A13", "A14", "A15", "A17", "A18", "A19",
        "1A6", "2A6", "3A6", "4A6", "5A6", "6A6", "7A6", "8A6", "9A6"
    ]
    output = run_code_with_input(original_code, " ".join(test_inputs) + " ")
    print(f"Вывод для false_positives: {repr(output)}")
    assert "Нужных чисел не найдено" in output or output.strip() == ""


def test_case_sensitivity(original_code):
    """Тест на регистрозависимость"""
    # Проверяем, что 'a16' (маленькими буквами) не путается с 'A16'
    output = run_code_with_input(original_code, "a16 A16 ")
    print(f"Вывод для case: {repr(output)}")
    # Должно найти только A16 (если код регистрозависим)
    # Если код регистронезависим, то найдет оба
    assert "A16" in output


def test_multiple_numbers_same_value(original_code):
    """Тест с несколькими одинаковыми числами"""
    output = run_code_with_input(original_code, "A16 A16 A16 ")
    print(f"Вывод для same_values: {repr(output)}")
    # Должно найти A16
    assert "A один шесть" in output or "A16" in output


def test_numbers_in_different_order(original_code):
    """Тест с числами в разном порядке"""
    output = run_code_with_input(original_code, "5A16 2A16 8A16 1A16 9A16 3A16 ")
    print(f"Вывод для different_order: {repr(output)}")
    # Максимальное - 9A16
    assert "девять A один шесть" in output or "9A16" in output


# Параметризованные тесты
@pytest.mark.parametrize("test_input,expected_max", [
    ("1A16 2A16 3A16", "3A16"),
    ("A16 1A16 2A16", "2A16"),
    ("A1A B2B C3C", "Нужных чисел не найдено"),
    ("FA16 FFA16 FFFA16", "FFFA16"),
    ("123 45A16 789 12A16", "45A16"),
    ("A16 A26 A36", "A16"),
    ("5A16 2A16 8A16 1A16 9A16", "9A16"),
    ("", "Файл пуст или не тот"),
])
def test_parametrized(original_code, test_input, expected_max):
    """Параметризованный тест для разных входных данных"""
    output = run_code_with_input(original_code, test_input + " ")
    print(f"Вывод для '{test_input}': {repr(output)}")
    assert expected_max in output


# Конфигурация pytest
def pytest_addoption(parser):
    parser.addoption(
        "--github-url",
        action="store",
        default=GITHUB_RAW_URL,
        help="URL для скачивания кода из GitHub"
    )


@pytest.fixture(scope="session")
def github_url(request):
    """Фикстура для получения URL из командной строки"""
    return request.config.getoption("--github-url")


# Фикстура для сохранения кода локально
@pytest.fixture(scope="session")
def saved_code_file(original_code, tmp_path_factory):
    """Сохраняет скачанный код во временный файл для отладки"""
    tmp_path = tmp_path_factory.mktemp("code")
    code_file = tmp_path / "downloaded_code.py"
    code_file.write_text(original_code, encoding='utf-8')
    return code_file


# Тест для проверки загрузки кода
def test_code_downloaded(original_code):
    """Проверяет, что код успешно загружен"""
    assert original_code is not None
    assert len(original_code) > 0
    print(f"Код загружен, длина: {len(original_code)} символов")


# Тест для проверки формата вывода (прописью)
def test_output_format(original_code):
    """Проверяет, что числа выводятся прописью"""
    output = run_code_with_input(original_code, "1A16 2A16 3A16 ")
    print(f"Вывод формата: {repr(output)}")
    # Проверяем, что вывод содержит слова для цифр
    has_words = any(word in output for word in ['ноль', 'один', 'два', 'три', 'четыре',
                                                'пять', 'шесть', 'семь', 'восемь', 'девять'])
    # Буквы A-F могут выводиться как есть
    assert has_words or ('A' in output and 'один' in output and 'шесть' in output)


if __name__ == "__main__":
    # Запуск с подробным выводом
    pytest.main(["-v", "-s", __file__])