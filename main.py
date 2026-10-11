"""
Приложение для классного руководителя PulseteAdmin.
Управление учениками и просмотр их ответов.
"""

import asyncio

import flet as ft
import httpx


API_BASE_URL = "http://localhost:8000"


class ApiService:
    """Сервис для взаимодействия с PulseBackend API."""

    def __init__(self):
        self.client = httpx.AsyncClient(base_url=API_BASE_URL, timeout=10.0)

    async def get_students(self) -> list[dict]:
        response = await self.client.get("/students")
        response.raise_for_status()
        return response.json()

    async def create_student(self, name: str) -> dict:
        response = await self.client.post("/students", json={"name": name})
        response.raise_for_status()
        return response.json()

    async def delete_student(self, student_id: int) -> bool:
        response = await self.client.delete(f"/students?id={student_id}")
        return response.status_code in (200, 204)

    async def get_answers(self) -> list[dict]:
        response = await self.client.get("/answers")
        response.raise_for_status()
        return response.json()

    async def get_questions(self) -> list[dict]:
        response = await self.client.get("/questions")
        response.raise_for_status()
        return response.json()

    async def close(self):
        await self.client.aclose()


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
            content=ft.Text("—", size=12, weight=ft.FontWeight.W_600, color="#B0AEA9"),
            width=26,
            height=26,
            bgcolor="#EDEDEB",
            border_radius=13,
            alignment=ft.alignment.Alignment(0, 0),
        )

    if value >= 4:
        color = "#2F6B47"
        bg_color = "#D8C8F0"
    elif value == 3:
        color = "#8A6A1F"
        bg_color = "#F7ECD0"
    else:
        color = "#A4442A"
        bg_color = "#FBE3DC"

    return ft.Container(
        content=ft.Text(str(value), size=12, weight=ft.FontWeight.W_600, color=color),
        width=26,
        height=26,
        bgcolor=bg_color,
        border_radius=13,
        alignment=ft.alignment.Alignment(0, 0),
    )


def get_avatar_bg(has_answers: bool) -> str:
    return "#D8C8F0" if has_answers else "#E8E7E4"


def get_avatar_color(has_answers: bool) -> str:
    return "#5A3D8A" if has_answers else "#8A8986"


def students_page(
        students_data: list[dict],
        answers_data: list[dict],
        questions_data: list[dict],
        page: ft.Page,
        api: ApiService,
):
    """Страница списка учеников. Получает готовые данные для рендера."""
    page.title = "Пульс класса - Админ"
    page.padding = 0
    page.window_width = 400
    page.window_height = 800

    ft.Text(
        "Test",
        size=13,
        color="#6D6C6A",
    )

    subtitle_text = ft.Text(
        "Последние ответы · загрузка...",
        size=13,
        color="#6D6C6A",
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
            bgcolor="#A4442A" if error else "#2F6B47",
        )
        page.snack_bar = snackbar
        page.snack_bar.open = True
        _update()

    def _close_dialog():
        if page.dialog:
            page.dialog.open = False
            _update()

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
                ft.TextButton("Отмена", on_click=_close_dialog),
                ft.Button(
                    "Добавить",
                    bgcolor="#5A3D8A",
                    color="#FFFFFF",
                    on_click=lambda _: asyncio.create_task(_create_student(name_field.value)),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        page.dialog = dialog
        dialog.open = True
        _update()

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
            _show_snackbar(f"Ошибка подключения к серверу", error=True)

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
        for ans in answers_data:
            sid = ans["student_id"]
            if sid not in answers_map:
                answers_map[sid] = {}
            answers_map[sid][ans["question_id"]] = ans["value"]

        def sort_key(student):
            has_answers = any(
                a is not None
                for a in _get_last_answers(student["id"], answers_map)
            )
            return (not has_answers, student["name"])

        sorted_students = sorted(students_data, key=sort_key)

        student_list_inner.controls.clear()
        print(f"Rendering {len(sorted_students)} students")

        for student in sorted_students:
            last_answers = _get_last_answers(student["id"], answers_map)
            row = _create_student_row(student, last_answers)
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

    def _create_student_row(student: dict, last_answers: list[int | None]) -> ft.Container:
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

        name_text = ft.Text(student["name"], size=14, weight=ft.FontWeight.W_400, color="#1A1918")
        code_text = ft.Text(str(student["code"]), size=11, weight=ft.FontWeight.W_400, color="#6D6C6A")
        student_info = ft.Column(controls=[name_text, code_text], spacing=2, height=33)

        left_block = ft.Row(
            controls=[avatar, student_info],
            spacing=10,
            # align=ft.CrossAxisAlignment.CENTER,
        )

        answers_controls = [get_answer_circle(a) for a in last_answers]
        right_block = ft.Row(
            controls=answers_controls,
            spacing=4,
            # align=ft.CrossAxisAlignment.CENTER,
        )

        delete_menu = ft.PopupMenuButton(
            icon=ft.Icon(ft.icons.Icons.MORE_VERT, size=18, color="#6D6C6A"),
            items=[
                ft.PopupMenuItem(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.icons.Icons.DELETE_OUTLINE, size=18, color="#A4442A"),
                            ft.Text("Удалить", size=13, color="#A4442A"),
                        ],
                        spacing=8,
                        # align=ft.CrossAxisAlignment.CENTER,
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
                # align=ft.CrossAxisAlignment.CENTER,
                expand=True,
            ),
            bgcolor="white",
            border=ft.border.Border.all(0, "#E5E4E1"),
            margin=ft.Margin.only(bottom=2),
            padding=ft.Padding.symmetric(horizontal=12, vertical=10),
        )

    def _show_delete_dialog(student: dict):
        dialog = ft.AlertDialog(
            title=ft.Text("Удалить ученика"),
            content=ft.Text(f"Вы уверены, что хотите удалить {student['name']}?"),
            actions=[
                ft.TextButton("Отмена", on_click=_close_dialog),
                ft.Button(
                    "Удалить",
                    bgcolor="#A4442A",
                    color="#FFFFFF",
                    on_click=lambda _: _confirm_delete(student),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        page.dialog = dialog
        dialog.open = True
        _update()

    async def _confirm_delete(student: dict):
        _close_dialog()
        try:
            await api.delete_student(student["id"])
            await _load_data()
            _show_snackbar(f"Ученик {student['name']} удалён")
        except Exception as ex:
            _show_snackbar(f"Ошибка удаления: {ex}", error=True)

    header = ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text("Ученики", size=22, weight=ft.FontWeight.W_600, color="#1A1918"),
                        ft.Container(
                            content=ft.Text("21 – 27 апр", size=12, weight=ft.FontWeight.W_500, color="#1A1918"),
                            bgcolor="white",
                            padding=ft.Padding.symmetric(horizontal=14, vertical=10),
                            border_radius=6,
                        ),
                    ],
                    spacing=4,
                    wrap=True,
                ),
                subtitle_text,
            ],
            spacing=4,
            wrap=True,
        ),
        padding=ft.Padding.only(left=24, right=24, top=8, bottom=8),
    )

    add_button = ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(ft.icons.Icons.ADD, size=18, color="#FFFFFF"),
                ft.Text("Добавить ученика", size=15, weight=ft.FontWeight.W_600, color="#FFFFFF"),
            ],
            spacing=8,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        bgcolor="#5A3D8A",
        padding=ft.Padding.symmetric(vertical=14, horizontal=20),
        margin=ft.Margin.only(left=2, right=2, top=4, bottom=4),
        on_click=_on_add_click,
    )

    student_list_container = ft.Container(
        content=student_list_inner,
        bgcolor="white",
        margin=ft.Margin.only(top=2),
        padding=ft.Padding.symmetric(horizontal=2),
    )

    column = ft.Column(
        controls=[
            header, add_button, student_list_container],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    return column, _load_data, _render_student_list


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
                        color="#FFFFFF" if is_active else "#A8A7A5",
                    )
                ],
                spacing=4,
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            expand=True,
            bgcolor="#5A3D8A" if is_active else "white",
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
        height=60,
        expand=False,
        bgcolor="#F5F4F1",
        border=ft.border.Border.only(bottom=ft.border.BorderSide(1, "#E5E4E1")),
    )


async def main(page: ft.Page):
    """Точка входа приложения."""
    page.title = "PulseteAdmin"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.theme = ft.Theme(font_family="Inter")
    page.bg_color = "#F5F4F1"
    page.horizontal_alignment = ft.CrossAxisAlignment.STRETCH
    page.scroll = ft.ScrollMode.ADAPTIVE

    api = ApiService()

    students_data = await api.get_students()
    answers_data = await api.get_answers()
    questions_data = await api.get_questions()
    print(f"Loaded: {len(students_data)} students, {len(answers_data)} answers, {len(questions_data)} questions")

    students_column, load_data, render_student_list = students_page(
        students_data, answers_data, questions_data, page, api
    )

    bottom = bottom_nav()

    page.controls.append(
        ft.Column(
            controls=[students_column, bottom],
            spacing=0,
            alignment=ft.MainAxisAlignment.START,
        )
    )

    render_student_list()

    try:
        import asyncio
        await asyncio.Future()
    finally:
        await api.close()


if __name__ == "__main__":
    ft.run(main)
