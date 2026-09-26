import asyncio
import logging
import os
import aiohttp
import base64
import sqlite3
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters.command import Command
from aiogram.enums import ChatAction

logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = "8956965454:AAE59cdRPbtr6yz4vAwH0akzRvQNUogAbiI"
API_DUCK_KEY = "sk-cvc-15d7a1d9457a18e474075b145212bb2f9627f78b1de2dc21c243d99439d35efd"

# ID Твоего аккаунта в Телеграме (чтобы только ТЫ мог смотреть статистику)
# Узнать свой ID можно в боте @myidbot (просто отправь ему любое сообщение)
ADMIN_ID = 0  # <-- ВСТАВЬ СУДА СВОЙ TELEGRAM ID (число без кавычек)

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# --- РАБОТА С БАЗОЙ ДАННЫХ (SQLite) ---
def init_db():
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY
        )
    """)
    conn.commit()
    conn.close()

def add_user(user_id: int):
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

def get_users_count() -> int:
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    conn.close()
    return count

# --- ВЕБ-СЕРВЕР ДЛЯ RENDER ---
async def handle(request):
    return web.Response(text="Бот работает!")

# --- ЗАПРОС К CLAUDE ---
async def ask_claude(prompt, image_data=None):
    url = "https://apiduck.sytes.net/v1/chat/completions"
    headers = {"Authorization": f"Bearer {API_DUCK_KEY}", "Content-Type": "application/json"}
    
    content = [{"type": "text", "text": prompt}]
    if image_data:
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}
        })

    data = {
        "model": "claude-sonnet-4-6",
        "messages": [{"role": "user", "content": content}]
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data, headers=headers, ssl=False) as resp:
            res = await resp.json()
            return res['choices'][0]['message']['content']

# --- КОМАНДЫ БОТА ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    add_user(message.from_user.id) # Сохраняем юзера
    await message.answer("Пришли фотку домашки или просто текст!")

# Команда для проверки статистики (только для тебя или для всех)
@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    add_user(message.from_user.id)
    count = get_users_count()
    await message.answer(f"📊 **Статистика бота:**\n\nВсего пользователей: **{count}**", parse_mode="Markdown")

@dp.message(F.photo)
async def handle_photo(message: types.Message):
    add_user(message.from_user.id) # Сохраняем юзера
    await bo
t.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    try:
        photo = message.photo[-1]
        file_content = await bot.download(photo)
        image_base64 = base64.b64encode(file_content.read()).decode('utf-8')
        answer = await ask_claude("Реши задачу на этой фотографии пошагово.", image_base64)
        await message.answer(answer)
    except Exception as e:
        await message.answer(f"Ошибка: {str(e)}")

@dp.message()
async def handle_text(message: types.Message):
    add_user(message.from_user.id) # Сохраняем юзера
    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    try:
        answer = await ask_claude(message.text)
        await message.answer(answer)
    except Exception as e:
        await message.answer(f"Ошибка: {str(e)}")

async def main():
    init_db() # Инициализируем базу данных при старте
    
    app = web.Application()
    app.add_routes([web.get('/', handle)])
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
