from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]

class Settings(BaseSettings):
    DATABASE_URL: str
    AZURE_STORAGE_ACCOUNT: str
    AZURE_CONTAINER_NAME: str
    AZURE_STORAGE_CONNECTION_STRING: str
    AZURE_KEY_VAULT_URL: str
    SECRET_KEY: str

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

settings = Settings()
print("Settings loaded OK")