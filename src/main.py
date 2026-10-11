"""Точка входа приложения PulseteAdmin."""

import asyncio

import flet as ft

from src.api import ApiService
from src.constants import APP_TITLE, BG_COLOR_CARD, FONT_FAMILY
from src.ui import bottom_nav, students_page


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

    header, add_button, scrollable_list, load_data, render_student_list = students_page(
        students_data, answers_data, questions_data, page, api
    )

    bottom = bottom_nav()

    main_column = ft.Column(
        controls=[header, add_button, scrollable_list, bottom],
        spacing=0,
        alignment=ft.MainAxisAlignment.START,
        expand=True,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
    )

    page.controls.append(main_column)

    render_student_list()

    try:
        await asyncio.Future()
    finally:
        await api.close()


if __name__ == "__main__":
    ft.run(main)
