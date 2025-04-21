import asyncio
from datetime import datetime
from pprint import pprint

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

        data = self.preparate(hotels, locataion, check_in, days, preference_id)

        print(f"add hotels for location {locataion}")
        await self.load_hotels(data)

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
            response = await session.request(
                "GET", req_url, json=None, params=req_params
            )

            body = await response.json()

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
                        "price_per_day": int(item["priceAvg"]) / days,
                        "preference": [preference_id],
                    }
                }
            )

        return res

    async def load_hotels(self, hotels: list):
        req_url = "https://true.tabs.sale/fusion/v1/datasheets/dstNBH9m70fMYr5mdX/records?viewId=viwbk0Np3NGEJ&fieldKey=name"

        headers = {
            "Authorization": self.mws_tables_token,
            "Content-Type": "application/json",
        }

        data = {
            "records": hotels,
            "fieldKey": "name",
        }

        async with aiohttp.ClientSession() as session:
            response = await session.request(
                "POST",
                req_url,
                json=data,
                params=None,
                headers=headers,
                data=None,
            )

            body = await response.json()

