import asyncio
from pprint import pprint
import json

import aiohttp
import httpx

from ainetwork.deepseek import DeepSeek
from db.cache import RedisRepository
from core.settings import settings


class Idea:
    mws_tables_token = settings.mws_tables_token
    state = set()
    deepdeek = DeepSeek()
    cache = RedisRepository()

    async def smart_idea(self):
        while True:

            ideas = await self.get_ideas()

            for item in ideas:
                try:
                    name = item["fields"]["name"]
                except KeyError:
                    continue
                try:
                    description = (
                        item["fields"]["description"]
                        if item["fields"].get("description")
                        else None
                    )
                except KeyError:
                    continue

                recordId = item["recordId"]

                idea = "_".join([name, recordId])

                if idea in await self.cache.get_list("neiro_getway"):
                    continue

                print(f"finded new idea {name}")

                if description:
                    smart_preference = self.deepdeek.get_ai_preferences(
                        description
                    )

                user_id = item["fields"]["user"][0]
                user_city_id = await self.get_user_city(user_id)
                home_iata_code = await self.get_iata_code(user_city_id)

                preferences = []
                for destination in smart_preference:

                    data = {
                        "fields": {
                            "origin": home_iata_code,
                            "destination": destination,
                            "departure_at": item["fields"]["start_date"],
                            "return_at": item["fields"]["return_date"],
                        }
                    }
                    print(
                        f"create preferences for route {home_iata_code} - {destination} for motivation {description}"
                    )

                    preference = await self.load_preferences(data)
                    if preference:
                        preferences.append(preference)

                    await self.cache.add_list("neiro_getway", idea)

                await self.update_idea(item, preferences)

    async def update_idea(self, idea: dict, preferences: list):

        idea_id = idea["recordId"]

        try:
            pref = idea["fields"]["preferences"]
        except KeyError:
            pref = []

        pref.extend(preferences)

        req_url = (
            settings.mws_api_path
            + f"/fusion/v1/datasheets/{settings.mws_table_ideas}/records"
        )

        headers = {
            "Authorization": self.mws_tables_token,
            "Content-Type": "application/json",
        }

        new_idea = {
            "fields": {
                "preferences": pref,
            },
            "recordId": idea_id,
        }

        json = {
            "records": [new_idea],
            "fieldKey": "name",
        }

        async with aiohttp.ClientSession() as session:

            try:
                await session.request(
                    "PATCH", req_url, json=json, headers=headers, timeout=5
                )
            except TimeoutError:
                print(f"timeout with api: {settings.mws_api_path}")

    async def load_preferences(self, data):

        req_url = (
            settings.mws_api_path
            + f"/fusion/v1/datasheets/{settings.mws_table_preferences}/records"
        )

        headers = {
            "Authorization": self.mws_tables_token,
            "Content-Type": "application/json",
        }

        json_data = {
            "records": [data],
            "fieldKey": "name",
        }

        async with aiohttp.ClientSession() as session:

            try:
                response = await session.request(
                    "POST", req_url, json=json_data, headers=headers, timeout=5
                )
            except TimeoutError:
                response = None
                print(f"timeout with api: {settings.mws_api_path}")

            if response:
                try:
                    body = await response.json()
                    return body["data"]["records"][0]["recordId"]
                except (
                    aiohttp.client_exceptions.ContentTypeError,
                    json.decoder.JSONDecodeError,
                ) as e:
                    print("error = {e} in func: load_preferences")
            else:
                return None

    async def get_ideas(self):

        req_url = (
            settings.mws_api_path
            + f"/fusion/v1/datasheets/{settings.mws_table_ideas}/records"
        )

        req_json = {"Authorization": self.mws_tables_token}

        async with httpx.AsyncClient() as client:

            try:
                response = await client.request(
                    "GET",
                    req_url,
                    headers=req_json,
                    timeout=5,
                )
            except (
                TimeoutError,
                aiohttp.client_exceptions.ClientConnectorError,
            ):
                response = None
                print(f"timeout with api: {settings.mws_api_path}")

            if response:
                try:
                    body = response.json()
                    return body["data"]["records"]
                except (
                    aiohttp.client_exceptions.ContentTypeError,
                    json.decoder.JSONDecodeError,
                ) as e:
                    print(f"error - {e}")
                    return []
            else:
                return []

    async def get_user_city(self, user_id=None):

        req_url = (
            settings.mws_api_path
            + f"/fusion/v1/datasheets/{settings.mws_table_users}/records"
        )

        json_data = {"fieldKey": "name"}

        if user_id:
            json_data["recordIds"] = user_id

        req_json = {"Authorization": self.mws_tables_token}

        async with aiohttp.ClientSession() as session:
            try:
                response = await session.request(
                    "GET",
                    req_url,
                    json=json_data,
                    params=None,
                    headers=req_json,
                    timeout=5,
                )
            except TimeoutError:
                response = None
                print(f"timeout with api: {settings.mws_api_path}")

            try:
                body = await response.json()
            except (
                json.decoder.JSONDecodeError,
                aiohttp.client_exceptions.ContentTypeError,
            ) as e:
                body = None
                print(f"error - {e}")

            try:
                user_city = body["data"]["records"][0]["fields"]["city"][0]
            except (KeyError, IndexError, TypeError):
                user_city = "recAzsPCk7887"

            return user_city

    async def get_iata_code(self, city_id=None):

        req_url = (
            settings.mws_api_path
            + f"/fusion/v1/datasheets/{settings.mws_table_airports}/records?viewId={city_id}"
        )
        req_json = {"Authorization": self.mws_tables_token}

        async with aiohttp.ClientSession() as session:
            try:
                response = await session.request(
                    "GET",
                    req_url,
                    headers=req_json,
                    timeout=5,
                )

                body = await response.json()
            except (
                TimeoutError,
                json.decoder.JSONDecodeError,
                aiohttp.client_exceptions.ContentTypeError,
            ):
                response = None
                print(f"timeout with api: {settings.mws_api_path}")

            try:
                iata_code = body["data"]["records"][0]["fields"]["iata_code"]
            except (KeyError, IndexError, TypeError):
                iata_code = "DME"

            return iata_code


if __name__ == "__main__":
    idea = Idea()
    asyncio.run(idea.smart_idea())
