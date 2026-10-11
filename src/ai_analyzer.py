"""Сервис для анализа данных через GigaChat API."""

from gigachat import GigaChat


class GigaChatService:
    """Сервис для работы с GigaChat API."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._client: GigaChat | None = None

    def _get_client(self) -> GigaChat:
        """Лениво создаёт клиент GigaChat."""
        if self._client is None:
            self._client = GigaChat(
                credentials=self.api_key,
                base_url="https://api.giga.chat/v1",
                verify_ssl_certs=False,
                scope="GIGACHAT_API_PERS",
                model="GigaChat-2",
            )
            self._client.get_token()
        return self._client

    async def analyze_week(
        self,
        questions: list[dict],
        answers: list[dict],
        week_label: str,
    ) -> str:
        """Анализирует ответы за неделю и возвращает заключение."""
        import asyncio

        # Формируем контекст для промпта
        questions_map = {q["id"]: q["text"] for q in questions}

        # Группируем ответы по вопросам
        answers_by_question: dict[int, list[int]] = {}
        for ans in answers:
            qid = ans["question_id"]
            val = ans.get("value")
            if val is not None:
                answers_by_question.setdefault(qid, []).append(val)

        # Считаем средние по каждому вопросу
        summary_lines = []
        for qid, qtext in questions_map.items():
            values = answers_by_question.get(qid, [])
            if values:
                avg = sum(values) / len(values)
                count = len(values)
                summary_lines.append(f"- «{qtext}»: {avg:.1f}/5 ({count} ответов)")
            else:
                summary_lines.append(f"- «{qtext}»: нет ответов")

        total_participants = len(set(a["student_id"] for a in answers))
        total_answers = len(answers)

        system_prompt = (
            "Ты — помощник классного руководителя. "
            "Ты анализируешь результаты еженедельного мониторинга эмоционального состояния школьников. "
            "Оценивания по 5-балльной шкале (5 = отлично, 3 = нормально, 1 = плохо). "
            "Дай краткий анализ (3-5 предложений): "
            "1) Общий эмоциональный климат класса. "
            "2) Проблемные зоны (вопросы с низкими баллами < 3.5). "
            "3) Сильные стороны (вопросы с высокими баллами > 4). "
            "4) Рекомендации для классного руководителя. "
            "Отвечай кратко и по делу, на русском языке. "
            "Используй markdown-форматирование для структурирования текста."
        )

        user_prompt = (
            f"Неделя: {week_label}\n"
            f"Всего ответов: {total_answers}, участников: {total_participants}\n\n"
            f"Результаты по категориям:\n"
            + "\n".join(summary_lines)
            + "\n\n"
            f"Вопросы опроса:\n"
            + "\n".join(f"{i+1}. {q['text']}" for i, q in enumerate(questions))
            + "\n\n"
            f"Дай краткий анализ за эту неделю."
        )

        client = self._get_client()

        # Запускаем в потоке, т.к. SDK синхронная
        def _chat():
            resp = client.chat.create({
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            })
            # Ответ в resp.messages[0].content[0].text
            return resp.messages[0].content[0].text

        return await asyncio.to_thread(_chat)

    async def close(self):
        if self._client:
            self._client.close()
            self._client = None
