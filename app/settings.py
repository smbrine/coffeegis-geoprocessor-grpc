from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    POSTGRES_URL: str
    DEBUG: bool = True
    REDIS_URL: str

    class Config:
        env_file = ".env.app"


settings = Settings()
