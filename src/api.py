"""Сервис для взаимодействия с PulseBackend API."""

import httpx

from src.constants import API_BASE_URL


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
        response = await self.client.delete(f"/students?student_id={student_id}")
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
