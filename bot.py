import asyncio
import json
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

API_TOKEN = "8458016571:AAFQpM-UjHR2nneYhwgDHECQILulwGTtapQ"
ADMIN_ID = 6218936231  # твой айди

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Хранилище данных
USERS_FILE = "users.json"
PROMO_FILE = "promocodes.json"


# ============ Работа с файлами ============
def load_data(file, default):
    try:
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default


def save_data(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def get_users():
    return load_data(USERS_FILE, {})


def save_users(users):
    save_data(USERS_FILE, users)


def get_promos():
    return load_data(PROMO_FILE, {})


def save_promos(promos):
    save_data(PROMO_FILE, promos)


# ============ Основные функции ============
def get_balance(user_id):
    users = get_users()
    return users.get(str(user_id), {}).get("balance", 0)


def update_balance(user_id, amount):
    users = get_users()
    uid = str(user_id)
    if uid not in users:
        users[uid] = {"balance": 0, "first_bonus": False}
    users[uid]["balance"] = users[uid].get("balance", 0) + amount
    save_users(users)
    return users[uid]["balance"]


def set_first_bonus(user_id):
    users = get_users()
    uid = str(user_id)
    if uid not in users:
        users[uid] = {"balance": 0, "first_bonus": False}
    if not users[uid]["first_bonus"]:
        users[uid]["balance"] += 25
        users[uid]["first_bonus"] = True
    save_users(users)
    return users[uid]["balance"]


# ============ Команды ============
@dp.message(F.text == "/start")
async def start_cmd(message: types.Message):
    balance = set_first_bonus(message.from_user.id)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Баланс", callback_data="balance")],
            [InlineKeyboardButton(text="Отправить", callback_data="send")],
            [InlineKeyboardButton(text="Активировать промокод", callback_data="activate")],
        ]
    )
    await message.answer(
        f"👋 Привет, {message.from_user.first_name}!\n"
        f"На твой баланс начислено +25 коинов 🎉\n"
        f"Текущий баланс: {balance} коинов.",
        reply_markup=kb
    )


@dp.callback_query(F.data == "balance")
async def check_balance(callback: types.CallbackQuery):
    balance = get_balance(callback.from_user.id)
    await callback.message.answer(f"💰 Твой баланс: {balance} коинов")


@dp.message(F.text == "/balance")
async def balance_cmd(message: types.Message):
    balance = get_balance(message.from_user.id)
    await message.answer(f"💰 Твой баланс: {balance} коинов")


@dp.callback_query(F.data == "send")
async def send_btn(callback: types.CallbackQuery):
    await callback.message.answer("Чтобы отправить: напиши команду в формате:\n/send ID_ПОЛУЧАТЕЛЯ СУММА")


@dp.message(F.text.startswith("/send"))
async def send_cmd(message: types.Message):
    try:
        _, target_id, amount = message.text.split()
        target_id, amount = int(target_id), int(amount)

        if get_balance(message.from_user.id) < amount:
            await message.answer("❌ Недостаточно средств.")
            return

        update_balance(message.from_user.id, -amount)
        new_balance_sender = get_balance(message.from_user.id)

        update_balance(target_id, amount)
        new_balance_receiver = get_balance(target_id)

        await message.answer(
            f"✅ Перевод успешен!\n"
            f"📤 Ты отправил {amount} коинов пользователю {target_id}.\n"
            f"💰 Твой баланс: {new_balance_sender} коинов."
        )
        await bot.send_message(
            target_id,
            f"📥 Ты получил {amount} коинов от {message.from_user.id}.\n"
            f"💰 Твой баланс: {new_balance_receiver} коинов."
        )

    except:
        await message.answer("⚠ Ошибка! Используй: /send ID СУММА")


# ============ Промокоды ============
@dp.message(F.text.startswith("/createpromo"))
async def create_promo(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ У тебя нет прав для создания промокода.")
        return

    try:
        _, code, reward = message.text.split()
        reward = int(reward)

        promos = get_promos()
        promos[code] = {
            "reward": reward,
            "expires": (datetime.now() + timedelta(days=1)).isoformat()
        }
        save_promos(promos)

        await message.answer(f"🎁 Промокод создан!\nКод: {code}\nНаграда: {reward} коинов (срок действия 24 часа)")

    except:
        await message.answer("⚠ Ошибка! Используй: /createpromo КОД НАГРАДА")


@dp.callback_query(F.data == "activate")
async def activate_btn(callback: types.CallbackQuery):
    await callback.message.answer("Введи команду: /promo КОД")


@dp.message(F.text.startswith("/promo"))
async def promo_cmd(message: types.Message):
    try:
        _, code = message.text.split()
        promos = get_promos()

        if code not in promos:
            await message.answer("❌ Промокод недействителен.")
            return

        promo = promos[code]
        if datetime.now() > datetime.fromisoformat(promo["expires"]):
            await message.answer("⏰ Срок действия промокода истёк.")
            return

        reward = promo["reward"]
        new_balance = update_balance(message.from_user.id, reward)

        del promos[code]
        save_promos(promos)

        await message.answer(
            f"🎉 Ура! Промокод активирован.\n"
            f"💝 Тебе начислено {reward} коинов.\n"
            f"💰 Текущий баланс: {new_balance} коинов."
        )
    except:
        await message.answer("⚠ Ошибка! Используй: /promo КОД")


# ============ Запуск ============
async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
