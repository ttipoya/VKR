# ============================================================================
# КОНФИГУРАЦИЯ ВИЗУАЛЬНОГО СТИЛЯ
# ============================================================================
# Централизованная конфигурация для всех визуальных элементов приложения

# === ОСНОВНЫЕ ЦВЕТА (Бело-серая палитра) ===
COLORS = {
    # Основные цвета - серая палитра
    "primary": "#4a4a4a",           # Темно-серый (заголовки)
    "primary_dark": "#2d2d2d",      # Еще темнее серый
    "secondary": "#707070",         # Средний серый (акценты)
    "success": "#2e7d32",           # Зеленый (успех)
    "error": "#c62828",             # Красный (ошибка)
    "warning": "#f57f17",           # Оранжевый (предупреждение)
    "info": "#1565c0",              # Синий (информация)
    
    # Фоны
    "bg_light": "#eeeeee",          # Светлый серый фон
    "bg_dark": "#333333",           # Темный серый фон
    "bg_panel": "#ffffff",          # Белый фон панели
    "bg_secondary": "#f8f8f8",      # Светло-серый альтернативный фон
    
    # Текст
    "text_primary": "#1a1a1a",      # Почти черный текст
    "text_secondary": "#666666",    # Серый текст
    "text_light": "#ffffff",        # Белый текст
    
    # Статусы
    "status_pass": "#e8f5e9",       # Светло-зеленый фон для успеха
    "status_fail": "#ffebee",       # Светло-красный фон для ошибки
    "status_info": "#e3f2fd",       # Светло-синий фон для информации
}

# === ЦВЕТОВЫЕ ПАЛЛЕТЫ ДЛЯ РАЗНЫХ СТАТУСОВ ===
STATUS_COLORS = {
    "passed": {
        "bg": "#e8f5e8",
        "fg": "#1e7e1e",
        "icon": "✅"
    },
    "failed": {
        "bg": "#ffebee",
        "fg": "#c62828",
        "icon": "❌"
    },
    "pending": {
        "bg": "#fff3e0",
        "fg": "#f57f17",
        "icon": "⏳"
    },
    "info": {
        "bg": "#e3f2fd",
        "fg": "#1565c0",
        "icon": "ℹ️"
    }
}

# === ШРИФТЫ ===
FONTS = {
    "header_large": ("Arial", 18, "bold"),
    "header": ("Arial", 16, "bold"),
    "subheader": ("Arial", 14, "bold"),
    "title": ("Arial", 12, "bold"),
    "regular": ("Arial", 10),
    "small": ("Arial", 9),
    "monospace": ("Courier New", 10),
    "monospace_small": ("Courier New", 9),
}

# === ОТСТУПЫ И РАЗМЕРЫ ===
SPACING = {
    "padding_small": 5,
    "padding": 10,
    "padding_large": 15,
    "padding_xl": 20,
    
    "margin_small": 2,
    "margin": 5,
    "margin_large": 10,
    
    "border_radius": 5,
    "border_width": 1,
}

# === ТАБЛИЦА ===
TABLE_CONFIG = {
    "header_bg": COLORS["primary"],
    "header_fg": COLORS["text_light"],
    "row_bg": COLORS["bg_panel"],
    "row_bg_alt": "#f9f9f9",
    "row_fg": COLORS["text_primary"],
    "border_color": "#ddd",
    "header_height": 35,
    "row_height": 30,
    "column_min_width": 80,
}

# === КНОПКИ ===
BUTTON_CONFIG = {
    "fg_color": COLORS["primary"],
    "hover_color": COLORS["primary_dark"],
    "text_color": COLORS["text_light"],
    "border_width": 0,
    "corner_radius": 5,
    "font": FONTS["regular"],
}

# === ФРЕЙМЫ И КОНТЕЙНЕРЫ ===
FRAME_CONFIG = {
    "fg_color": COLORS["bg_panel"],
    "border_color": COLORS["primary"],
    "corner_radius": SPACING["border_radius"],
}

# === МЕТКИ И ТЕКСТ ===
LABEL_CONFIG = {
    "text_color": COLORS["text_primary"],
    "font": FONTS["regular"],
}

LABEL_HEADER = {
    "text_color": COLORS["text_light"],
    "font": FONTS["header"],
    "fg_color": COLORS["primary"],
}

# === ТЕКСТОВЫЕ ПОЛЯ ===
TEXTBOX_CONFIG = {
    "fg_color": COLORS["bg_panel"],
    "text_color": COLORS["text_primary"],
    "font": FONTS["monospace"],
    "wrap": "word",
}

# === SCROLLBAR ===
SCROLLBAR_CONFIG = {
    "fg_color": COLORS["bg_light"],
    "button_color": COLORS["primary"],
    "button_hover_color": COLORS["primary_dark"],
}

# === ТАБЛИЦА SQLite ===
SQLITE_TABLE_CONFIG = {
    "header_fg_color": COLORS["primary"],
    "header_text_color": COLORS["text_light"],
    "row_height": 35,
    "column_spacing": 10,
    "alternating_colors": True,
    "row_color_1": COLORS["bg_panel"],
    "row_color_2": COLORS["bg_secondary"],
    "null_text": "NULL",
    "null_color": COLORS["text_secondary"],
}

# === ТЕСТИРОВАНИЕ ===
TEST_RESULT_CONFIG = {
    "passed": {
        "bg": STATUS_COLORS["passed"]["bg"],
        "fg": STATUS_COLORS["passed"]["fg"],
        "icon": "✅"
    },
    "failed": {
        "bg": STATUS_COLORS["failed"]["bg"],
        "fg": STATUS_COLORS["failed"]["fg"],
        "icon": "❌"
    },
    "running": {
        "bg": STATUS_COLORS["pending"]["bg"],
        "fg": STATUS_COLORS["pending"]["fg"],
        "icon": "⏳"
    }
}

# === ТАБЫ ===
TAB_CONFIG = {
    "fg_color": COLORS["bg_light"],
    "border_color": COLORS["primary"],
    "text_color": COLORS["text_primary"],
    "segmented_button_fg_color": COLORS["primary"],
    "segmented_button_selected_color": COLORS["primary"],
    "segmented_button_selected_hover_color": COLORS["primary_dark"],
}
