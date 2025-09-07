# ayuoin_bot.py
import asyncio
import os
import logging
import sqlite3
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ---------- Настройки ----------
API_TOKEN = os.getenv("API_TOKEN", "8458016571:AAFQpM-UjHR2nneYhwgDHECQILulwGTtapQ")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6218936231"))
DB_PATH = os.getenv("DB_PATH", "ayuoin.db")
PORT = int(os.getenv("PORT", 8080))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------- Aiogram init ----------
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# ---------- FSM ----------
class Transfer(StatesGroup):
    waiting_for_user = State()
    waiting_for_amount = State()

# ---------- Inline keyboard ----------
main_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Баланс °.•🎀", callback_data="balance")],
    [InlineKeyboardButton(text="Отправить °.•🎀", callback_data="send")]
])

# ---------- SQLite helper ----------
_conn = None

def init_db():
    global _conn
    _conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    _conn.row_factory = sqlite3.Row
    cur = _conn.cursor()
    # users: user_id text PK, username text, balance int
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            username TEXT,
            balance INTEGER NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS promocodes (
            code TEXT PRIMARY KEY,
            reward INTEGER NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS used_promos (
            code TEXT,
            user_id TEXT,
            PRIMARY KEY(code, user_id)
        )
    """)
    _conn.commit()

def get_user_row(user_id):
    cur = _conn.execute("SELECT * FROM users WHERE user_id = ?", (str(user_id),))
    return cur.fetchone()

def ensure_user(user_id, username=None):
    """Если пользователя нет — добавить с балансом 25. Если есть — обновить username при необходимости.
       Возвращает текущий баланс (int)."""
    u = get_user_row(user_id)
    if u is None:
        _conn.execute("INSERT INTO users (user_id, username, balance) VALUES (?, ?, ?)",
                      (str(user_id), username if username else None, 25))
        _conn.commit()
        return 25
    else:
        # обновляем username при изменении
        if username and (u["username"] != username):
            _conn.execute("UPDATE users SET username = ? WHERE user_id = ?", (username, str(user_id)))
            _conn.commit()
        return u["balance"]

def get_balance(user_id):
    row = _conn.execute("SELECT balance FROM users WHERE user_id = ?", (str(user_id),)).fetchone()
    return row["balance"] if row else None

def add_balance(user_id, amount):
    _conn.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, str(user_id)))
    _conn.commit()

def create_promo(code, reward):
    _conn.execute("INSERT OR REPLACE INTO promocodes (code, reward) VALUES (?, ?)", (code, int(reward)))
    _conn.commit()

def promo_activate(user_id, code):
    """Активировать промокод: вернуть (True, reward) при успехе; (False, reason) при неудаче."""
    row = _conn.execute("SELECT reward FROM promocodes WHERE code = ?", (code,)).fetchone()
    if not row:
        return False, "no_such"
    if _conn.execute("SELECT 1 FROM used_promos WHERE code = ? AND user_id = ?", (code, str(user_id))).fetchone():
        return False, "used"
    reward = int(row["reward"])
    try:
        cur = _conn.cursor()
        cur.execute("BEGIN")
        cur.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (reward, str(user_id)))
        cur.execute("INSERT INTO used_promos (code, user_id) VALUES (?, ?)", (code, str(user_id)))
        _conn.commit()
        return True, reward
    except Exception as e:
        _conn.rollback()
        logger.exception("promo activation failed")
        return False, "error"

def find_user_by_username(username):
    """Ищет user_id по username (без @), нечувствительно к регистру."""
    if not username:
        return None
    row = _conn.execute("SELECT user_id FROM users WHERE LOWER(username) = ?", (username.lower(),)).fetchone()
    return row["user_id"] if row else None

def transfer_atomic(sender_id, receiver_username, amount):
    """Атомарный перевод по username (без @). Возвращает (True, receiver_id) или (False, reason)."""
    if amount <= 0:
        return False, "invalid_amount"
    receiver_row = _conn.execute("SELECT user_id FROM users WHERE LOWER(username) = ?", (receiver_username.lower(),)).fetchone()
    if not receiver_row:
        return False, "no_user"
    receiver_id = receiver_row["user_id"]
    try:
        cur = _conn.cursor()
        cur.execute("BEGIN IMMEDIATE")
        srow = cur.execute("SELECT balance FROM users WHERE user_id = ?", (str(sender_id),)).fetchone()
        if not srow or srow["balance"] < amount:
            _conn.rollback()
            return False, "no_money"
        cur.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, str(sender_id)))
        cur.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, receiver_id))
        _conn.commit()
        return True, receiver_id
    except Exception:
        _conn.rollback()
        logger.exception("transfer failed")
        return False, "error"

# ---------- Handlers ----------
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = str(message.from_user.id)
    username = message.from_user.username  # could be None
    # гарантируем наличие в БД и подарок при первом заходе
    bal = ensure_user(user_id, username)
    # Если в /start передали аргумент — считаем это промокодом
    parts = (message.text or "").split()
    if len(parts) > 1:
        code = parts[1].strip()
        ok, info = promo_activate(user_id, code)
        if ok:
            # info — reward
            await message.answer("ура! промокод активировался! Поздравляю💝")
        else:
            if info == "used":
                await message.answer("Этот промокод уже использован вами ранее 🥺")
            elif info == "no_such":
                await message.answer("Такого промокода не существует 🥺")
            else:
                await message.answer("Ошибка активации промокода, попробуйте позже.")
    # Отправляем основное приветствие (одним сообщением)
    text = (
        "Добро пожаловать!\n"
        "Я аюоин, валюта tg канала: @ayuolmaoo (⁠.⁠❛⁠ᴗ⁠❛⁠.)\n\n"
        "Благодаря мне можно:\n"
        "Обменивать, продавать, покупать персонажей ;\n\n"
        "🎀 Проверь свой баланс или отправь аюоины другу!"
    )
    await message.answer(text, reply_markup=main_menu)

@dp.callback_query(F.data == "balance")
async def on_balance_query(callback: types.CallbackQuery):
    # обязательно ack
    await callback.answer()  # ack callback
    user_id = str(callback.from_user.id)
    bal = get_balance(user_id)
    if bal is None:
        # на всякий случай — создаём пользователя и даём подарок
        bal = ensure_user(user_id, callback.from_user.username)
    # Покажем баланс в alert (один раз, без дублей в чате)
    await callback.answer(f"Твой баланс: {bal} аюоинов 💖", show_alert=True)

@dp.callback_query(F.data == "send")
async def on_send_query(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()  # ack
    await callback.message.answer(
        "Отправьте другому человеку аюоины ^^ ~\n"
        "Для этого напишите его @юзернейм (например: @nick) 💕"
    )
    await state.set_state(Transfer.waiting_for_user)

@dp.message(Transfer.waiting_for_user)
async def process_user(message: types.Message, state: FSMContext):
    username = message.text.lstrip("@").strip()
    # проверим, есть ли юзер с таким username
    target_id = find_user_by_username(username)
    if not target_id:
        await message.answer("Такого пользователя нет в базе... 🥺 (попроси его нажать /start чтобы зарегистрироваться)")
        return
    await state.update_data(receiver=username)
    await message.answer("Введите число аюоинов для перевода ✨")
    await state.set_state(Transfer.waiting_for_amount)

@dp.message(Transfer.waiting_for_amount)
async def process_amount(message: types.Message, state: FSMContext):
    try:
        amount = int(message.text.strip())
    except:
        await message.answer("Введите корректное число!")
        return
    sender_id = str(message.from_user.id)
    data_state = await state.get_data()
    receiver_username = data_state.get("receiver")
    if not receiver_username:
        await message.answer("Ошибка: не найден получатель. Повторите попытку.")
        await state.clear()
        return
    ok, info = transfer_atomic(sender_id, receiver_username, amount)
    if not ok:
        if info == "no_user":
            await message.answer("Пользователь не найден.")
        elif info == "no_money":
            await message.answer("Недостаточно аюоинов 💔")
        elif info == "invalid_amount":
            await message.answer("Неверная сумма перевода.")
        else:
            await message.answer("Ошибка перевода, попробуйте позже.")
        await state.clear()
        return
    # Успешный перевод
    await message.answer(f"Вы отправили @{receiver_username} {amount} аюоинов! ^^ спасибо! 🎀")
    # попытаемся оповестить получателя
    try:
        await bot.send_message(info, f"Пользователь @{message.from_user.username} отправил вам {amount} аюоинов! Спасибо ^^~ 💕")
    except Exception:
        logger.exception("Не удалось отправить уведомление получателю")
    await state.clear()

# --- Admin: создать промокод ---
@dp.message(Command("newpromo"))
async def cmd_newpromo(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = (message.text or "").split()
    if len(parts) != 3:
        await message.answer("Формат: /newpromo название число")
        return
    code = parts[1].strip()
    try:
        reward = int(parts[2])
    except:
        await message.answer("Нужно указать число награды!")
        return
    create_promo(code, reward)
    link = f"https://t.me/{(await bot.get_me()).username}?start={code}"
    await message.answer(f"✨ Промокод создан: '{code}' (+{reward} аюоинов)\nСсылка для активации: {link}")

@dp.message(Command("promos"))
async def cmd_promos(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    rows = _conn.execute("SELECT code, reward FROM promocodes").fetchall()
    if not rows:
        await message.answer("Нет активных промокодов 🌸")
        return
    text = "Активные промокоды:\n"
    for r in rows:
        text += f"- {r['code']} : +{r['reward']} аюоинов\n"
    await message.answer(text)

# ---------- Web server (заглушка) ----------
async def handle_root(request):
    return web.Response(text="Ayuoin bot is running")

async def start_web_app():
    app = web.Application()
    app.add_routes([web.get("/", handle_root)])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info("Web app started on port %s", PORT)

# ---------- Startup / main ----------
async def main():
    init_db()
    # Удаляем webhook (если был установлен ранее) — чтобы избежать дублирующихся апдейтов
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Webhook deleted (drop_pending_updates=True)")
    except Exception:
        logger.exception("Failed to delete webhook")

    # запустим web-заглушку и polling параллельно
    await start_web_app()
    # start polling (blocking) - aiogram will keep running
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    finally:
        # Закрываем соединение с ботом
        try:
            asyncio.run(bot.session.close())
        except Exception:
            pass
