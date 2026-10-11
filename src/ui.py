"""UI-компоненты и логика экранов."""

import asyncio
from datetime import datetime, timedelta

import flet as ft

from src.api import ApiService
from src.constants import (
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
)


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


# --- Страница учеников ---


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


def bottom_nav() -> ft.Container:
    """Нижняя навигация."""
    nav_items = [
        ("ОБЗОР", False),
        ("ДИНАМИКА", False),
        ("УЧЕНИКИ", True),
    ]

    controls = []
    for label, is_active in nav_items:
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
        )
        controls.append(btn)

    return ft.Container(
        content=ft.Row(
            controls=controls,
            spacing=4,
            alignment=ft.MainAxisAlignment.START,
        ),
        width=float("inf"),
        height=NAV_HEIGHT,
        expand=False,
        bgcolor=BG_NAV_CONTAINER,
        border=ft.border.Border.only(bottom=ft.border.BorderSide(1, BG_BORDER)),
    )
