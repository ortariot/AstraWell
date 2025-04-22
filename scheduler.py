import asyncio
import time
from datetime import datetime
from pprint import pprint
import json

import aiohttp

from etl.flight import FlightEtl
from etl.hotel import HotelEtl
from etl.weather import WeathersEtl
from core.settings import settings
from db.cache import RedisRepository


class PoolRunner:

    mws_tables_token = settings.mws_tables_token
    state = set()
    cache = RedisRepository()
    flights = FlightEtl()
    hotels = HotelEtl()
    weather = WeathersEtl()

    def create_state(self, row_state: list):
        res = []
        for item in row_state:
            try:
                origin = item["fields"]["origin"]
            except KeyError:
                continue
            try:
                destination = item["fields"]["destination"]
            except KeyError:
                continue
            try:
                departure_at = str(
                    datetime.fromtimestamp(
                        (item["fields"]["departure_at"]) / 1000
                    )
                ).split(" ")[0]
            except KeyError:
                continue

            try:
                return_at = (
                    str(
                        datetime.fromtimestamp(
                            (item["fields"]["return_at"]) / 1000
                        )
                    ).split(" ")[0]
                    if item["fields"].get("return_at")
                    else "None"
                )
            except KeyError:
                continue

            preference_id = str(item["recordId"])

            res.append(
                "_".join(
                    [
                        origin,
                        destination,
                        preference_id,
                        departure_at,
                        return_at,
                    ]
                )
            )

        return res

    async def scheduler(self):

        req_url = (
            settings.mws_api_path
            + f"/fusion/v1/datasheets/{settings.mws_table_preferences}/records"
        )

        headers = {
            "Authorization": self.mws_tables_token,
            "Content-Type": "application/json",
        }

        # json_data = {
        #     "fieldKey": "name",
        # }

        params = {
            "pageSize": 1000,
            "fields": [
                "origin",
                "destination",
                "departure_at",
                "return_at",
            ],
        }
        async with aiohttp.ClientSession() as session:
            while True:

                try:
                    response = await session.request(
                        "GET",
                        req_url,
                        # json=json_data,
                        headers=headers,
                        params=params,
                        timeout=5,
                    )
                except (TimeoutError, ValueError):
                    response = None
                    print(f"timeout with api: {settings.mws_api_path}")
                if response:

                    try:
                        body = await response.json()
                    except (
                        json.decoder.JSONDecodeError,
                        aiohttp.client_exceptions.ContentTypeError,
                    ) as e:
                        body = None
                        print(f"error - {e}")

                    if body:
                        res = self.create_state(body["data"]["records"])
                    else:
                        res = []

                    for item in res:
                        if item not in await self.cache.get_list("scheduler"):
                            print("new idea found!!!")

                            params = item.split("_")

                            params[4] = (
                                None if params[4] == "None" else params[4]
                            )

                            await self.flights.flight_etl(*params)
                            await self.hotels.hotels_etl(
                                params[1], params[2], params[3], params[4]
                            )
                            await self.weather.weather_etl(
                                params[1], params[2], params[3], params[4]
                            )
                            await self.cache.add_list("scheduler", item)

                    now = time.time()

                    time.sleep(10)
                    print(f"wait new ideas last idea by {now}")


if __name__ == "__main__":
    etl = PoolRunner()

    asyncio.run(etl.scheduler())
