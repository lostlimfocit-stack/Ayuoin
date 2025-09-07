import asyncio
import json
import time
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_TOKEN = "8458016571:AAFQpM-UjHR2nneYhwgDHECQILulwGTtapQ"
ADMIN_ID = 6218936231
WEBHOOK_PATH = f"/webhook/{API_TOKEN}"
WEBHOOK_URL = "https://your-app-name.onrender.com" + WEBHOOK_PATH  # Замените на ваш URL

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
                if user_id not in data["used_promos"].get(code, []):    
                    reward = promo["reward"]    
                    data["balances"][user_id] += reward    
                    if "used_promos" not in data:
                        data["used_promos"] = {}
                    if code not in data["used_promos"]:
                        data["used_promos"][code] = []
                    data["used_promos"][code].append(user_id)    
                    save_data(data)    
                    await message.answer(f"✨ Промокод активирован! +{reward} аюоинов 🌸\nВаш баланс: {data['balances'][user_id]} аюоинов! 💖")
                else:
                    await message.answer("Вы уже использовали этот промокод 🎀")
            else:
                await message.answer("Промокод истёк 🎀")
        else:
            await message.answer("Промокод не найден 🎀")

    save_data(data)    
    text = (    
        "Добро пожаловать!\n"    
        "Я аюоин, валюта tg канала: @ayuolmaoo (⁠.⁠❛⁠ᴗ⁠❛⁠.)\n\n"    
        "Благодаря мне можно:\n"    
        "Обменивать, продавать, покупать персонажей ;\n\n"    
        "🎀 Проверь свой баланс или отправь аюоины другу!"    
    )    
    await message.answer(text, reply_markup=main_menu)

@dp.message(Command("balance"))
async def cmd_balance(message: types.Message):
    user_id = str(message.from_user.id)
    
    if user_id not in data["balances"]:
        await message.answer("Сначала нажмите /start чтобы зарегистрироваться 🎀")
        return
        
    bal = data["balances"].get(user_id, 0)
    await message.answer(f"Твой баланс... {bal} аюоинов! 💖")

@dp.message(Command("send"))
async def cmd_send(message: types.Message):
    user_id = str(message.from_user.id)
    
    if user_id not in data["balances"]:
        await message.answer("Сначала нажмите /start чтобы зарегистрироваться 🎀")
        return
        
    parts = message.text.split()
    if len(parts) != 3:
        await message.answer("Используйте: /send @юзернейм количество")
        return

    username = parts[1].lstrip("@").lower()
    try:
        amount = int(parts[2])
    except ValueError:
        await message.answer("Введите число аюоинов!")
        return

    if username not in data["usernames"]:
        await message.answer("Такого пользователя нет в базе... 🥺 (попроси его нажать /start чтобы зарегистрироваться)")
        return

    receiver_id = data["usernames"][username]

    if data["balances"].get(user_id, 0) < amount:
        await message.answer("Недостаточно аюоинов 💔")
        return

    data["balances"][user_id] -= amount
    data["balances"][receiver_id] = data["balances"].get(receiver_id, 0) + amount
    save_data(data)

    await message.answer(f"Вы отправили @{username} {amount} аюоинов! ^^ спасибо! 🎀")
    try:
        await bot.send_message(
            receiver_id,
            f"Пользователь @{message.from_user.username} отправил вам {amount} аюоинов! Спасибо ^^~ 💕"
        )
    except:
        await message.answer("Не удалось уведомить получателя, но перевод выполнен 🎀")

@dp.callback_query(F.data == "balance")
async def balance_callback(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    
    if user_id not in data["balances"]:
        await callback.answer("Сначала нажмите /start чтобы зарегистрироваться 🎀", show_alert=True)
        return
        
    bal = data["balances"].get(user_id, 0)
    await callback.message.answer(f"Твой баланс... {bal} аюоинов! 💖")
    await callback.answer()

@dp.callback_query(F.data == "send")
async def send_callback(callback: types.CallbackQuery, state: FSMContext):
    user_id = str(callback.from_user.id)
    
    if user_id not in data["balances"]:
        await callback.answer("Сначала нажмите /start чтобы зарегистрироваться 🎀", show_alert=True)
        return
        
    await callback.message.answer(
        "Отправьте другому человеку аюоины ^^ ~\n"
        "Для этого напишите его @юзернейм 💕"
    )
    await state.set_state(Transfer.waiting_for_user)
    await callback.answer()

@dp.message(Transfer.waiting_for_user)
async def process_user(message: types.Message, state: FSMContext):
    username = message.text.lstrip("@").lower()
    if username not in data["usernames"]:
        await message.answer("Такого пользователя нет в базе... 🥺 (попроси его нажать /start чтобы зарегистрироваться)")
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

    data["balances"][sender_id] -= amount    
    data["balances"][receiver_id] = data["balances"].get(receiver_id, 0) + amount    
    save_data(data)    

    await message.answer(f"Вы отправили @{receiver_username} {amount} аюоинов! ^^ спасибо! 🎀")
    try:    
        await bot.send_message(    
            receiver_id,    
            f"Пользователь @{message.from_user.username} отправил вам {amount} аюоинов! Спасибо ^^~ 💕"    
        )    
    except:    
        await message.answer("Не удалось уведомить получателя, но перевод выполнен 🎀")

    await state.clear()

@dp.message(Command("newpromo"))
async def new_promo(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Недостаточно прав 🎀")
        return
        
    parts = message.text.split()
    if len(parts) != 3:
        await message.answer("Формат: /newpromo название число")
        return
        
    code, reward = parts[1], parts[2]
    try:
        reward = int(reward)
    except ValueError:
        await message.answer("Нужно указать число награды!")
        return

    data["promocodes"][code] = {"reward": reward, "created_at": time.time()}    
    save_data(data)    

    link = f"https://t.me/Ayuoin_bot?start={code}"    
    await message.answer(    
        f"💝Награда: {reward} коинов (срок действия 24 часа)\n"    
        f"Ссылка на промокод: {link}"    
    )

@dp.message(Command("promos"))
async def show_promos(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Недостаточно прав 🎀")
        return
        
    if not data["promocodes"]:
        await message.answer("Нет активных промокодов 🌸")
        return
        
    text = "Активные промокоды:\n"
    current_time = time.time()
    expired_promos = []
    
    for code, promo in data["promocodes"].items():
        time_passed = current_time - promo["created_at"]
        if time_passed < 86400:
            time_left = 86400 - time_passed
            hours_left = int(time_left // 3600)
            minutes_left = int((time_left % 3600) // 60)
            text += f"- {code} : +{promo['reward']} аюоинов (осталось: {hours_left}ч {minutes_left}м)\n"
        else:
            expired_promos.append(code)
    
    for code in expired_promos:
        del data["promocodes"][code]
    
    if expired_promos:
        save_data(data)
        text += f"\n🗑 Удалено {len(expired_promos)} истёкших промокодов"
    
    await message.answer(text)

async def on_startup(bot: Bot) -> None:
    await bot.set_webhook(WEBHOOK_URL)
    logger.info("Бот запущен с webhook! 🎀")

async def on_shutdown(bot: Bot) -> None:
    await bot.delete_webhook()
    logger.info("Бот остановлен! 🎀")

async def main_webhook():
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    app = web.Application()
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
    )
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)
    
    return app

async def main_polling():
    logger.info("Бот запущен в режиме polling! 🎀")
    await dp.start_polling(bot)

if __name__ == "__main__":
    # Для Render используем webhook, для локального тестирования - polling
    import os
    if os.getenv("RENDER"):
        web.run_app(main_webhook(), host="0.0.0.0", port=10000)
    else:
        asyncio.run(main_polling())
