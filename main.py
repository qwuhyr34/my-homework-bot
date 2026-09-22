import asyncio
import logging
import os
import aiohttp
import base64
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters.command import Command
from aiogram.enums import ChatAction # <-- ДОБАВЛЕНО

logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = "8956965454:AAE59cdRPbtr6yz4vAwH0akzRvQNUogAbiI"
API_DUCK_KEY = "sk-cvc-15d7a1d9457a18e474075b145212bb2f9627f78b1de2dc21c243d99439d35efd"

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

async def handle(request):
    return web.Response(text="Бот работает!")

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
        "model": "gpt-5.4-mini",
        "messages": [{"role": "user", "content": content}]
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data, headers=headers, ssl=False) as resp:
            res = await resp.json()
            return res['choices'][0]['message']['content']

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Пришли фотку домашки или просто текст!")

@dp.message(F.photo)
async def handle_photo(message: types.Message):
    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING) # <-- ДОБАВЛЕНО
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
    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING) # <-- ДОБАВЛЕНО
    try:
        answer = await ask_claude(message.text)
        await message.answer(answer)
    except Exception as e:
        await message.answer(f"Ошибка: {str(e)}")

async def main():
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

