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


class StudentsPage(ft.Column):
    """Страница списка учеников."""

    def __init__(self, api: ApiService, root_page: ft.Page):
        super().__init__()
        self.api = api
        self._pg = root_page
        self.students_data: list[dict] = []
        self.questions_data: list[dict] = []
        self.answers_data: list[dict] = []

        self.expand = False
        self.spacing = 0

        self.subtitle_text = ft.Text(
            "Последние ответы · загрузка...",
            size=13,
            color="#6D6C6A",
        )

        self.student_list_inner = ft.Column(
            controls=[],
            spacing=2,
        )

        self.header = ft.Container(
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
                        align=ft.CrossAxisAlignment.CENTER,
                        wrap=True,
                    ),
                    self.subtitle_text,
                ],
                spacing=4,
                wrap=True,
            ),
            padding=ft.Padding.only(left=24, right=24, top=8, bottom=8),
        )

        self.add_button = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.icons.Icons.ADD, size=18, color="#FFFFFF"),
                    ft.Text("Добавить ученика", size=15, weight=ft.FontWeight.W_600, color="#FFFFFF"),
                ],
                spacing=8,
                align=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor="#5A3D8A",
            padding=ft.Padding.symmetric(vertical=14, horizontal=20),
            margin=ft.Margin.only(left=2, right=2, top=4, bottom=4),
            on_click=self._on_add_click,
        )

        self.student_list_container = ft.Container(
            content=self.student_list_inner,
            bgcolor="white",
            margin=ft.Margin.only(top=2),
            padding=ft.Padding.symmetric(horizontal=2),
        )

        self.controls = [self.header, self.add_button, self.student_list_container]

    def _update(self):
        self._pg.update()

    def _show_snackbar(self, message: str, error: bool = False):
        snackbar = ft.SnackBar(
            content=ft.Text(message),
            bgcolor="#A4442A" if error else "#2F6B47",
        )
        self._pg.snack_bar = snackbar
        self._pg.snack_bar.open = True
        self._update()

    def _on_add_click(self, e):
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
                ft.TextButton("Отмена", on_click=self._close_dialog),
                ft.ElevatedButton(
                    "Добавить",
                    bgcolor="#5A3D8A",
                    color="#FFFFFF",
                    on_click=lambda _: self._create_student(name_field.value),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        self._pg.dialog = dialog
        dialog.open = True
        self._update()
        name_field.focus()

    def _close_dialog(self):
        if self._pg.dialog:
            self._pg.dialog.open = False
            self._update()

    async def _create_student(self, name: str):
        if not name or not name.strip():
            self._show_snackbar("Введите имя ученика", error=True)
            return

        try:
            student = await self.api.create_student(name.strip())
            self._close_dialog()
            await self._load_data()
            self._show_snackbar(f"Ученик {student['name']} добавлен")
        except httpx.HTTPStatusError as ex:
            self._show_snackbar(f"Ошибка: {ex.response.status_code}", error=True)
        except Exception as ex:
            self._show_snackbar(f"Ошибка подключения к серверу", error=True)

    async def _load_data(self):
        try:
            students, answers, questions = await asyncio.gather(
                self.api.get_students(),
                self.api.get_answers(),
                self.api.get_questions(),
            )
            print(f"Loaded: {len(students)} students, {len(answers)} answers, {len(questions)} questions")
            self.students_data = students
            self.answers_data = answers
            self.questions_data = questions
            self._render_student_list()
        except Exception as ex:
            self._show_snackbar(f"Ошибка загрузки данных: {ex}", error=True)

    def _render_student_list(self):
        answers_map: dict[int, dict[int, int]] = {}
        for ans in self.answers_data:
            sid = ans["student_id"]
            if sid not in answers_map:
                answers_map[sid] = {}
            answers_map[sid][ans["question_id"]] = ans["value"]

        def sort_key(student):
            has_answers = any(
                a is not None
                for a in self._get_last_answers(student["id"], answers_map)
            )
            return (not has_answers, student["name"])

        sorted_students = sorted(self.students_data, key=sort_key)

        self.student_list_inner.controls.clear()
        print(f"Rendering {len(sorted_students)} students")

        for student in sorted_students:
            last_answers = self._get_last_answers(student["id"], answers_map)
            row = self._create_student_row(student, last_answers)
            self.student_list_inner.controls.append(row)

        students_with_answers = sum(
            1 for s in self.students_data
            if any(a is not None for a in self._get_last_answers(s["id"], answers_map))
        )
        self.subtitle_text.value = (
            f"Последние ответы · {students_with_answers} из {len(self.students_data)} учеников"
        )

        self._update()

    def _get_last_answers(self, student_id: int, answers_map: dict) -> list[int | None]:
        student_answers = answers_map.get(student_id, {})
        result = []
        for q in sorted(self.questions_data, key=lambda x: x["id"]):
            result.append(student_answers.get(q["id"]))
        return result[:5]

    def _create_student_row(self, student: dict, last_answers: list[int | None]) -> ft.Container:
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
            align=ft.CrossAxisAlignment.CENTER,
        )

        answers_controls = [get_answer_circle(a) for a in last_answers]
        right_block = ft.Row(
            controls=answers_controls,
            spacing=4,
            align=ft.CrossAxisAlignment.CENTER,
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
                        align=ft.CrossAxisAlignment.CENTER,
                    ),
                    on_click=lambda e, s=student: self._show_delete_dialog(s),
                ),
            ],
        )

        right_block.controls.append(delete_menu)

        return ft.Container(
            content=ft.Row(
                controls=[left_block, right_block],
                spacing=10,
                align=ft.CrossAxisAlignment.CENTER,
                expand=True,
            ),
            bgcolor="white",
            border=ft.border.Border.all(0, "#E5E4E1"),
            margin=ft.Margin.only(bottom=2),
            padding=ft.Padding.symmetric(horizontal=12, vertical=10),
        )

    def _show_delete_dialog(self, student: dict):
        dialog = ft.AlertDialog(
            title=ft.Text("Удалить ученика"),
            content=ft.Text(f"Вы уверены, что хотите удалить {student['name']}?"),
            actions=[
                ft.TextButton("Отмена", on_click=self._close_dialog),
                ft.ElevatedButton(
                    "Удалить",
                    bgcolor="#A4442A",
                    color="#FFFFFF",
                    on_click=lambda _: self._confirm_delete(student),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        self._pg.dialog = dialog
        dialog.open = True
        self._update()

    async def _confirm_delete(self, student: dict):
        self._close_dialog()
        try:
            await self.api.delete_student(student["id"])
            await self._load_data()
            self._show_snackbar(f"Ученик {student['name']} удалён")
        except Exception as ex:
            self._show_snackbar(f"Ошибка удаления: {ex}", error=True)


class BottomNav(ft.Container):
    """Нижняя навигация."""

    def __init__(self):
        super().__init__()

        self.width = float("inf")
        self.height = 60
        self.expand = False
        self.bgcolor = "#F5F4F1"
        self.border = ft.border.Border.only(bottom=ft.border.BorderSide(1, "#E5E4E1"))

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

        self.content = ft.Row(
            controls=controls,
            spacing=4,
            alignment=ft.MainAxisAlignment.START,
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

    students_page = StudentsPage(api, page)
    await students_page._load_data()

    bottom_nav = BottomNav()

    page.controls.append(
        ft.Column(
            controls=[students_page, bottom_nav],
            spacing=0,
            alignment=ft.MainAxisAlignment.START,
        )
    )

    page.update()

    try:
        import asyncio
        await asyncio.Future()
    finally:
        await api.close()


if __name__ == "__main__":
    ft.run(main)