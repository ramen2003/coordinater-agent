from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    coordinator_internal_api_key: str = ""
    hrmony_backend_url: str = "http://localhost:3001"
    webhook_base_url: str = "http://localhost:8001"
    google_client_id: str = ""
    google_client_secret: str = ""
    redis_url: str = "redis://localhost:6379"
    token_ttl_hours: int = 72
    log_level: str = "INFO"

    # Deprecated — emails are now sent via NestJS (/internal/email/send).
    # These fields are kept so existing .env files don't break on startup.
    brevo_api_key: str | None = None
    brevo_sender_email: str | None = None
    brevo_sender_name: str | None = None

    class Config:
        env_file = ".env"


settings = Settings()
