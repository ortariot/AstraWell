import asyncio
from pprint import pprint
import json

import aiohttp

from core.settings import settings


class FlightEtl:
    aviasale_token = settings.aviasales_token
    mws_tables_token = settings.mws_tables_token
    state = set()

    async def flight_etl(
        self,
        origin: str,
        destination: str,
        preference_id: str,
        departure_at: str,
        return_at: str = None,
    ):

        data = await self.get_flight(
            origin=origin,
            destination=destination,
            departure_at=departure_at,
            return_at=return_at,
            preference_id=preference_id,
        )

        if data:
            await self.send_data(data)
            print(f"aff flight by route {origin} - {destination}")
        else:
            print(f"no flight information {origin} - {destination}")

    async def send_data(self, flights):

        req_url = (
            settings.mws_api_path
            + f"/fusion/v1/datasheets/{settings.mws_table_flights}/records"
        )

        async with aiohttp.ClientSession() as session:

            headers = {
                "Authorization": self.mws_tables_token,
                "Content-Type": "application/json",
            }

            json = {
                "records": flights,
                "fieldKey": "name",
            }

            try:
                response = await session.request(
                    "POST",
                    req_url,
                    json=json,
                    params=None,
                    headers=headers,
                    data=None,
                    timeout=5,
                )
            except TimeoutError:
                print(f"timeout with api: {settings.mws_api_path}")

    async def test_get(self):
        async with aiohttp.ClientSession() as session:
            req_url = "https://true.tabs.sale/fusion/v1/datasheets/dstcm0K692wmmJX2Pq/records?viewId=viwR9ZsN4vH3x&fieldKey=name"

            req_json = {"Authorization": self.mws_tables_token}
            response = await session.request(
                "GET", req_url, json=None, params=None, headers=req_json
            )

    async def monthly_flight(
        self,
        origin: str,
        destination: str,
        departure_at: str,
        preference_id: str,
    ):
        req_url = "http://api.travelpayouts.com/v2/prices/month-matrix"
        req_params = {
            "currency": "rub",
            "origin": origin,
            "destination": destination,
            "show_to_affiliates": "false",
            "month": departure_at,
            "one_way": "true",
            "token": self.aviasale_token,
        }

        async with aiohttp.ClientSession() as session:

            try:
                response = await session.request(
                    "GET", req_url, params=req_params, timeout=2
                )
            except TimeoutError:
                print(
                    f"timeout from api.travelpayouts with month-matrix operation for {origin} - {destination} flight"
                )
                response = None

            if response:

                try:
                    body = await response.json()
                except json.decoder.JSONDecodeError as e:
                    body = {}
                    print(f"error - {e}")

            else:
                body = {}

            flight_data = body.get("data") if body.get("data") else []

            monthly_data = [
                {
                    "fields": {
                        "price": int(item["value"]),
                        "origin_airport": item["origin"],
                        "destination_airport": item["destination"],
                        "departure_at": item["depart_date"],
                        "preference": [preference_id],
                    }
                }
                for item in flight_data
            ]

            return monthly_data

    def preparate_data(self, body: list, preference_id: str) -> list:
        return [
            {
                "fields": {
                    "flight_number": item["airline"]
                    + " "
                    + item["flight_number"],
                    "price": int(item["price"]),
                    "origin_airport": item["origin_airport"],
                    "destination_airport": item["destination_airport"],
                    "departure_at": item["departure_at"],
                    "preference": [preference_id],
                }
            }
            for item in body
        ]

    async def get_flight(
        self,
        origin: str,
        destination: str,
        departure_at: str,
        preference_id: str,
        return_at: str | None = None,
    ) -> list:
        result = []
        req_url = "https://api.travelpayouts.com/aviasales/v3/prices_for_dates"

        req_params = {
            "origin": origin,
            "destination": destination,
            "departure_at": departure_at,
            "unique": "false",
            "sorting": "price",
            "direct": "false",
            "currency": "rub",
            "limit": 20,
            "token": self.aviasale_token,
            "page": 1,
            "one_way": "false",
        }

        async with aiohttp.ClientSession() as session:

            try:
                response = await session.request(
                    "GET", req_url, params=req_params, timeout=5
                )
                body = await response.json()
            except (TimeoutError, json.decoder.JSONDecodeError) as e:
                body = {}
                print(
                    f"error {e} for api.travelpayouts with prices_for_dates operation for {origin} - {destination} flight"
                )

            if body.get("data"):
                prepeare_data = self.preparate_data(
                    body.get("data"), preference_id
                )
                result.extend(prepeare_data)
            else:
                montly_data = await self.monthly_flight(
                    origin, destination, departure_at, preference_id
                )
                result.extend(montly_data)

        if return_at:
            req_params["origin"] = destination
            req_params["destination"] = origin
            req_params["departure_at"] = return_at

            async with aiohttp.ClientSession() as session:
                response = await session.request(
                    "GET", req_url, params=req_params
                )

                try:
                    body = await response.json()
                except json.decoder.JSONDecodeError as e:
                    body = {}
                    print(f"error - {e}")

                if body.get("data"):
                    prepeare_data = self.preparate_data(
                        body.get("data"), preference_id
                    )
                    result.extend(prepeare_data)
                else:
                    montly_data = await self.monthly_flight(
                        destination, origin, departure_at, preference_id
                    )
                    result.extend(montly_data)

        return result
