from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@db:5432/infilect"

    # App
    APP_NAME: str = "Infilect Data Ingestion API"
    DEBUG: bool = False

    # Ingestion
    CSV_CHUNK_SIZE: int = 2000          # rows per processing chunk
    MAX_UPLOAD_SIZE_MB: int = 200       # hard limit for uploads

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
