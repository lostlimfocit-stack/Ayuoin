import asyncio
import json
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiohttp import web

API_TOKEN = os.getenv("API_TOKEN", "8458016571:AAFQpM-UjHR2nneYhwgDHECQILulwGTtapQ")
ADMIN_ID = int(os.getenv("ADMIN_ID", 6218936231))  # твой айди

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- Работа с JSON ---
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
    except:
        return {"balances": {}, "usernames": {}, "used_promos": {}, "promocodes": {}}

def save_data(data):
    with open("balances.json", "w") as f:
        json.dump(data, f)

data = load_data()

# --- FSM для перевода ---
class Transfer(StatesGroup):
    waiting_for_user = State()
    waiting_for_amount = State()

# --- Кнопки ---
main_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Баланс °.•🎀", callback_data="balance")],
    [InlineKeyboardButton(text="Отправить °.•🎀", callback_data="send")]
])

# --- Старт ---
@dp.message(F.text.startswith("/start"))
async def start(message: types.Message):
    user_id = str(message.from_user.id)
    username = message.from_user.username
    args = message.text.split()

    if user_id not in data["balances"]:
        data["balances"][user_id] = 25
    if username:
        data["usernames"][username.lower()] = user_id

    # Проверка промокода
    if len(args) > 1:
        code = args[1]
        if code in data["promocodes"] and user_id not in data["used_promos"].get(code, []):
            reward = data["promocodes"][code]
            data["balances"][user_id] += reward
            data["used_promos"].setdefault(code, []).append(user_id)
            save_data(data)
            await message.answer(f"✨ Промокод '{code}' активирован! +{reward} аюоинов 🌸")

    save_data(data)

    text = (
        "Добро пожаловать!\n"
        "Я аюоин, валюта tg канала: @ayuolmaoo (⁠.⁠❛⁠ᴗ⁠❛⁠.)\n\n"
        "Благодаря мне можно:\n"
        "Обменивать, продавать, покупать персонажей ;\n\n"
        "🎀 Проверь свой баланс или отправь аюоины другу!"
    )
    await message.answer(text, reply_markup=main_menu)

# --- Баланс ---
@dp.callback_query(F.data == "balance")
async def balance(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    bal = data["balances"].get(user_id, 0)
    await callback.message.answer(f"Твой баланс... {bal} аюоинов! 💖")

# --- Отправить ---
@dp.callback_query(F.data == "send")
async def send(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "Отправьте другому человеку аюоины ^^ ~\n"
        "Для этого напишите его @юзернейм 💕"
    )
    await state.set_state(Transfer.waiting_for_user)

@dp.message(Transfer.waiting_for_user)
async def process_user(message: types.Message, state: FSMContext):
    username = message.text.lstrip("@").lower()
    if username not in data["usernames"]:
        await message.answer("Такого пользователя нет... 🥺")
        return
    await state.update_data(receiver=username)
    await message.answer("Введите число аюоинов для перевода ✨")
    await state.set_state(Transfer.waiting_for_amount)

@dp.message(Transfer.waiting_for_amount)
async def process_amount(message: types.Message, state: FSMContext):
    try:
        amount = int(message.text)
    except:
        await message.answer("Введите число!")
        return

    sender_id = str(message.from_user.id)
    user_data = await state.get_data()
    receiver_username = user_data["receiver"]
    receiver_id = data["usernames"][receiver_username]

    if data["balances"].get(sender_id, 0) < amount:
        await message.answer("Недостаточно аюоинов 💔")
        await state.clear()
        return

    # Перевод
    data["balances"][sender_id] -= amount
    data["balances"][receiver_id] = data["balances"].get(receiver_id, 0) + amount
    save_data(data)

    # Сообщения
    await message.answer(
        f"Вы отправили @{receiver_username} {amount} аюоинов! ^^ спасибо! 🎀"
    )
    try:
        await bot.send_message(
            receiver_id,
            f"Пользователь @{message.from_user.username} отправил вам {amount} аюоинов! Спасибо ^^~ 💕"
        )
    except:
        pass

    await state.clear()

# --- Создание нового промокода (только админ) ---
@dp.message(F.text.startswith("/newpromo"))
async def new_promo(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) != 3:
        await message.answer("Формат: /newpromo название число")
        return
    code, reward = parts[1], parts[2]
    try:
        reward = int(reward)
    except:
        await message.answer("Нужно указать число награды!")
        return

    data["promocodes"][code] = reward
    save_data(data)

    link = f"https://t.me/Ayuoin_bot?start={code}"
    await message.answer(
        f"✨ Промокод создан: '{code}' (+{reward} аюоинов)\n"
        f"Ссылка для активации: {link}"
    )

# --- Просмотр активных промокодов (только админ) ---
@dp.message(F.text.startswith("/promos"))
async def show_promos(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    if not data["promocodes"]:
        await message.answer("Нет активных промокодов 🌸")
        return
    text = "Активные промокоды:\n"
    for code, reward in data["promocodes"].items():
        text += f"- {code} : +{reward} аюоинов\n"
    await message.answer(text)

# --- Web server-заглушка для Render ---
async def handle(request):
    return web.Response(text="Bot is running!")

async def start_web_app():
    app = web.Application()
    app.add_routes([web.get("/", handle)])
    port = int(os.environ.get("PORT", 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

# --- Запуск ---
async def main():
    # запускаем web-сервер + polling параллельно
    asyncio.create_task(start_web_app())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
