import asyncio
import logging
from asyncio import CancelledError
from datetime import datetime
from functools import partial

from dateutil.parser import parse
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.filters.command import Command
from aiogram.enums.dice_emoji import DiceEmoji
from aiogram.types import LinkPreviewOptions
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiohttp import ClientSession
from pydantic import BaseModel, Field
from aiogram.filters import Command
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state, StatesGroup, State
from aiogram.types import Message, ReplyKeyboardRemove

from src.config import CFG

logger = logging.getLogger(__name__)

class UserInfo(BaseModel):
    nick: str | None = None
    chat_id: int | None = None
    mts_role: str | None = None
    mts_record_id: str| None = None
    mts_user_id: str = None


class StateService(BaseModel):
    users: list[UserInfo] = []
    from_nick: dict[str, UserInfo] = Field(None, exclude=True)
    from_mts_user_id: dict[str, UserInfo] = Field(None, exclude=True)



bot = Bot(token=CFG.BOT.TOKEN)
# Диспетчер
dp = Dispatcher()
STATE = StateService()

async def _get_table(url: str, fields: list[str] | None = None):
    params = {'fields': fields} if fields else {}
    async with ClientSession() as ses:
        async with ses.get(
                url,
                headers={'Authorization': f'Bearer {CFG.MTS.TOKEN}'},
                params=params,
                raise_for_status=True
        ) as response:
            return await response.json()

get_users = partial(_get_table, 'https://true.tabs.sale/fusion/v1/datasheets/dstGLhT5cQ14QWYrvP/records')
get_managers = partial(_get_table, 'https://true.tabs.sale/fusion/v1/datasheets/dstQrDCjZUP3CURDDD/records')
get_directors = partial(_get_table, 'https://true.tabs.sale/fusion/v1/datasheets/dst83xQGFcF3Rq1epj/records')
get_user_autocomplete = partial(_get_table, 'https://true.tabs.sale/fusion/v1/datasheets/dstfmuNcr1RQQypr9q/records')
get_poling_messages = partial(_get_table, 'https://true.tabs.sale/fusion/v1/datasheets/dstkgFW7oLupkX4qAP/records')

async def do_user_autocomplete():
    data = await get_user_autocomplete()
    data = data['data']
    logger.info('К авттокомплекту: %s', data['total'])
    if data['total'] > 0:
        for record in data['records']:
            try:
                async with ClientSession() as ses:
                    fields = record['fields']
                    if fields['user'] not in STATE.from_mts_user_id:
                        logger.info('пора ради %s обновить %s', fields['user'], STATE.from_mts_user_id )
                        await merge_users()
                    if fields['user'] in STATE.from_mts_user_id:
                        data = {
                            'records': [
                                {
                                    'recordId': fields['target_id'],
                                    'fields': {
                                        f'{fields["target_field"]}': [
                                            STATE.from_mts_user_id[fields['user']].mts_record_id
                                        ]
                                    }
                                }
                            ]
                        }
                        async with ses.patch(
                            f"https://true.tabs.sale/fusion/v1/datasheets/{fields['target_shield']}/records",
                            headers={'Authorization': f'Bearer {CFG.MTS.TOKEN}'},
                            raise_for_status=True,
                            json=data
                        ) as response:
                            result = await response.json()
                            logger.debug('Проставил юзера %s, %s, %s', record, result, data)
                    else:
                        logger.warning('ПЛОХАЯ ЗАПИСЬ! %s', record)
                    # ПРИБОРКА
                    async with ses.delete(
                        "https://true.tabs.sale/fusion/v1/datasheets/dstfmuNcr1RQQypr9q/records",
                        headers={'Authorization': f'Bearer {CFG.MTS.TOKEN}'},
                        raise_for_status=True,
                        params={'recordIds': record['recordId']}
                    ) as response:
                        result = await response.json()
                        logger.debug('Очистил атвокомпликт %s, %s', record, result)

            except Exception as exc:
                logger.exception('Автокомпликт %s, %s', exc, record)


async def autocompleting():
    run = True
    while run:
        try:
             await do_user_autocomplete()
        except CancelledError:
            run = False
        except Exception as exc:
            logger.exception('FAIL AUTOCOMPLETTIG %s', exc)
        await asyncio.sleep(2)

simple_msg = {
    'text': None,
    'markdown': ParseMode.MARKDOWN,
    'html': ParseMode.HTML
}

async def send_messages(messages: list[dict], bot: Bot):
    for record in messages:
        try:
            type_message = record['fields'].get('type', 'text')
            if type_message in simple_msg:
                type_message = simple_msg[type_message]
                kwargs = {} if type_message is None else dict(
                    parse_mode=type_message
                )
                await bot.send_message(STATE.from_nick[record['fields']['username']].chat_id, record['fields']['text'], **kwargs)
            async with ClientSession() as ses:
                async with ses.delete(
                        "https://true.tabs.sale/fusion/v1/datasheets/dstkgFW7oLupkX4qAP/records",
                        headers={'Authorization': f'Bearer {CFG.MTS.TOKEN}'},
                        params={'recordIds': record['recordId']},
                        raise_for_status=True
                ) as response:
                    data = await response.json()
                    logger.debug('Очистка удалённого сообщения %s', data)
        except Exception as exc:
            logger.exception('Отправка сообщения, %s %s', exc, record)

async def get_polling_mts_message():
    full_fields = {'username', 'type', 'text'}
    good_messages = []
    drop_messages = []
    data = await get_poling_messages()
    if data['code'] == 200:
        for record in data['data']['records']:
            if set(record['fields']) == full_fields:
                good_messages.append(record)
            else:
                drop_messages.append(record)
        logger.info('Годных сообщений %s, плохих сообщений %s', len(good_messages), len(drop_messages))
    else:
        logger.warning('Ошибка запроса сообщений: %s', data)
    return good_messages

async def polling(bot: Bot):
    run = True
    while run:
        try:
            messages = await get_polling_mts_message()
            await send_messages(messages, bot)
        except CancelledError:
            run = False
        except Exception as exc:
            logger.exception('FAIL POLLINNG %s', exc)
        await asyncio.sleep(2)

def _extract_nicks(data: dict, user_field: str = None) -> dict[str, UserInfo]:
    if data['code'] != 200:
        logger.warning('fail http response %s', data)
        return {}
    try:
        return {
            name_: (UserInfo() if user_field is None else UserInfo(
                nick=name_,
                mts_record_id=record['recordId'],
                mts_user_id=record['fields'][user_field]['id']
            ))
            for record in data['data']['records'] if (name_ := record['fields'].get('user_name')) is not None
        }
    except Exception as exc:
        logger.exception('ПАРСИНГ %s', data)
        return {}

class NewIdea(StatesGroup):
    name = State()
    description = State()
    start_date = State()
    end_date = State()

def make_row_keyboard(*items: list[str]) -> types.ReplyKeyboardMarkup:
    """
    Создаёт реплай-клавиатуру с кнопками в один ряд
    :param items: список текстов для кнопок
    :return: объект реплай-клавиатуры
    """
    row = [types.KeyboardButton(text=item) for item in items]
    return types.ReplyKeyboardMarkup(keyboard=[row], resize_keyboard=True, input_field_placeholder="Хм...")

# Хэндлер на команду /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await update_register(message)

    user = STATE.from_nick[message.from_user.username]
    logger.info('start %s', user)
    if user.mts_role == 'director':
        await message.answer("Привет, господин директор!")
    elif user.mts_role == 'manager':
        await message.answer("Привет, господин менеджер.")
    elif user.mts_role == 'user':
        keyboard = make_row_keyboard("новая идея", "посмотреть идеи")
        await message.answer("Привет, пользователь!\nПодумаем над новой идеей? Или вспомним  какие уже есть?", reply_markup=keyboard)
    else:
        options_2 = LinkPreviewOptions(
            url="https://true.tabs.sale/share/shrj0nKc2ujcmCU8zTQz0/fomyhCAk2XGlPDZn6B",
            prefer_small_media=True
        )
        await message.answer("Привет!.. Мы поможем тебе хорошо отдохнуть и не пролететь. Давай подключаться к проекту?", link_preview_options=options_2)


def _is_user(message: types.Message):
    user = STATE.from_nick[message.from_user.username]
    return user.mts_role == 'user'


def _is_manager(message: types.Message):
    user = STATE.from_nick[message.from_user.username]
    return user.mts_role == 'manager'


def _is_director(message: types.Message):
    user = STATE.from_nick[message.from_user.username]
    return user.mts_role == 'director'


@dp.message(F.text.lower() == "новая идея")
async def new_idea(message: types.Message, state: FSMContext):
    if not _is_user(message):
        return
    await state.clear()
    await message.answer('Отлично! Давайте её кратко назовём:')
    await state.set_state(NewIdea.name)


@dp.message(NewIdea.name)
async def new_idea_name(message: Message, state: FSMContext):
    if not _is_user(message):
        return
    await state.update_data(idea_name=message.text)
    await message.answer(
        text=f"{message.text} - 'это звучит неплохо! Теперь, опишите, чего вы бы вы хотели получить от этой поездки? Не стесняйтесь в своих пожеланиях ;)",
    )
    await state.set_state(NewIdea.description)


@dp.message(NewIdea.description)
async def new_idea_description(message: Message, state: FSMContext):
    if not _is_user(message):
        return
    await state.update_data(idea_description=message.text)
    await message.answer(
        text=f"Отлично задумано! Напишите дату (желательно YYYY.MM.DD), когда бы хотели начать:"
    )
    await state.set_state(NewIdea.start_date)

@dp.message(NewIdea.start_date)
async def new_idea_start_date(message: Message, state: FSMContext):
    if not _is_user(message):
        return
    try:
        date: datetime = parse(message.text)
        timestamp = date.timestamp() * 1000
    except Exception as exc:
        await message.answer(
            text=f"Ууупс, я извиняюсь, не смог разобрать дату. Напишите дату, когда бы хотели начать:"
        )
    else:
        await state.update_data(idea_start_date=timestamp)
        await message.answer(
            text=f"записал {date.isoformat()}! Напишите дату (желательно YYYY.MM.DD), когда бы хотели вернуться:"
        )
        await state.set_state(NewIdea.end_date)



@dp.message(NewIdea.end_date)
async def new_idea_end_date(message: Message, state: FSMContext):
    if not _is_user(message):
        return
    try:
        date: datetime = parse(message.text)
        timestamp = date.timestamp()*1000
    except Exception as exc:
        await message.answer(
            text=f"Ууупс, я извиняюсь, не смог разобрать дату. Напишите дату, когда бы хотели вернуться:"
        )
    else:
        keyboard = make_row_keyboard("новая идея", "посмотреть идеи")
        result = 'Отлично, [записал](https://true.tabs.sale/workbench/mirwP09NHQExSZeMr6), скоро будут предложения.'
        data = await state.get_data()
        await state.clear()
        try:
            async with ClientSession() as ses:
                async with ses.post(
                    "https://true.tabs.sale/fusion/v1/datasheets/dstBuL8jPgynbJrEpD/records",
                    headers={'Authorization': f'Bearer {CFG.MTS.TOKEN}'},
                    raise_for_status=True,
                    json={
                        'records':[
                            {
                                "fields": {
                                    "name": data["idea_name"],
                                    "description": data["idea_description"],
                                    "user": [STATE.from_nick[message.from_user.username].mts_record_id],
                                    "start_date":data["idea_start_date"],
                                    "return_date": timestamp
                                }
                            }
                        ]
                    }
                ) as response:
                    data = await response.json()
                    logger.debug('Добавление записи идеи %s', data)
        except Exception as exc:
            result = 'Ууупс, я извиняюсь, что-то пошло не так, попробуйте позже...'
            logger.exception('Ошибка регистрации идеи %s %s', message.from_user.username, exc)
        await message.answer(
            text=f"{result} Что-нибудь ещё?", reply_markup = keyboard,
            parse_mode=ParseMode.MARKDOWN
        )


@dp.message(F.text.lower() == "поcмотреть идеи")
async def without_puree(message: types.Message, state: FSMContext):
    await message.reply("Так невкусно!")



@dp.message(Command("dice"))
async def cmd_dice(message: types.Message, bot: Bot):
    await bot.send_dice(message.chat.id, emoji=DiceEmoji.DICE)

@dp.message(Command("reply_builder"))
async def reply_builder(message: types.Message):
    builder = ReplyKeyboardBuilder()
    for i in range(1, 17):
        builder.add(types.KeyboardButton(text=str(i)))
    builder.adjust(4)
    await message.answer(
        "Выберите число:",
        reply_markup=builder.as_markup(resize_keyboard=True),
    )

async def merge_users():
    user_nicks = _extract_nicks(await get_users(fields=['user_name', 'FormUser']), user_field='FormUser')
    for k, v in user_nicks.items():
        if k in STATE.from_nick:
            vv = STATE.from_nick[k]
            vv.mts_user_id = vv.mts_user_id or v.mts_user_id
            vv.mts_record_id = vv.mts_record_id or v.mts_record_id
            if vv.mts_user_id is not None:
                STATE.from_mts_user_id[vv.mts_user_id] = vv
        else:
            STATE.users.append(v)
            STATE.from_nick[v.nick] = v
            STATE.from_mts_user_id[v.mts_user_id] = v
    return user_nicks

@dp.message()
async def update_register(message: types.Message):
    logger.debug('update register')
    id_ = message.from_user.id
    nick_ = message.from_user.username
    if nick_ not in STATE.from_nick:
        new_info = UserInfo(nick=nick_, chat_id=id_)
        STATE.from_nick[nick_] = new_info
        STATE.users.append(new_info)
    info = STATE.from_nick[nick_]
    info.chat_id = id_
    if info.mts_role is None:
        user_nicks = await merge_users()
        if nick_ in user_nicks:
            info.mts_role = 'user'
        elif nick_ in _extract_nicks(await get_managers(fields=['user_name'])):
            info.mts_role = 'manager'
        if nick_ in _extract_nicks(await get_directors(fields=['user_name'])):
            info.mts_role = 'director'