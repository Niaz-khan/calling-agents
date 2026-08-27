from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Call Agent"
    app_version: str = "1.0.0"

    database_url: str

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    llm_api_key: str
    llm_model: str = "gpt-4o-mini"
    llm_base_url: str | None = None

    stt_provider: str = "openai"
    stt_model: str = "whisper-1"
    stt_language: str | None = None

    tts_provider: str = "openai"
    tts_model: str = "gpt-4o-mini-tts"
    tts_voice: str = "alloy"
    tts_format: str = "wav"

    voice_max_utterance_seconds: int = 30
    voice_heartbeat_seconds: int = 20
    voice_idle_timeout_seconds: int = 300

    telephony_provider: str = "twilio"
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""
    public_base_url: str = "http://localhost:8000"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()