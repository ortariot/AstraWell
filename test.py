import asyncio
from pprint import pprint

import aiohttp

from ainetwork.deepseek import DeepSeek
from core.settings import settings


class Idea:
    mws_tables_token = settings.mws_tables_token
    state = set()
    deepdeek = DeepSeek()

    async def smart_idea(self):
        while True:
            try:
                ideas = await self.get_ideas()
            except Exception as e:
                print(f"error -{e}")
                continue

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

                if idea in self.state:
                    continue

                print(f"finded new idea {name}")

                # smart_preference = ["KJA"]

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
                    preferences.append(preference)

                    self.state.add(idea)

                await self.update_idea(item, preferences)

    async def load_pref(self):

        data = {
            "fields": {
                "origin": "AAA",
                "destination": "DME",
                "departure_at": "2025-07-07",
                "return_at": "2025-07-09",
            }
        }

        req_url = "https://true.tabs.sale/fusion/v1/datasheets/dstThkcrNzwYXtJYrA/records?viewId=viwn1y8BUUFTy&fieldKey=name"

        headers = {
            "Authorization": self.mws_tables_token,
            "Content-Type": "application/json",
        }

        data = {
            "records": [data],
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
            print(body)
            return body["data"]["records"][0]["recordId"]

    async def get_pref(self):

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

                pprint(body["data"]["records"][0])
                # res = self.create_state(body["data"]["records"])


if __name__ == "__main__":
    idea = Idea()
    asyncio.run(idea.load_pref())
