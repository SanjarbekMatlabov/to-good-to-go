from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    SECRET_KEY: str = "your-secret-key-here"  
    ALGORITHM: str = "HS256" 

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )

settings = Settings()