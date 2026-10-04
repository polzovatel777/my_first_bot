import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiohttp import web

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = "8902950051:AAHEezrDT3kehQ22cm6w1_bz_j1UwPd7U5s"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- Клавиатуры ---

def get_main_reply_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.button(text="ℹ️ О боте")
    builder.button(text="🔗 Полезные ссылки")
    builder.adjust(2)  # Расположить по 2 кнопки в ряд
    return builder.as_markup(resize_keyboard=True)

def get_links_inline_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🌐 Наш сайт", url="https://python.org")
    builder.button(text="🎲 Нажми меня", callback_data="btn_click")
    builder.adjust(1)
    return builder.as_markup()

# --- Хэндлеры (Обработчики) ---

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer(
        "Привет! Я обновился и теперь умею работать с кнопками 🚀\nВыбери действие в меню ниже:",
        reply_markup=get_main_reply_keyboard()
    )

@dp.message(F.text == "ℹ️ О боте")
async def about_handler(message: types.Message):
    await message.answer("Я телеграм-бот, созданный на Python (aiogram 3) и работающий 24/7 на Render!")

@dp.message(F.text == "🔗 Полезные ссылки")
async def links_handler(message: types.Message):
    await message.answer(
        "Вот интерактивные inline-кнопки:",
        reply_markup=get_links_inline_keyboard()
    )

@dp.callback_query(F.data == "btn_click")
async def callback_handler(callback: types.CallbackQuery):
    await callback.answer("Ты нажал на inline-кнопку!", show_alert=True)
    await callback.message.edit_text("Вы успешно нажали на кнопкy! 🎉")

# --- Серверная частичка для Render ---

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