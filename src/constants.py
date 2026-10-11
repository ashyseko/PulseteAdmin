"""Константы приложения: цвета, строки, URL."""

import os
from datetime import datetime, timedelta

API_BASE_URL = "http://localhost:8000"

# --- GigaChat ---
GIGACHAT_API_KEY = os.environ.get("GIGACHAT_API_KEY", "")

# --- Цвета текста ---
COLOR_TEXT_PRIMARY = "#1A1918"
COLOR_TEXT_SECONDARY = "#6D6C6A"
COLOR_TEXT_TERTIARY = "#8A8986"
COLOR_TEXT_PLACEHOLDER = "#B0AEA9"

COLOR_TEXT_GREEN = "#2F6B47"
COLOR_TEXT_YELLOW = "#8A6A1F"
COLOR_TEXT_RED = "#A4442A"
COLOR_TEXT_PURPLE = "#5A3D8A"
COLOR_TEXT_WHITE = "#FFFFFF"

# --- Фоновые цвета ---
BG_COLOR_PRIMARY = "#F5F4F1"
BG_COLOR_CARD = "#FFFFFF"
BG_BORDER = "#E5E4E1"

BG_AVATAR_WITH_ANSWERS = "#D8C8F0"
BG_AVATAR_WITHOUT_ANSWERS = "#E8E7E4"

BG_ANSWER_GREEN = "#D8C8F0"
BG_ANSWER_YELLOW = "#F7ECD0"
BG_ANSWER_RED = "#FBE3DC"
BG_ANSWER_NEUTRAL = "#EDEDEB"

BG_NAV_ACTIVE = "#5A3D8A"
BG_NAV_INACTIVE = "#FFFFFF"
BG_NAV_CONTAINER = "#F5F4F1"

BG_SNACKBAR_SUCCESS = "#2F6B47"
BG_SNACKBAR_ERROR = "#A4442A"

# --- Размеры ---
WINDOW_WIDTH = 400
WINDOW_HEIGHT = 800
NAV_HEIGHT = 60

# --- Строки ---
APP_TITLE = "PulseteAdmin"
PAGE_TITLE = "Пульс класса - Админ"
FONT_FAMILY = "Inter"
SUBTITLE_PLACEHOLDER = "Последние ответы · загрузка..."


# --- Утилиты для работы с неделями ---

def get_current_week_range() -> tuple[datetime, datetime]:
    """Возвращает начало (понедельник) и конец (воскресенье) текущей недели."""
    today = datetime.now()
    # Monday = 0, Sunday = 6
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    return start_of_week.replace(hour=0, minute=0, second=0, microsecond=0), end_of_week.replace(hour=23, minute=59, second=59, microsecond=0)


def get_week_range(offset: int = 0) -> tuple[datetime, datetime]:
    """Возвращает начало и конец недели с учётом смещения (0 = текущая, -1 = прошлая, +1 = следующая)."""
    today = datetime.now()
    start_of_week = today - timedelta(days=today.weekday()) + timedelta(weeks=offset)
    end_of_week = start_of_week + timedelta(days=6)
    return start_of_week.replace(hour=0, minute=0, second=0, microsecond=0), end_of_week.replace(hour=23, minute=59, second=59, microsecond=0)


def format_week_range(start: datetime, end: datetime) -> str:
    """Форматирует диапазон недели: '5 – 11 окт.'"""
    months = ["", "янв", "фев", "мар", "апр", "мая", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"]
    return f"{start.day} – {end.day} {months[end.month]}"


def filter_answers_by_week(answers_data: list[dict], week_start: datetime, week_end: datetime) -> list[dict]:
    """Фильтрует ответы по выбранной неделе."""
    filtered = []
    for ans in answers_data:
        ts = ans.get("created_at")
        if not ts:
            continue
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if week_start <= dt <= week_end:
                filtered.append(ans)
        except (ValueError, AttributeError):
            continue
    return filtered
