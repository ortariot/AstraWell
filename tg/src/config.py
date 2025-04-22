from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict
import pathlib

ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent
ENV_PATH = ROOT_DIR / ".env"

class Bot(BaseModel):
    TOKEN: str

class MTS_(BaseModel):
    TOKEN: str
    BASE_URL = 'https://tables.mws.ru'

class Config(BaseSettings):
    BOT: Bot = None
    MTS: MTS_ = None

    model_config = SettingsConfigDict(
        env_file=ENV_PATH,
        env_ignore_empty=True,
        case_sensitive=True,
        extra="ignore",
        env_nested_delimiter="__",
    )

CFG = Config()