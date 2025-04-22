from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    mws_tables_token: str = "test"
    mts__token: str = "test"


class Config:
    FLIGHTS_TABLE_ID = "dstcm0K692wmmJX2Pq"
    HOTEL_TABLE_ID = "dstNBH9m70fMYr5mdX"
    IDEAS_TABLE_ID = "dstBuL8jPgynbJrEpD"
    PREFERENCE_TABLE_ID = "dstThkcrNzwYXtJYrA"
    WEATHER_TABLE_ID = "dst7K9VFJa4MwzrTgi"
    VARIANT_TABLE_ID = "dstuF86aY45mW9LSvm"


settings = BaseConfig()


if __name__ == "__main__":

    print(settings)
