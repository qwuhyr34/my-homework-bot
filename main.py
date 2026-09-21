import asyncio
import logging
import os
import aiohttp
import base64
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters.command import Command

logging.basicConfig(level=logging.INFO)

# ТВОИ ТОКЕНЫ
TELEGRAM_TOKEN = "8956965454:AAG4Dup2K8i6clQH83jaA9gMRcGYEw8wS3Y"
API_DUCK_KEY = "sk-cvc-15d7a1d9457a18e474075b145212bb2f9627f78b1de2dc21c243d99439d35efd"

bot = Bot(token=TELEGRAM_TOKEN) 
dp = Dispatcher()

# Мини-сервер для Render (чтобы не падал)
async def handle(request):
    return web.Response(text="Бот-глаз запущен!")

async def start_web_server():
    app = web.Application()
    app.add_routes([web.get('/', handle)])
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

# --- ЛОГИКА ОТПРАВКИ В CLAUDE ---
async def ask_claude(prompt, image_data=None):
    url = "https://apiduck.sytes.net/v1/chat/completions"
    headers = {"Authorization": f"Bearer {API_DUCK_KEY}", "Content-Type": "application/json"}
    
    # Если есть картинка, кодируем её в формат, который поймет Клод
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

# --- ОБРАБОТКА ФОТО ---
@dp.message(F.photo)
async def handle_photo(message: types.Message):
    status = await message.answer("Вижу фотку! Изучаю... 🧐")
    
    # Скачиваем фото в память
    photo = message.photo[-1]
    file_info = await bot.get_file(photo.file_id)
    file_content = await bot.download_file(file_info.file_path)
    
    # Переводим в Base64
    image_base64 = base64.b64encode(file_content.read()).decode('utf-8')
    
    try:
        answer = await ask_claude("Реши задачу на этой фотографии пошагово и понятно на русском языке.", image_base64)
        await status.delete()
        await message.answer(answer)
    except Exception as e:
        await status.edit_text(f"Ошибка при чтении фото: {str(e)}")

# --- ОБРАБОТКА ТЕКСТА ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Пришли фотку домашки или просто текст!")

@dp.message()
async def handle_text(message: types.Message):
    status = await message.answer("Думаю... 🧠")
    try:
        answer = await ask_claude(message.text)
        await status.delete()
        await message.answer(answer)
    except Exception as e:
        await status.edit_text(f"Ошибка: {str(e)}")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await start_web_server()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

