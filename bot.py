import asyncio
import json
import time
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_TOKEN = "8458016571:AAFQpM-UjHR2nneYhwgDHECQILulwGTtapQ"
ADMIN_ID = 6218936231

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

def load_data():
    try:
        with open("balances.json", "r") as f:
            data = json.load(f)
            if "balances" not in data:
                data["balances"] = {}
            if "usernames" not in data:
                data["usernames"] = {}
            if "used_promos" not in data:
                data["used_promos"] = {}
            if "promocodes" not in data:
                data["promocodes"] = {}
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        return {"balances": {}, "usernames": {}, "used_promos": {}, "promocodes": {}}

def save_data(data):
    with open("balances.json", "w") as f:
        json.dump(data, f)

data = load_data()

class Transfer(StatesGroup):
    waiting_for_user = State()
    waiting_for_amount = State()

main_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Баланс °.•🎀", callback_data="balance")],
    [InlineKeyboardButton(text="Отправить °.•🎀", callback_data="send")]
])

@dp.message(Command("start"))
async def start(message: types.Message):
    user_id = str(message.from_user.id)
    username = message.from_user.username
    args = message.text.split()

    if user_id not in data["balances"]:    
        data["balances"][user_id] = 25
        await message.answer("✨ Вам начислено 25 аюоинов за регистрацию! 🎀")
    
    if username:    
        data["usernames"][username.lower()] = user_id    

    if len(args) > 1:    
        code = args[1]    
        if code in data["promocodes"]:
            promo = data["promocodes"][code]
            if time.time() - promo["created_at"] < 86400:
                if user
import asyncio
import os
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher

# твой токен
API_TOKEN = "ТВОЙ_ТОКЕН"

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- тут твои хендлеры dp.message / dp.callback_query и т.д. ---

# Минимальный вебсервер (Render требует открытый порт)
async def handle(request):
    return web.Response(text="Bot is running!")

async def start_webserver():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 10000))  # Render даёт порт в переменной окружения
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

async def start_bot():
    await dp.start_polling(bot)

async def main():
    await asyncio.gather(start_webserver(), start_bot())

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
