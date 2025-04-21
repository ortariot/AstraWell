import asyncio
import time
from datetime import datetime
from pprint import pprint

import aiohttp

from etl.flight import FlightEtl
from etl.hotel import HotelEtl
from etl.weather import WeathersEtl
from core.settings import settings


class PoolRunner:

    mws_tables_token = settings.mws_tables_token
    state = set()
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

        req_url = "https://true.tabs.sale/fusion/v1/datasheets/dstThkcrNzwYXtJYrA/records?viewId=viwn1y8BUUFTy&fieldKey=name"
        headers = {
            "Authorization": self.mws_tables_token,
            "Content-Type": "application/json",
        }
        async with aiohttp.ClientSession() as session:
            while True:
                response = await session.request(
                    "GET", req_url, json=None, params=None, headers=headers
                )

                body = await response.json()

                res = self.create_state(body["data"]["records"])

                for item in res:
                    if item not in self.state:
                        print("new idea found!!!")

                        params = item.split("_")

                        # print(params)
                        params[4] = None if params[4] == "None" else params[4]

                        await self.flights.flight_etl(*params)
                        await self.hotels.hotels_etl(
                            params[1], params[2], params[3], params[4]
                        )
                        await self.weather.weather_etl(
                            params[1], params[2], params[3], params[4]
                        )
                        self.state.add(item)

                time.sleep(10)


if __name__ == "__main__":
    etl = PoolRunner()

    asyncio.run(etl.scheduler())
