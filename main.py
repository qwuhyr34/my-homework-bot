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

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8956965454:AAGTHK_bpqnW12LMwrqlQeL92yuTpUgI9Og")
API_DUCK_KEY = os.getenv("API_DUCK_KEY", "sk-cvc-15d7a1d9457a18e474075b145212bb2f9627f78b1de2dc21c243d99439d35efd")

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

DB_NAME = "jorik_memory.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            role TEXT,
            content TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_message(user_id: int, role: str, content: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO history (user_id, role, content) VALUES (?, ?, ?)", (user_id, role, content))
    conn.commit()
    conn.close()

def get_history(user_id: int, limit: int = 6):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT role, content FROM history WHERE user_id = ? ORDER BY id DESC LIMIT ?", (user_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return [{"role": r[0], "content": r[1]} for r in reversed(rows)]

def clear_history(user_id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM history WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

async def ask_claude(user_id: int, prompt: str, image_data=None):
    url = "https://apiduck.servepics.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_DUCK_KEY}", 
        "Content-Type": "application/json"
    }

    messages = [
        {
            "role": "system", 
            "content": ""
        }
    ]

    past_history = get_history(user_id, limit=6)
    messages.extend(past_history)

    if image_data:
        current_content = [
            {"type": "text", "text": prompt},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}
            }
        ]
    else:
        current_content = prompt

    messages.append({"role": "user", "content": current_content})

    data = {
        "model": "claude-sonnet-4-6",
        "messages": messages
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data, headers=headers, ssl=False) as resp:
            if resp.status != 200:
                err_text = await resp.text()
                logging.error(f"Ошибка сервера {resp.status}: {err_text}")
                raise Exception(f"Ошибка сервера ({resp.status})")
                
            res = await resp.json()
            answer_text = res['choices'][0]['message']['content']

            save_message(user_id, "user", prompt)
            save_message(user_id, "assistant", answer_text)

            return answer_text

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(".")

@dp.message(Command("clear"))
async def cmd_clear(message: types.Message):
    clear_history(message.chat.id)
    await message.answer("Память очищена, бро! Начинаем с чистого листа 🧼🐶")

@dp.message(F.photo)
async def handle_photo(message: types.Message):
    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    try:
        photo = message.photo[-1]
        file_content = await bot.download(photo)
        image_base64 = base64.b64encode(file_content.read()).decode('utf-8')
        
        caption = message.caption if message.caption else "Реши задачу на этой фотографии пошагово."
        answer = await ask_claude(message.chat.id, caption, image_base64)
        await message.answer(answer)
    except Exception as e:
        await message.answer(f"Ошибка: {str(e)}")

@dp.message()
async def handle_text(message: types.Message):
    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    try:
        answer = await ask_claude(message.chat.id, message.text)
        await message.answer(answer)
    except Exception as e:
        await message.answer(f"Ошибка: {str(e)}")

async def handle(request):
    return web.Response(text="Жорик работает и помнит всё!")

async def main():
    init_db()

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
