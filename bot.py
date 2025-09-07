import asyncio
import json
import time
from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

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
    except:
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

@dp.message(F.text.startswith("/start"))
async def start(message: types.Message):
    user_id = str(message.from_user.id)
    username = message.from_user.username
    args = message.text.split()

    # Автоматическое начисление 25 аюоинов новым пользователям
    if user_id not in data["balances"]:    
        data["balances"][user_id] = 25
        await message.answer("✨ Вам начислено 25 аюоинов за регистрацию! 🎀")
    
    if username:    
        data["usernames"][username.lower()] = user_id    

    if len(args) > 1:    
        code = args[1]    
        if code in data["promocodes"]:
            promo = data["promocodes"][code]
            if time.time() - promo["created_at"] < 86400 and user_id not in data["used_promos"].get(code, []):    
                reward = promo["reward"]    
                data["balances"][user_id] += reward    
                data["used_promos"].setdefault(code, []).append(user_id)    
                save_data(data)    
                await message.answer(f"✨ Промокод активирован! +{reward} аюоинов 🌸\nВаш баланс: {data['balances'][user_id]} аюоинов! 💖")
            else:
                await message.answer("Промокод недействителен или уже использован 🎀")

    save_data(data)    
    text = (    
        "Добро пожаловать!\n"    
        "Я аюоин, валюта tg канала: @ayuolmaoo (⁠.⁠❛⁠ᴗ⁠❛⁠.)\n\n"    
        "Благодаря мне можно:\n"    
        "Обменивать, продавать, покупать персонажей ;\n\n"    
        "🎀 Проверь свой баланс или отправь аюоины другу!"    
    )    
    await message.answer(text, reply_markup=main_menu)

@dp.message(F.text.startswith("/balance"))
async def cmd_balance(message: types.Message):
    user_id = str(message.from_user.id)
    
    # Проверка регистрации пользователя
    if user_id not in data["balances"]:
        await message.answer("Сначала нажмите /start чтобы зарегистрироваться 🎀")
        return
        
    bal = data["balances"].get(user_id, 0)
    await message.answer(f"Твой баланс... {bal} аюоинов! 💖")

@dp.message(F.text.startswith("/send"))
async def cmd_send(message: types.Message):
    user_id = str(message.from_user.id)
    
    # Проверка регистрации пользователя
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
        pass

@dp.callback_query(F.data == "balance")
async def balance(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    
    # Проверка регистрации пользователя
    if user_id not in data["balances"]:
        await callback.message.answer("Сначала нажмите /start чтобы зарегистрироваться 🎀")
        return
        
    bal = data["balances"].get(user_id, 0)
    await callback.message.answer(f"Твой баланс... {bal} аюоинов! 💖")

@dp.callback_query(F.data == "send")
async def send(callback: types.CallbackQuery, state: FSMContext):
    user_id = str(callback.from_user.id)
    
    # Проверка регистрации пользователя
    if user_id not in data["balances"]:
        await callback.message.answer("Сначала нажмите /start чтобы зарегистрироваться 🎀")
        return
        
    await callback.message.answer(
        "Отправьте другому человеку аюоины ^^ ~\n"
        "Для этого напишите его @юзернейм 💕"
    )
    await state.set_state(Transfer.waiting_for_user)

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
        pass    

    await state.clear()

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

    data["promocodes"][code] = {"reward": reward, "created_at": time.time()}    
    save_data(data)    

    link = f"https://t.me/Ayuoin_bot?start={code}"    
    await message.answer(    
        f"💝Награда: {reward} коинов (срок действия 24 часа)\n"    
        f"Ссылка на промокод: {link}"    
    )

@dp.message(F.text.startswith("/promos"))
async def show_promos(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    if not data["promocodes"]:
        await message.answer("Нет активных промокодов 🌸")
        return
    text = "Активные промокоды:\n"
    for code, promo in data["promocodes"].items():
        time_left = 86400 - (time.time() - promo["created_at"])
        hours_left = int(time_left // 3600)
        minutes_left = int((time_left % 3600) // 60)
        text += f"- {code} : +{promo['reward']} аюоинов (осталось: {hours_left}ч {minutes_left}м)\n"
    await message.answer(text)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
