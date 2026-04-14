from typing import Literal

from pydantic import BaseModel, Field, field_validator


ParticipationFormat = Literal["Базовый", "Стандарт", "VIP"]
PracticeExperience = Literal["есть опыт", "немного", "нет опыта"]
MessageRole = Literal["user", "assistant"]


class RetreatTicket(BaseModel):
    name: str | None = None
    request: str | None = None
    practice_experience: PracticeExperience | None = None
    participation_format: ParticipationFormat | None = None
    retreat_dates: str | None = None
    contact: str | None = None
    referral_source: str | None = None

    @field_validator("name", "request", "retreat_dates", "contact", "referral_source")
    @classmethod
    def clean_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = " ".join(value.split()).strip()
        return cleaned or None

    def merge(self, other: "RetreatTicket") -> None:
        for field_name, value in other.model_dump().items():
            if value not in (None, ""):
                setattr(self, field_name, value)

    def is_complete(self) -> bool:
        return all(
            [
                self.name,
                self.request,
                self.practice_experience,
                self.participation_format,
                self.retreat_dates,
                self.contact,
                self.referral_source,
            ]
        )


class DialogueMessage(BaseModel):
    role: MessageRole
    text: str = Field(min_length=1)

    @field_validator("text")
    @classmethod
    def clean_text(cls, value: str) -> str:
        cleaned = " ".join(value.split()).strip()
        if not cleaned:
            raise ValueError("Dialogue message cannot be empty")
        return cleaned


class AssistantTurn(BaseModel):
    reply: str = Field(min_length=1)
    extracted_ticket: RetreatTicket = Field(default_factory=RetreatTicket)
    ready_to_submit: bool = False


class RetreatSession(BaseModel):
    user_id: int
    chat_id: int
    telegram_username: str | None = None
    telegram_first_name: str | None = None
    started: bool = False
    submitted: bool = False
    ticket: RetreatTicket = Field(default_factory=RetreatTicket)
    history: list[DialogueMessage] = Field(default_factory=list)

    def add_user_message(self, text: str) -> None:
        self._append_history("user", text)

    def add_assistant_message(self, text: str) -> None:
        self._append_history("assistant", text)

    def recent_history(self, limit: int = 8) -> list[DialogueMessage]:
        return list(self.history[-limit:])

    @property
    def last_assistant_message(self) -> str | None:
        for message in reversed(self.history):
            if message.role == "assistant":
                return message.text
        return None

    def reset(self) -> None:
        self.started = False
        self.submitted = False
        self.ticket = RetreatTicket()
        self.history = []

    def _append_history(self, role: MessageRole, text: str) -> None:
        self.history.append(DialogueMessage(role=role, text=text))
        if len(self.history) > 20:
            self.history = self.history[-20:]
