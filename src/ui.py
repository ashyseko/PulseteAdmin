"""UI-компоненты и логика экранов."""

import asyncio
from datetime import datetime, timedelta

import flet as ft

from src.ai_analyzer import GigaChatService
from src.api import ApiService
from src.constants import (
    APP_TITLE,
    BG_ANSWER_GREEN,
    BG_ANSWER_NEUTRAL,
    BG_ANSWER_RED,
    BG_ANSWER_YELLOW,
    BG_AVATAR_WITH_ANSWERS,
    BG_AVATAR_WITHOUT_ANSWERS,
    BG_BORDER,
    BG_COLOR_CARD,
    BG_NAV_ACTIVE,
    BG_NAV_CONTAINER,
    BG_NAV_INACTIVE,
    BG_SNACKBAR_ERROR,
    BG_SNACKBAR_SUCCESS,
    COLOR_TEXT_GREEN,
    COLOR_TEXT_PLACEHOLDER,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_PURPLE,
    COLOR_TEXT_RED,
    COLOR_TEXT_SECONDARY,
    COLOR_TEXT_TERTIARY,
    COLOR_TEXT_WHITE,
    COLOR_TEXT_YELLOW,
    FONT_FAMILY,
    NAV_HEIGHT,
    PAGE_TITLE,
    SUBTITLE_PLACEHOLDER,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
    get_current_week_range,
    get_week_range,
    format_week_range,
    filter_answers_by_week,
)

import os


# --- Вспомогательные функции ---


def get_initials(name: str) -> str:
    """Получить инициалы из имени."""
    parts = name.strip().split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[1][0]).upper()
    elif len(parts) == 1:
        return parts[0][:2].upper()
    return name[:2].upper()


def get_answer_circle(value: int | None) -> ft.Container:
    """Создать круг с оценкой или прочерком."""
    if value is None:
        return ft.Container(
            content=ft.Text("—", size=12, weight=ft.FontWeight.W_600, color=COLOR_TEXT_PLACEHOLDER),
            width=26,
            height=26,
            bgcolor=BG_ANSWER_NEUTRAL,
            border_radius=13,
            alignment=ft.alignment.Alignment(0, 0),
        )

    if value >= 4:
        color = COLOR_TEXT_GREEN
        bg_color = BG_ANSWER_GREEN
    elif value == 3:
        color = COLOR_TEXT_YELLOW
        bg_color = BG_ANSWER_YELLOW
    else:
        color = COLOR_TEXT_RED
        bg_color = BG_ANSWER_RED

    return ft.Container(
        content=ft.Text(str(value), size=12, weight=ft.FontWeight.W_600, color=color),
        width=26,
        height=26,
        bgcolor=bg_color,
        border_radius=13,
        alignment=ft.alignment.Alignment(0, 0),
    )


def format_last_answer(ts: str | None) -> str:
    """Форматирует дату последнего ответа (UTC → Moscow UTC+3)."""
    if not ts:
        return ""
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        dt_msk = dt + timedelta(hours=3)
        return dt_msk.strftime("%d.%m.%Y %H:%M")
    except (ValueError, AttributeError):
        return ""


def get_avatar_bg(has_answers: bool) -> str:
    return BG_AVATAR_WITH_ANSWERS if has_answers else BG_AVATAR_WITHOUT_ANSWERS


def get_avatar_color(has_answers: bool) -> str:
    return COLOR_TEXT_PURPLE if has_answers else COLOR_TEXT_TERTIARY


def get_bar_color(value: float) -> str:
    """Возвращает цвет прогресс-бара на основе значения."""
    if value >= 4.0:
        return COLOR_TEXT_PURPLE
    return COLOR_TEXT_YELLOW


def get_bar_bg(value: float) -> str:
    """Возвращает цвет фона прогресс-бара."""
    if value >= 4.0:
        return BG_ANSWER_GREEN
    return BG_ANSWER_YELLOW


def _create_category_row(name: str, value: float | None, max_value: float = 5.0) -> ft.Container:
    """Создаёт строку категории с прогресс-барами."""
    bar_width = 96  # ~6rem in pixels
    bar_height = 8  # ~0.5rem

    if value is not None and value > 0:
        fill_ratio = min(value / max_value, 1.0)
        fill_width = bar_width * fill_ratio
        fill = ft.Container(
            width=fill_width,
            height=bar_height,
            bgcolor=get_bar_color(value),
        )
    else:
        fill = ft.Container(
            width=0,
            height=bar_height,
            bgcolor=COLOR_TEXT_PLACEHOLDER,
        )

    track = ft.Container(
        content=fill,
        width=bar_width,
        height=bar_height,
        bgcolor=BG_ANSWER_NEUTRAL,
    )

    score_text = ft.Text(
        f"{value:.1f}" if value is not None else "—",
        size=15,
        weight=ft.FontWeight.W_600,
        color=COLOR_TEXT_PRIMARY,
        width=32,
    )

    label = ft.Text(name, size=14, weight=ft.FontWeight.W_500, color=COLOR_TEXT_PRIMARY, expand=True)

    return ft.Container(
        content=ft.Row(
            controls=[label, track, score_text],
            spacing=12,
            alignment=ft.MainAxisAlignment.START,
        ),
        bgcolor=BG_COLOR_CARD,
        padding=ft.Padding.symmetric(horizontal=16, vertical=14),
        margin=ft.Margin.only(bottom=2),
    )


def _calculate_category_avg(question_id: int, answers: list[dict]) -> float | None:
    """Вычисляет среднее значение для вопроса."""
    values = [a["value"] for a in answers if a.get("question_id") == question_id and a.get("value") is not None]
    if not values:
        return None
    return sum(values) / len(values)


# --- Страница обзора ---


def overview_page(
    students_data: list[dict],
    answers_data: list[dict],
    questions_data: list[dict],
    page: ft.Page,
    api: ApiService,
):
    """Страница обзора класса."""
    page.title = PAGE_TITLE
    page.padding = 0
    page.window_width = WINDOW_WIDTH
    page.window_height = WINDOW_HEIGHT

    # Week state
    _week_offset = 0
    week_start, week_end = get_week_range(_week_offset)
    week_label = format_week_range(week_start, week_end)

    subtitle_text = ft.Text(
        "Результаты за неделю",
        size=13,
        color=COLOR_TEXT_SECONDARY,
    )

    # Week picker buttons
    week_buttons = ft.Row(
        controls=[],
        spacing=4,
        wrap=False,
    )

    def _set_week(offset):
        nonlocal _week_offset, week_start, week_end, week_label
        _week_offset = offset
        week_start, week_end = get_week_range(_week_offset)
        week_label = format_week_range(week_start, week_end)
        _update_week_buttons()
        _render()

    def _update_week_buttons():
        week_buttons.controls.clear()
        for i in range(-5, 1):  # 5 назад + текущая
            ws, we = get_week_range(i)
            label = format_week_range(ws, we)
            btn = ft.Container(
                content=ft.Text(label, size=11, weight=ft.FontWeight.W_500, color=COLOR_TEXT_WHITE if i == _week_offset else COLOR_TEXT_PRIMARY),
                bgcolor=COLOR_TEXT_PURPLE if i == _week_offset else COLOR_TEXT_WHITE,
                border=ft.border.Border.all(1, COLOR_TEXT_PURPLE if i == _week_offset else BG_BORDER),
                border_radius=6,
                padding=ft.Padding.symmetric(vertical=6, horizontal=10),
                on_click=lambda ie, off=i: _set_week(off),
            )
            week_buttons.controls.append(btn)

    # Average score display
    avg_score_text = ft.Text("0.0", size=32, weight=ft.FontWeight.W_400, color=COLOR_TEXT_PRIMARY)
    avg_change_text = ft.Text("", size=13, weight=ft.FontWeight.W_600, color=COLOR_TEXT_PURPLE)
    avg_participants_text = ft.Text("Участвовали 0 из 0 учеников", size=12, color=COLOR_TEXT_PLACEHOLDER)

    # Category rows container
    category_rows = ft.Column(
        controls=[],
        spacing=0,
        expand=True,
    )

    # AI Analysis
    ai_analysis_text = ft.Text(
        "Нажмите кнопку для получения AI-анализа",
        size=13,
        color=COLOR_TEXT_SECONDARY,
        selectable=True,
    )
    ai_loading = ft.ProgressRing(width=20, height=20, visible=False, stroke_width=2)
    ai_container = ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Icon(ft.icons.Icons.AUTO_AWESOME, size=18, color=COLOR_TEXT_PURPLE),
                        ft.Text("AI-заключение", size=15, weight=ft.FontWeight.W_600, color=COLOR_TEXT_PRIMARY),
                    ],
                    spacing=8,
                ),
                ai_loading,
                ai_analysis_text,
            ],
            spacing=8,
        ),
        bgcolor=BG_COLOR_CARD,
        padding=ft.Padding.symmetric(vertical=16, horizontal=16),
        margin=ft.Margin.only(top=4, bottom=2),
        border_radius=8,
        border=ft.border.Border.all(1, BG_BORDER),
    )

    async def _run_ai_analysis():
        """Запускает AI-анализ текущей недели."""
        api_key = os.environ.get("GIGACHAT_API_KEY", "")
        if not api_key:
            _show_snackbar("Сначала настройте переменную окружения GIGACHAT_API_KEY", error=True)
            return

        ai_loading.visible = True
        ai_analysis_text.value = "Анализирую данные..."
        _update()

        try:
            week_answers = filter_answers_by_week(answers_data, week_start, week_end)
            service = GigaChatService(api_key=api_key)
            analysis = await service.analyze_week(questions_data, week_answers, week_label)
            ai_analysis_text.value = analysis
            _show_snackbar("AI-анализ готов")
            await service.close()
        except Exception as ex:
            ai_analysis_text.value = f"Ошибка: {str(ex)}"
            _show_snackbar(f"Ошибка AI-анализа: {ex}", error=True)
        finally:
            ai_loading.visible = False
            _update()

    ai_button = ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(ft.icons.Icons.AUTO_GRAPH, size=16, color=COLOR_TEXT_WHITE),
                ft.Text("Получить анализ", size=13, weight=ft.FontWeight.W_600, color=COLOR_TEXT_WHITE),
            ],
            spacing=6,
        ),
        bgcolor=COLOR_TEXT_PURPLE,
        border_radius=6,
        padding=ft.Padding.symmetric(vertical=8, horizontal=12),
        on_click=lambda e: page.run_task(_run_ai_analysis),
    )

    def _update():
        page.update()

    def _show_snackbar(message: str, error: bool = False):
        import flet as ft
        snackbar = ft.SnackBar(
            content=ft.Text(message),
            bgcolor=BG_SNACKBAR_ERROR if error else BG_SNACKBAR_SUCCESS,
        )
        page.snack_bar = snackbar
        page.snack_bar.open = True
        _update()

        _update_week_buttons()

    def _render():
        """Перерисовывает обзор."""
        # Filter answers by week
        week_answers = filter_answers_by_week(answers_data, week_start, week_end)

        # Calculate overall average
        values = [a["value"] for a in week_answers if a.get("value") is not None]
        avg = 0.0
        if values:
            avg = sum(values) / len(values)
            avg_score_text.value = f"{avg:.1f}"
        else:
            avg_score_text.value = "0.0"

        # Calculate participants
        participants = len(set(a["student_id"] for a in week_answers))
        total_students = len(students_data)
        avg_participants_text.value = f"Участвовали {participants} из {total_students} учеников"

        # Calculate change from last week
        last_week_start, last_week_end = get_week_range(_week_offset - 1)
        last_week_answers = filter_answers_by_week(answers_data, last_week_start, last_week_end)
        last_values = [a["value"] for a in last_week_answers if a.get("value") is not None]
        if values and last_values:
            last_avg = sum(last_values) / len(last_values)
            diff = avg - last_avg
            sign = "+" if diff > 0 else ""
            avg_change_text.value = f"{sign}{diff:.1f} к прошлой неделе"
            avg_change_text.color = COLOR_TEXT_GREEN if diff >= 0 else COLOR_TEXT_RED
        elif values:
            avg_change_text.value = "Нет данных за прошлую неделю"
            avg_change_text.color = COLOR_TEXT_PLACEHOLDER
        else:
            avg_change_text.value = ""

        # Calculate category averages
        category_rows.controls.clear()
        for q in questions_data:
            cat_avg = _calculate_category_avg(q["id"], week_answers)
            row = _create_category_row(q["text"], cat_avg)
            category_rows.controls.append(row)

        _update_week_buttons()
        _update()

    # Header
    header = ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text("Обзор класса", size=22, weight=ft.FontWeight.W_600, color=COLOR_TEXT_PRIMARY),
                    ],
                    spacing=4,
                    wrap=True,
                ),
                ft.Row(
                    controls=[
                        subtitle_text,
                    ],
                    spacing=4,
                ),
                week_buttons,
            ],
            spacing=4,
            wrap=True,
        ),
        padding=ft.Padding.only(left=24, right=24, top=8, bottom=8),
        expand=False,
    )

    # Average score card
    avg_card = ft.Container(
        content=ft.Column(
            controls=[
                ft.Text("Средний балл", size=15, weight=ft.FontWeight.W_600, color=COLOR_TEXT_PRIMARY, text_align=ft.TextAlign.CENTER),
                avg_score_text,
                avg_change_text,
                avg_participants_text,
            ],
            spacing=4,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            tight=True,
        ),
        bgcolor=BG_COLOR_CARD,
        padding=ft.Padding.symmetric(vertical=20, horizontal=20),
        margin=ft.Margin.only(top=4, bottom=2),
    )

    scrollable_content = ft.Column(
        controls=[avg_card, category_rows, ai_container, ai_button],
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )

    return header, scrollable_content, _render


def _format_short_date(dt: datetime) -> str:
    """Форматирует дату в коротком формате: '24 мар'."""
    months = ["", "янв", "фев", "мар", "апр", "мая", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"]
    return f"{dt.day} {months[dt.month]}"


def _format_delta(delta: float) -> str:
    """Форматирует дельту: +0.3, -0.4, 0.0."""
    if delta > 0:
        return f"+{delta:.1f}"
    elif delta < 0:
        return f"{delta:.1f}"
    return f"{delta:.1f}"


def _delta_color(delta: float) -> str:
    """Цвет дельты: зелёный/жёлтый/серый."""
    if delta > 0:
        return COLOR_TEXT_PURPLE
    elif delta < 0:
        return COLOR_TEXT_YELLOW
    return COLOR_TEXT_PLACEHOLDER


def dynamic_page(
    students_data: list[dict],
    answers_data: list[dict],
    questions_data: list[dict],
    page: ft.Page,
    api: ApiService,
):
    """Страница динамики — сравнение с прошлыми неделями."""
    page.title = PAGE_TITLE
    page.padding = 0
    page.window_width = WINDOW_WIDTH
    page.window_height = WINDOW_HEIGHT

    # Current week data
    week_start, week_end = get_week_range(0)
    week_label = format_week_range(week_start, week_end)

    subtitle_text = ft.Text(
        "Сравнение с прошлыми неделями",
        size=13,
        color=COLOR_TEXT_SECONDARY,
    )

    # Average score by week chart
    chart_title = ft.Text("Средний балл по неделям", size=15, weight=ft.FontWeight.W_600, color=COLOR_TEXT_PRIMARY, text_align=ft.TextAlign.CENTER)
    chart_weeks = ft.Column(controls=[], spacing=0)

    # Category change rows
    category_changes = ft.Column(controls=[], spacing=0, expand=True)

    def _update():
        page.update()

    def _render():
        # Filter current week answers
        current_answers = filter_answers_by_week(answers_data, week_start, week_end)

        # Calculate averages for last 5 weeks + current
        week_data = []
        for i in range(-5, 1):  # 5 previous + current
            ws, we = get_week_range(i)
            week_answers = filter_answers_by_week(answers_data, ws, we)
            values = [a["value"] for a in week_answers if a.get("value") is not None]
            avg = sum(values) / len(values) if values else None
            week_data.append((ws, avg))

        # Build chart
        chart_weeks.controls.clear()
        valid_avgs = [w[1] for w in week_data if w[1] is not None]
        max_avg = max(valid_avgs) if valid_avgs else 5.0
        chart_height = 90  # height of chart area

        chart_row = ft.Row(
            controls=[],
            spacing=8,
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.END,
        )

        for ws, avg in week_data:
            if avg is None:
                bar_height = 8
                bar_color = BG_ANSWER_NEUTRAL
                value_text = ft.Text("—", size=11, color=COLOR_TEXT_PLACEHOLDER)
                label_text = ft.Text(_format_short_date(ws), size=10, color=COLOR_TEXT_PLACEHOLDER)
            else:
                is_current = ws == week_start
                bar_height = max(8, (avg / max_avg) * chart_height)
                bar_color = COLOR_TEXT_PURPLE if is_current else BG_ANSWER_GREEN
                value_text = ft.Text(f"{avg:.1f}", size=11, weight=ft.FontWeight.W_600, color=COLOR_TEXT_PRIMARY if is_current else COLOR_TEXT_SECONDARY)
                label_text = ft.Text(_format_short_date(ws), size=10, weight=ft.FontWeight.W_600 if is_current else ft.FontWeight.W_400, color=COLOR_TEXT_PURPLE if is_current else COLOR_TEXT_PLACEHOLDER)

            chart_row.controls.append(ft.Column(
                controls=[
                    value_text,
                    ft.Container(width=64, height=bar_height, bgcolor=bar_color, border_radius=4),
                    label_text,
                ],
                spacing=4,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.END,
            ))

        chart_weeks.controls.append(chart_row)

        # Calculate category changes (current vs previous week)
        category_changes.controls.clear()
        last_week_start, last_week_end = get_week_range(-1)
        last_answers = filter_answers_by_week(answers_data, last_week_start, last_week_end)

        for q in questions_data:
            # Current week avg for this question
            q_current = [a["value"] for a in current_answers if a.get("question_id") == q["id"] and a.get("value") is not None]
            current_avg = sum(q_current) / len(q_current) if q_current else None

            # Last week avg for this question
            q_last = [a["value"] for a in last_answers if a.get("question_id") == q["id"] and a.get("value") is not None]
            last_avg = sum(q_last) / len(q_last) if q_last else None

            if current_avg is not None and last_avg is not None:
                delta = current_avg - last_avg
                delta_str = _format_delta(delta)
                delta_c = _delta_color(delta)
                was_str = f"Было {last_avg:.1f}"
            elif current_avg is not None:
                delta = 0.0
                delta_str = _format_delta(delta)
                delta_c = COLOR_TEXT_PLACEHOLDER
                was_str = ""
            else:
                continue

            row = ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Column(
                            controls=[
                                ft.Text(q["text"], size=14, weight=ft.FontWeight.W_500, color=COLOR_TEXT_PRIMARY),
                                ft.Text(was_str, size=12, color=COLOR_TEXT_PLACEHOLDER) if was_str else ft.Container(),
                            ],
                            expand=True,
                            spacing=2,
                        ),
                        ft.Text(delta_str, size=16, weight=ft.FontWeight.W_700, color=delta_c, width=40, text_align=ft.TextAlign.RIGHT),
                    ],
                    spacing=12,
                ),
                bgcolor=BG_COLOR_CARD,
                padding=ft.Padding.symmetric(horizontal=16, vertical=14),
                margin=ft.Margin.only(bottom=2),
            )
            category_changes.controls.append(row)

        _update()

    # Header
    header = ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text("Динамика", size=22, weight=ft.FontWeight.W_600, color=COLOR_TEXT_PRIMARY),
                    ],
                    spacing=4,
                    wrap=True,
                ),
                ft.Row(
                    controls=[
                        subtitle_text,
                    ],
                    spacing=4,
                ),
            ],
            spacing=4,
            wrap=True,
        ),
        padding=ft.Padding.only(left=24, right=24, top=8, bottom=8),
        expand=False,
    )

    # Chart card
    chart_card = ft.Container(
        content=ft.Column(
            controls=[chart_title, chart_weeks],
            spacing=12,
        ),
        bgcolor=BG_COLOR_CARD,
        padding=ft.Padding.symmetric(vertical=20, horizontal=16),
        margin=ft.Margin.only(top=4, bottom=2),
    )

    scrollable_content = ft.Column(
        controls=[chart_card, category_changes],
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )

    return header, scrollable_content, _render


def students_page(
    students_data: list[dict],
    answers_data: list[dict],
    questions_data: list[dict],
    page: ft.Page,
    api: ApiService,
):
    """Страница списка учеников. Получает готовые данные для рендера."""
    page.title = PAGE_TITLE
    page.padding = 0
    page.window_width = WINDOW_WIDTH
    page.window_height = WINDOW_HEIGHT

    subtitle_text = ft.Text(
        SUBTITLE_PLACEHOLDER,
        size=13,
        color=COLOR_TEXT_SECONDARY,
    )

    student_list_inner = ft.Column(
        controls=[],
        spacing=2,
    )

    def _update():
        page.update()

    def _show_snackbar(message: str, error: bool = False):
        snackbar = ft.SnackBar(
            content=ft.Text(message),
            bgcolor=BG_SNACKBAR_ERROR if error else BG_SNACKBAR_SUCCESS,
        )
        page.snack_bar = snackbar
        page.snack_bar.open = True
        _update()

    def _close_dialog():
        if page.overlay:
            for c in list(page.overlay):
                if isinstance(c, ft.AlertDialog):
                    c.open = False
            page.update()

    def _on_add_click(e):
        name_field = ft.TextField(
            label="Имя ученика",
            hint_text="Введите ФИО",
            expand=True,
            autofocus=True,
        )

        dialog = ft.AlertDialog(
            title=ft.Text("Добавить ученика"),
            content=ft.Column(
                controls=[name_field],
                tight=True,
                expand=True,
            ),
            actions=[
                ft.TextButton("Отмена", on_click=lambda ie: setattr(dialog, "open", False) or page.update()),
                ft.Button(
                    "Добавить",
                    bgcolor=COLOR_TEXT_PURPLE,
                    color=COLOR_TEXT_WHITE,
                    data=name_field,
                    on_click=lambda ie: page.run_task(_create_student, ie.control.data.value),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            open=True,
        )

        page.overlay.append(dialog)
        page.update()

    async def _create_student(name: str):
        if not name or not name.strip():
            _show_snackbar("Введите имя ученика", error=True)
            return

        try:
            student = await api.create_student(name.strip())
            _close_dialog()
            await _load_data()
            _show_snackbar(f"Ученик {student['name']} добавлен")
        except httpx.HTTPStatusError as ex:
            _show_snackbar(f"Ошибка: {ex.response.status_code}", error=True)
        except Exception as ex:
            _show_snackbar("Ошибка подключения к серверу", error=True)

    async def _load_data():
        """Перезагрузить данные и перерисовать список."""
        try:
            nonlocal students_data, answers_data, questions_data
            students_data, answers_data, questions_data = await asyncio.gather(
                api.get_students(),
                api.get_answers(),
                api.get_questions(),
            )
            _render_student_list()
        except Exception as ex:
            _show_snackbar(f"Ошибка загрузки данных: {ex}", error=True)

    def _render_student_list():
        answers_map: dict[int, dict[int, int]] = {}
        last_answer_time: dict[int, str] = {}
        for ans in answers_data:
            sid = ans["student_id"]
            if sid not in answers_map:
                answers_map[sid] = {}
            answers_map[sid][ans["question_id"]] = ans["value"]
            ts = ans.get("created_at")
            if ts and ts > last_answer_time.get(sid, ""):
                last_answer_time[sid] = ts

        def sort_key(student):
            has_answers = any(
                a is not None
                for a in _get_last_answers(student["id"], answers_map)
            )
            return (not has_answers, student["name"])

        sorted_students = sorted(students_data, key=sort_key)

        student_list_inner.controls.clear()

        for student in sorted_students:
            last_answers = _get_last_answers(student["id"], answers_map)
            last_time = last_answer_time.get(student["id"])
            row = _create_student_row(student, last_answers, last_time)
            student_list_inner.controls.append(row)

        students_with_answers = sum(
            1 for s in students_data
            if any(a is not None for a in _get_last_answers(s["id"], answers_map))
        )
        subtitle_text.value = (
            f"Последние ответы · {students_with_answers} из {len(students_data)} учеников"
        )

        _update()

    def _get_last_answers(student_id: int, answers_map: dict) -> list[int | None]:
        student_answers = answers_map.get(student_id, {})
        result = []
        for q in sorted(questions_data, key=lambda x: x["id"]):
            result.append(student_answers.get(q["id"]))
        return result[:5]

    def _create_student_row(student: dict, last_answers: list[int | None], last_time: str | None) -> ft.Container:
        has_answers = any(a is not None for a in last_answers)
        initials = get_initials(student["name"])

        avatar = ft.Container(
            content=ft.Text(initials, size=12, weight=ft.FontWeight.W_600, color=get_avatar_color(has_answers)),
            width=36,
            height=36,
            bgcolor=get_avatar_bg(has_answers),
            border_radius=18,
            alignment=ft.alignment.Alignment(0, 0),
        )

        name_text = ft.Text(student["name"], size=14, weight=ft.FontWeight.W_400, color=COLOR_TEXT_PRIMARY)
        code_text = ft.Text(
            f"{student['code']}{f'  •  {format_last_answer(last_time).strip()}' if last_time else ''}",
            size=11,
            weight=ft.FontWeight.W_400,
            color=COLOR_TEXT_SECONDARY,
        )
        student_info = ft.Column(controls=[name_text, code_text], spacing=2, height=33, width=175)

        left_block = ft.Row(
            controls=[avatar, student_info],
            spacing=10,
        )

        answers_controls = [get_answer_circle(a) for a in last_answers]
        right_block = ft.Row(
            controls=answers_controls,
            spacing=4,
        )

        delete_menu = ft.PopupMenuButton(
            icon=ft.Icon(ft.icons.Icons.MORE_VERT, size=18, color=COLOR_TEXT_SECONDARY),
            items=[
                ft.PopupMenuItem(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.icons.Icons.DELETE_OUTLINE, size=18, color=COLOR_TEXT_RED),
                            ft.Text("Удалить", size=13, color=COLOR_TEXT_RED),
                        ],
                        spacing=8,
                    ),
                    on_click=lambda e, s=student: _show_delete_dialog(s),
                ),
            ],
        )

        right_block.controls.append(delete_menu)

        return ft.Container(
            content=ft.Row(
                controls=[left_block, right_block],
                spacing=10,
                expand=True,
            ),
            bgcolor=BG_COLOR_CARD,
            border=ft.border.Border.all(0, BG_BORDER),
            margin=ft.Margin.only(bottom=2),
            padding=ft.Padding.symmetric(horizontal=12, vertical=10),
        )

    def _show_delete_dialog(student: dict):
        dialog = ft.AlertDialog(
            title=ft.Text("Удалить ученика"),
            content=ft.Text(f"Вы уверены, что хотите удалить {student['name']}?"),
            actions=[
                ft.TextButton("Отмена", on_click=lambda ie: page.overlay.remove(dialog) or page.update()),
                ft.Button(
                    "Удалить",
                    bgcolor=COLOR_TEXT_RED,
                    color=COLOR_TEXT_WHITE,
                    on_click=lambda ie: page.run_task(_confirm_delete, student),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            open=True,
        )

        page.overlay.append(dialog)
        page.update()

    async def _confirm_delete(student: dict):
        _close_dialog()
        try:
            await api.delete_student(student["id"])
            await _load_data()
            _show_snackbar(f"Ученик {student['name']} удалён")
        except Exception as ex:
            _show_snackbar(f"Ошибка удаления: {ex}", error=True)

    def _on_refresh_click(e):
        page.run_task(_load_data)

    header = ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text("Ученики", size=22, weight=ft.FontWeight.W_600, color=COLOR_TEXT_PRIMARY),
                    ],
                    spacing=4,
                    wrap=True,
                ),
                ft.Row(
                    controls=[
                        subtitle_text,
                        ft.IconButton(
                            icon=ft.icons.Icons.REFRESH,
                            icon_size=20,
                            on_click=_on_refresh_click,
                        ),
                    ],
                    spacing=4,
                ),
            ],
            spacing=4,
            wrap=True,
        ),
        padding=ft.Padding.only(left=24, right=24, top=8, bottom=8),
        expand=False,
    )

    add_button = ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(ft.icons.Icons.ADD, size=18, color=COLOR_TEXT_WHITE),
                ft.Text("Добавить ученика", size=15, weight=ft.FontWeight.W_600, color=COLOR_TEXT_WHITE),
            ],
            spacing=8,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        bgcolor=COLOR_TEXT_PURPLE,
        padding=ft.Padding.symmetric(vertical=14, horizontal=20),
        margin=ft.Margin.only(top=4, bottom=4),
        on_click=_on_add_click,
        expand=False,
    )

    student_list_container = ft.Container(
        content=student_list_inner,
        bgcolor=BG_COLOR_CARD,
        margin=ft.Margin.only(top=2),
        padding=ft.Padding.symmetric(horizontal=2),
        expand=True,
    )

    scrollable_list = ft.Column(
        controls=[student_list_inner],
        margin=ft.Margin.only(top=2),
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )

    return header, add_button, scrollable_list, _load_data, _render_student_list


# --- Нижняя навигация ---


def bottom_nav(on_tab_change=None) -> ft.Container:
    """Нижняя навигация."""
    nav_items = [
        ("ОБЗОР", 0),
        ("ДИНАМИКА", 1),
        ("УЧЕНИКИ", 2),
    ]

    _current_tab = [0]  # default to overview

    def _create_tab_btn(label, tab_index, is_active):
        btn = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(
                        label,
                        size=10,
                        weight=ft.FontWeight.W_600,
                        color=COLOR_TEXT_WHITE if is_active else COLOR_TEXT_TERTIARY,
                    )
                ],
                spacing=4,
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            expand=True,
            bgcolor=BG_NAV_ACTIVE if is_active else BG_NAV_INACTIVE,
            alignment=ft.alignment.Alignment(0, 0),
            on_click=lambda e, idx=tab_index: _on_tab_click(idx),
        )
        return btn

    def _on_tab_click(tab_index):
        _current_tab[0] = tab_index
        # Update all button colors
        for i, (label, _) in enumerate(nav_items):
            btn = nav_row.controls[i]
            btn.bgcolor = BG_NAV_ACTIVE if i == tab_index else BG_NAV_INACTIVE
            btn.content.controls[0].color = COLOR_TEXT_WHITE if i == tab_index else COLOR_TEXT_TERTIARY
        if on_tab_change:
            on_tab_change(tab_index)

    nav_row = ft.Row(
        controls=[
            _create_tab_btn(label, idx, idx == 0)
            for idx, (label, _) in enumerate(nav_items)
        ],
        spacing=4,
        alignment=ft.MainAxisAlignment.START,
    )

    return ft.Container(
        content=nav_row,
        width=float("inf"),
        height=NAV_HEIGHT,
        expand=False,
        bgcolor=BG_NAV_CONTAINER,
        border=ft.border.Border.only(bottom=ft.border.BorderSide(1, BG_BORDER)),
    )
