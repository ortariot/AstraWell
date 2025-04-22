import asyncio
import json
import logging
from contextlib import asynccontextmanager

import uvicorn

from aiohttp import ClientSession
from fastapi import FastAPI
from starlette.requests import Request
from starlette.responses import JSONResponse

from src.bot import bot, dp, polling, STATE, StateService, autocompleting


logging.basicConfig(level=logging.DEBUG)

logger = logging.getLogger(__name__)

BG_TASKS = set()

@asynccontextmanager
async def lifespan(app):
    with open('all_user.json') as file:
        data = json.load(file)
        state = StateService.model_validate(data)
        STATE.users = state.users
        STATE.from_nick = {_.nick:_ for _ in STATE.users if _.nick is not None}
        STATE.from_mts_user_id = {_.mts_user_id:_ for _ in STATE.users if _.mts_user_id is not None}
    STATE.http_session = ClientSession()
    await STATE.http_session.start()

    BG_TASKS.add(asyncio.create_task(dp.start_polling(bot,polling_timeout= 1)))
    BG_TASKS.add(asyncio.create_task(polling(bot)))
    BG_TASKS.add(asyncio.create_task(autocompleting()))
    yield
    with open('all_user.json', 'w') as file:
        json.dump(STATE.model_dump(), file)
    for t in BG_TASKS:
        t.cancel()
    await STATE.http_session.stop()


app = FastAPI(lifespan=lifespan, openapi_tags=[
    {'name': 'click_main'}
])

@app.get("/get_state")
async def get_state() -> StateService:
    return STATE.model_dump()




@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Непредвиденная ошибка запроса: {exc}")
    return JSONResponse(status_code=500, content=f"{exc}")

if __name__ == '__main__':
    uvicorn.run(app, port=8080)