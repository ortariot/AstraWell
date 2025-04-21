from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    mws_tables_token: str = "test"
    aviasales_token: str = "test"
    deepsek_key: str = "test"


settings = BaseConfig()


if __name__ == "__main__":

    print(settings)
