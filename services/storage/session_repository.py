from core import RetreatSession


class InMemorySessionRepository:
    def __init__(self) -> None:
        self._sessions: dict[int, RetreatSession] = {}

    def get_or_create(
        self,
        user_id: int,
        chat_id: int,
        telegram_username: str | None,
        telegram_first_name: str | None,
    ) -> RetreatSession:
        session = self._sessions.get(user_id)
        if session is None:
            session = RetreatSession(
                user_id=user_id,
                chat_id=chat_id,
                telegram_username=telegram_username,
                telegram_first_name=telegram_first_name,
            )
            self._sessions[user_id] = session
            return session

        session.chat_id = chat_id
        session.telegram_username = telegram_username
        session.telegram_first_name = telegram_first_name
        return session

    def reset(self, user_id: int) -> None:
        if user_id in self._sessions:
            self._sessions[user_id].reset()
