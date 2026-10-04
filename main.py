import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiohttp import web
from handlers import router
import database as db

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = "8902950051:AAHEezrDT3kehQ22cm6w1_bz_j1UwPd7U5s"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Подключаем роутер с обработчиками
dp.include_router(router)

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
    db.init_db()  # Инициализация базы данных
    await start_web_server()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())