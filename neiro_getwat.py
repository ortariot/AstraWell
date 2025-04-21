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

                print(item)
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

    async def update_idea(self, idea: dict, preferences: list):

        
        idea_id = idea["recordId"]
        
        try:
            pref = idea["fields"]["preferences"]
        except KeyError:
            pref = []

        pref.extend(preferences)

        req_url = f"https://true.tabs.sale/fusion/v1/datasheets/dstBuL8jPgynbJrEpD/records?viewId=viwoRLSXorhlE&fieldKey=name&recordId={idea_id}"

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

        data = {
            "records": [new_idea],
            "fieldKey": "name",
        }

        async with aiohttp.ClientSession() as session:
            response = await session.request(
                "PATCH",
                req_url,
                json=data,
                params=None,
                headers=headers,
                data=None,
            )

            await response.json()

    async def load_preferences(self, data):

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
            
            return body["data"]["records"][0]["recordId"]

    async def get_ideas(self):

        async with aiohttp.ClientSession() as session:
            req_url = "https://true.tabs.sale/fusion/v1/datasheets/dstBuL8jPgynbJrEpD/records?viewId=viwYpZ7p0n8gT&fieldKey=name"

            req_json = {"Authorization": self.mws_tables_token}
            response = await session.request(
                "GET", req_url, json=None, params=None, headers=req_json
            )

            body = await response.json()

            if body:
                return body["data"]["records"]

    async def get_user_city(self, user_id=None):

        users_req_url = "https://true.tabs.sale/fusion/v1/datasheets/dstGLhT5cQ14QWYrvP/records?viewId=viwboSnk89esr&fieldKey=name"
        user_req_url = f"https://true.tabs.sale/fusion/v1/datasheets/dstGLhT5cQ14QWYrvP/records?viewId=viwboSnk89esr&fieldKey=name&recordIds={user_id}"
        req_url = user_req_url if user_id else users_req_url

        req_json = {"Authorization": self.mws_tables_token}

        async with aiohttp.ClientSession() as session:
            response = await session.request(
                "GET", req_url, json=None, params=None, headers=req_json
            )

            body = await response.json()

            try:
                user_city = body["data"]["records"][0]["fields"]["city"][0]
            except (KeyError, IndexError):
                user_city = "recAzsPCk7887"

            return user_city

    async def get_iata_code(self, city_id=None):

        req_url = f"https://true.tabs.sale/fusion/v1/datasheets/dstrTgnHfh2WLuls4X/records?viewId=viw2qv1J7mKKQ&fieldKey=name&recordIds={city_id}"
        req_json = {"Authorization": self.mws_tables_token}

        async with aiohttp.ClientSession() as session:
            response = await session.request(
                "GET", req_url, json=None, params=None, headers=req_json
            )

            body = await response.json()

            try:
                iata_code = body["data"]["records"][0]["fields"]["iata_code"]
            except (KeyError, IndexError):
                iata_code = "DME"

            return iata_code


if __name__ == "__main__":
    idea = Idea()
    asyncio.run(idea.smart_idea())
