import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiohttp import web

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = "8902950051:AAHEezrDT3kehQ22cm6w1_bz_j1UwPd7U5s"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer("Привет! Я работаю на бесплатном сервере Render 24/7 🚀")

# Заглушка для Render Web Service (чтобы сервер слушал порт)
async def handle(request):
    return web.Response(text="Bot is running!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

async def main():
    await start_web_server()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())