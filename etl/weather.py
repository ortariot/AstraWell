import asyncio
from datetime import datetime
import json

import aiohttp

from core.settings import settings


class WeathersEtl:

    mws_tables_token = settings.mws_tables_token

    def get_probability(self, dataset: list):

        len_dataset = len(dataset)
        not_null = len_dataset - dataset.count(0)

        return not_null / len_dataset if len_dataset > 0 else 0

    async def weather_etl(
        self, location: str, preference_id: str, start_date: str, end_date: str
    ):
        try:
            geodata = await self.get_weather(
                location, preference_id, start_date, end_date
            )
        except aiohttp.client_exceptions.ConnectionTimeoutError:
            print(
                f"weather service is not available now, data for {location} not loaded :-("
            )
            geodata = None

        if geodata:
            print(f"add weather for location {location}")
            await self.load_weather(geodata)

    async def load_weather(self, data: list) -> None:

        req_url = (
            settings.mws_api_path
            + f"/fusion/v1/datasheets/{settings.mws_table_weather}/records"
        )

        headers = {
            "Authorization": self.mws_tables_token,
            "Content-Type": "application/json",
        }

        json = {
            "records": [data],
            "fieldKey": "name",
        }

        async with aiohttp.ClientSession() as session:

            try:
                response = await session.request(
                    "POST", req_url, json=json, headers=headers, timeout=5
                )
            except TimeoutError:
                print(f"timeout with api: {settings.mws_api_path} ")

    async def get_geodata(
        self, locataion: str, checkIn: str, checkOut: str | None = None
    ) -> tuple:

        if checkOut is None:
            checkOut = checkIn

        async with aiohttp.ClientSession() as session:
            req_url = "https://engine.hotellook.com/api/v2/cache.json?"

            req_params = {
                "location": locataion,
                "checkIn": checkIn,
                "checkOut": checkOut,
                "currency": "rub",
                "limit": 1,
            }
            try:
                response = await session.request(
                    "GET", req_url, params=req_params, timeout=5
                )
            except TimeoutError:
                response = None
                print(
                    f"timeout with api: engine.hotellook with operation cache.json"
                )

            try:
                body = await response.json()
            except (
                json.decoder.JSONDecodeError,
                aiohttp.client_exceptions.ContentTypeError,
            ) as e:
                body = None
                print(f"error - {e}")

            if body:
                location = body[0]["location"]

                return (
                    location["country"],
                    location["name"],
                    location["geo"]["lat"],
                    location["geo"]["lon"],
                )

            else:
                return (None, None, None, None)

    async def get_weather(
        self,
        location: str,
        preference_id: str,
        start_date: str,
        end_date: str | None = None,
    ) -> dict:

        country, city, latitude, longitude = await self.get_geodata(
            location, start_date, end_date
        )

        if (
            country is None
            or city is None
            or latitude is None
            or longitude is None
        ):
            return None

        temp = []
        snowfall = []
        rain = []

        async with aiohttp.ClientSession() as session:
            req_url = "https://archive-api.open-meteo.com/v1/archive"

            start_date_dt = datetime.fromisoformat(start_date)
            end_date_dt = (
                datetime.fromisoformat(end_date)
                if end_date
                else datetime.fromisoformat(start_date)
            )

            current_year = datetime.now().date().year

            cnt = 1
            while True:
                new_start = start_date_dt.date().replace(
                    year=current_year - cnt
                )
                new_end = end_date_dt.date().replace(year=current_year - cnt)

                cnt += 1

                if cnt > 6:
                    break

                params = {
                    "latitude": latitude,
                    "longitude": longitude,
                    "start_date": str(new_start),
                    "end_date": str(new_end),
                    "daily": [
                        "rain_sum",
                        "temperature_2m_mean",
                        "snowfall_sum",
                    ],
                }

                response = await session.request("GET", req_url, params=params)

                try:
                    body = await response.json()
                except (
                    json.decoder.JSONDecodeError,
                    aiohttp.client_exceptions.ContentTypeError,
                ) as e:
                    body = None
                    print(f"error - {e}")

                if body:
                    try:
                        temp.extend(body["daily"]["temperature_2m_mean"])
                        snowfall.extend(body["daily"]["snowfall_sum"])
                        rain.extend(body["daily"]["rain_sum"])
                    except KeyError:
                        print(f"not faind data for {location}")

            return {
                "fields": {
                    "latitude": str(latitude),
                    "longitude": str(longitude),
                    "start_date": start_date,
                    "end_date": end_date,
                    "avg_temp": (
                        str(round(sum(temp) / len(temp), 2))
                        if len(temp) > 0
                        else "0"
                    ),
                    "rain_probability": round(self.get_probability(rain), 2),
                    "rain_sum": (
                        str(round(sum(rain) / len(rain), 2))
                        if len(rain) > 0
                        else "0"
                    ),
                    "snowfall_probability": round(
                        self.get_probability(snowfall), 2
                    ),
                    "snowfall_sum": (
                        str(round(sum(snowfall) / len(snowfall), 2))
                        if len(snowfall) > 0
                        else "0"
                    ),
                    "preference": [preference_id],
                    "country": country,
                    "city": city,
                    "iata": location,
                }
            }


if __name__ == "__main__":
    weathers = WeathersEtl()

    res = asyncio.run(
        weathers.weather_etl(
            "OVB", "recaTxlzLUiY0", "2025-05-03", "2025-05-15"
        )
    )

    # pprint(res)

    # asyncio.run(weathers.get_geodata("IST", "2025-05-03", "2025-05-15"))
