import asyncio
import logging
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command

logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = "8956965454:AAE59cdRPbtr6yz4vAwH0akzRvQNUogAbiI"
API_DUCK_KEY = "sk-cvc-15d7a1d9457a18e474075b145212bb2f9627f78b1de2dc21c243d99439d35efd"

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Салют, бро! 🎓\n\n"
        "Я твой личный ИИ-решебник на базе Claude.\n"
        "Отправь мне текст домашнего задания, и я всё решу!"
    )


@dp.message()
async def ask_chatgpt(message: types.Message):
    status_message = await message.answer("Секунду, штурмую базу знаний... 🧠")

    url = "https://api.api-duck.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_DUCK_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "claude-sonnet-4-6",
        "messages": [
            {"role": "system",
             "content": "Ты — крутой школьный репетитор. Решай задачи пошагово и понятно на русском языке."},
            {"role": "user", "content": message.text}
        ]
    }

    try:
        timeout = aiohttp.ClientTimeout(total=90)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, json=data, headers=headers, ssl=False) as response:
                if response.status == 200:
                    result = await response.json()
                    answer = result['choices'][0]['message']['content']
                    await status_message.delete()
                    await message.answer(answer)
                else:
                    error_text = await response.text()
                    await status_message.delete()
                    await message.answer(f"Ошибка сервера ИИ (Код {response.status}):\n`{error_text}`")

    except Exception as e:
        await status_message.delete()
        await message.answer(f"Сетевая ошибка: `{repr(e)}`")


async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
