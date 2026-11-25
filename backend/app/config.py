"""Uygulama ayarları (.env veya ortam değişkenlerinden okunur)."""
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Afet Hasar Tespiti API"
    database_url: str = "sqlite:///./app.db"
    secret_key: str  # zorunlu: varsayılanı yok, .env.example'a bakın
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    storage_dir: Path = Path("./storage")
    max_upload_mb: int = 50
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    @field_validator("secret_key")
    @classmethod
    def secret_key_must_be_strong(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("SECRET_KEY en az 32 karakter olmalı (bkz. .env.example)")
        if v.startswith("BURAYA"):
            raise ValueError("SECRET_KEY hâlâ örnek değer; .env.example'daki komutla yeni bir anahtar üretin")
        return v

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
