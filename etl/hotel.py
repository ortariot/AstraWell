import asyncio
from datetime import datetime
from pprint import pprint
import json

import aiohttp

from core.settings import settings


class HotelEtl:

    mws_tables_token = settings.mws_tables_token

    async def hotels_etl(
        self,
        locataion: str,
        preference_id: str,
        check_in: str,
        check_out: str | None = None,
    ):

        hotels = await self.get_hotels(locataion, check_in, check_out)
        if check_out:

            days = datetime.fromisoformat(check_out) - datetime.fromisoformat(
                check_in
            )
            days = days.days

        else:
            days = 1

        if hotels:
            data = self.preparate(
                hotels, locataion, check_in, days, preference_id
            )

            await self.load_hotels(data)

            print(f"add hotels for location {locataion}")
        else:
            print(f"hotels for location {locataion} not found")

    async def get_hotels(
        self, locataion: str, checkIn: str, checkOut: str | None = None
    ) -> list:

        if checkOut is None:
            checkOut = checkIn

        async with aiohttp.ClientSession() as session:
            req_url = "https://engine.hotellook.com/api/v2/cache.json?"

            req_params = {
                "location": locataion,
                "checkIn": checkIn,
                "checkOut": checkOut,
                "currency": "rub",
                "limit": 10,
            }
            try:
                response = await session.request(
                    "GET", req_url, params=req_params, timeout=5
                )
            except TimeoutError:
                print(f"timeout with api: engine.hotellook.com")

            try:
                body = await response.json()
            except (
                json.decoder.JSONDecodeError,
                aiohttp.client_exceptions.ContentTypeError,
            ) as e:
                print(f"error {e} in func get_hotels")
                body = []

            return body

    def preparate(
        self,
        data: list,
        locataion: str,
        check_in: str,
        days: int,
        preference_id: str,
    ):

        # print(locataion)
        res = []
        for item in data:

            res.append(
                {
                    "fields": {
                        "hotel_name": item["hotelName"],
                        "iata": locataion,
                        "country": item["location"]["country"],
                        "city": item["location"]["name"],
                        "avg_price": item["priceAvg"],
                        "stars": item["stars"],
                        "arrival": check_in,
                        "days": days,
                        "price_per_day": (
                            int(item["priceAvg"]) / days
                            if days > 0
                            else item["priceAvg"]
                        ),
                        "preference": [preference_id],
                    }
                }
            )

        return res

    async def load_hotels(self, hotels: list):

        req_url = (
            settings.mws_api_path
            + f"/fusion/v1/datasheets/{settings.mws_table_hotels}/records"
        )

        headers = {
            "Authorization": self.mws_tables_token,
            "Content-Type": "application/json",
        }

        json = {
            "records": hotels,
            "fieldKey": "name",
        }

        async with aiohttp.ClientSession() as session:

            try:
                response = await session.request(
                    "POST", req_url, json=json, headers=headers, timeout=5
                )
            except TimeoutError:
                print(f"timeout with api: {settings.mws_api_path}")
