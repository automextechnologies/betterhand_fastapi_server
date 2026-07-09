import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    MONGODB_URL: str = Field(default="mongodb://localhost:27017")
    DB_NAME: str = Field(default="betterhand_db")
    
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    USE_REDIS: bool = Field(default=False)
    
    FIREBASE_CREDENTIALS_PATH: str = Field(default="firebase-credentials.json")
    FIREBASE_CREDENTIALS_JSON: str | None = Field(default=None)
    ORS_API_KEY: str = Field(default="your-ors-api-key-here")
    
    EMAIL_HOST_USER: str = Field(default="your-email@gmail.com")
    EMAIL_HOST_PASSWORD: str = Field(default="your-app-password")
    
    DONOR_COOLDOWN_DAYS: int = Field(default=90)
    
    JWT_SECRET_KEY: str = Field(default="supersecretkeyforbetterhandfastapibackenddevelopment123!")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=1440)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=30)
    
    FRONTEND_URL: str = Field(default="http://localhost:5173")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
