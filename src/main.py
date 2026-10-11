"""Точка входа приложения PulseteAdmin."""

import asyncio

import flet as ft

from src.api import ApiService
from src.constants import (
    APP_TITLE,
    BG_COLOR_CARD,
    BG_NAV_ACTIVE,
    BG_NAV_INACTIVE,
    COLOR_TEXT_TERTIARY,
    COLOR_TEXT_WHITE,
    FONT_FAMILY,
)
from src.ui import students_page, overview_page, dynamic_page


async def main(page: ft.Page):
    """Точка входа приложения."""
    page.title = APP_TITLE
    page.theme_mode = ft.ThemeMode.LIGHT
    page.theme = ft.Theme(font_family=FONT_FAMILY)
    page.bg_color = BG_COLOR_CARD
    page.horizontal_alignment = ft.CrossAxisAlignment.STRETCH
    page.scroll = None

    api = ApiService()

    students_data = await api.get_students()
    answers_data = await api.get_answers()
    questions_data = await api.get_questions()
    print(f"Loaded: {len(students_data)} students, {len(answers_data)} answers, {len(questions_data)} questions")

    # Create all pages
    header_overview, scrollable_overview, render_overview = overview_page(
        students_data, answers_data, questions_data, page, api
    )

    header_dynamic, scrollable_dynamic, render_dynamic = dynamic_page(
        students_data, answers_data, questions_data, page, api
    )

    header_students, add_button, scrollable_students, load_data, render_student_list = students_page(
        students_data, answers_data, questions_data, page, api
    )

    # Nav buttons
    _nav_buttons = []

    def _create_nav_button(label, tab_idx):
        btn = ft.Container(
            content=ft.Column(
                controls=[ft.Text(label, size=10, weight=ft.FontWeight.W_600, color=COLOR_TEXT_TERTIARY)],
                spacing=4,
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            expand=True,
            bgcolor=BG_NAV_INACTIVE,
            alignment=ft.alignment.Alignment(0, 0),
            on_click=lambda e, idx=tab_idx: _switch_tab(idx),
        )
        _nav_buttons.append(btn)
        return btn

    # Bottom nav
    _bottom = ft.Container(
        content=ft.Row(
            controls=[
                _create_nav_button("ОБЗОР", 0),
                _create_nav_button("ДИНАМИКА", 1),
                _create_nav_button("УЧЕНИКИ", 2),
            ],
            spacing=4,
            alignment=ft.MainAxisAlignment.START,
        ),
        width=float("inf"),
        height=60,
        expand=False,
        bgcolor="#F5F4F1",
        border=ft.border.Border.only(bottom=ft.border.BorderSide(1, "#E5E4E1")),
    )

    # Content area - will be swapped
    _content = ft.Column(
        controls=[],
        expand=True,
        scroll=ft.ScrollMode.AUTO,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
    )

    # Main layout - Column with content + fixed bottom
    _main = ft.Column(
        controls=[
            _content,
            _bottom,
        ],
        expand=True,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        margin=ft.Margin(left=100, right=100),
    )

    page.controls.append(_main)

    def _switch_tab(tab_index):
        if tab_index == 0:
            _content.controls = [header_overview, scrollable_overview]
            render_overview()
        elif tab_index == 1:
            _content.controls = [header_dynamic, scrollable_dynamic]
            render_dynamic()
        elif tab_index == 2:
            _content.controls = [header_students, add_button, scrollable_students]
            render_student_list()

        # Update nav colors
        for i, btn in enumerate(_nav_buttons):
            is_active = i == tab_index
            btn.bgcolor = BG_NAV_ACTIVE if is_active else BG_NAV_INACTIVE
            btn.content.controls[0].color = COLOR_TEXT_WHITE if is_active else COLOR_TEXT_TERTIARY

        page.update()

    # Show overview by default
    _switch_tab(0)

    try:
        await asyncio.Future()
    finally:
        await api.close()


if __name__ == "__main__":
    ft.run(main)
