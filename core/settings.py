from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    mws_api_path: str = "https://tables.mws.ru"
    mws_tables_token: str = "test"
    mws_table_ideas: str = "dstBuL8jPgynbJrEpD"
    mws_table_preferences: str = "dstThkcrNzwYXtJYrA"
    mws_table_weather: str = "dst7K9VFJa4MwzrTgi"
    mws_table_hotels: str = "dstNBH9m70fMYr5mdX"
    mws_table_flights: str = "dstcm0K692wmmJX2Pq"
    mws_table_users: str = "dstGLhT5cQ14QWYrvP"
    mws_table_airports: str = "dstrTgnHfh2WLuls4X"
    
    aviasales_token: str = "test"
    deepsek_key: str = "test"

    redis_host: str = '127.0.0.1'
    redis_port: int = 6379
    redis_password: str = 'REDIS_PASSWORD'


settings = BaseConfig()


if __name__ == "__main__":

    print(settings)
