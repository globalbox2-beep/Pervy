from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import Optional


class Settings(BaseSettings):
    bitrix24_webhook_url: str
    poll_interval_seconds: int = 60
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"
    deal_stages_filter: Optional[str] = None
    deal_assigned_filter: Optional[str] = None

    # Telegram
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    # События для уведомлений: created, updated, removed (через запятую)
    telegram_notify_events: Optional[str] = "created,updated,removed"

    @property
    def telegram_enabled(self) -> bool:
        return bool(self.telegram_bot_token and self.telegram_chat_id)

    @property
    def telegram_events(self) -> list[str]:
        if not self.telegram_notify_events:
            return ["created", "updated", "removed"]
        return [e.strip() for e in self.telegram_notify_events.split(",") if e.strip()]

    @field_validator("bitrix24_webhook_url")
    @classmethod
    def validate_webhook_url(cls, v: str) -> str:
        if not v.startswith("http"):
            raise ValueError("BITRIX24_WEBHOOK_URL must be a valid HTTP/HTTPS URL")
        return v.rstrip("/")

    @property
    def stages_filter(self) -> list[str]:
        if not self.deal_stages_filter:
            return []
        return [s.strip() for s in self.deal_stages_filter.split(",") if s.strip()]

    @property
    def assigned_filter(self) -> list[str]:
        if not self.deal_assigned_filter:
            return []
        return [s.strip() for s in self.deal_assigned_filter.split(",") if s.strip()]

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
