import logging
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import asyncio

API_TOKEN = 8458016571:AAFQpM-UjHR2nneYhwgDHECQILulwGTtapQ

ADMIN_ID = 6218936231

logging.basicConfig(level=logging.INFO)

# Создаём бота и диспетчер
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Подключаем SQLite
conn = sqlite3.connect("balances.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    balance INTEGER
)
""")
conn.commit()

def get_balance(user_id: int):
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    return row[0] if row else None

def set_balance(user_id: int, balance: int):
    cursor.execute("INSERT OR REPLACE INTO users (user_id, balance) VALUES (?, ?)", (user_id, balance))
    conn.commit()

def add_coins(user_id: int, amount: int):
    bal = get_balance(user_id)
    if bal is None:
        set_balance(user_id, amount)
    else:
        set_balance(user_id, bal + amount)

# /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    if get_balance(user_id) is None:
        set_balance(user_id, 25)
    await message.answer(f"Привет, {message.from_user.first_name}! 🎉\n"
                         f"На твой счёт зачислено 25 аюойнов.\n"
                         f"Напиши /balance чтобы проверить баланс.")

# /balance
@dp.message(Command("balance"))
async def cmd_balance(message: types.Message):
    user_id = message.from_user.id
    bal = get_balance(user_id)
    if bal is None:
        bal = 0
    await message.answer(f"Твой баланс: {bal} аюойнов 🪙")

# /give user_id amount
@dp.message(Command("give"))
async def cmd_give(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("У тебя нет прав на эту команду.")
    try:
        parts = message.text.split()
        user_id = int(parts[1])
        amount = int(parts[2])
        add_coins(user_id, amount)
        await message.answer(f"Выдано {amount} аюойнов пользователю {user_id}.")
    except Exception:
        await message.answer("Использование: /give user_id количество\nПример: /give 123456789 25")

# Запуск
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())