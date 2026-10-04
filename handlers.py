import aiohttp
from aiogram import Router, types, F, Bot
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
import keyboards as kb
import database as db

router = Router()

# 🔴 Твой Telegram USER_ID
ADMIN_ID = 818535227[cite: 6]

# 🟢 Твоя ссылка на Google Apps Script для выгрузки в Google Таблицу
GOOGLE_SHEET_URL = "https://script.google.com/macros/s/AKfycbzQLDGNCvFKvOeYzpW9ZgZx_GpVxdnwPnjXOyXpCOHxP1vFWkJxve1A2OHfTsORGokYlw/exec"[cite: 5]

class Form(StatesGroup):
    name = State()[cite: 6]
    phone = State()[cite: 6]
    comment = State()[cite: 6]

async def send_to_google_sheet(data: dict):
    """Отправка заявки в Google Таблицу"""
    if not GOOGLE_SHEET_URL:
        return
    try:
        async with aiohttp.ClientSession() as session:
            await session.post(GOOGLE_SHEET_URL, json=data)
    except Exception as e:
        print(f"Ошибка отправки в Google Таблицу: {e}")

@router.message(CommandStart())
async def cmd_start(message: types.Message):
    db.add_user(message.from_user.id, message.from_user.username, message.from_user.first_name)[cite: 6]
    is_admin = (message.from_user.id == ADMIN_ID)[cite: 6]
    
    await message.answer(
        f"Здравствуйте, <b>{message.from_user.first_name}</b>! 👋\n\n"[cite: 6]
        f"Добро пожаловать. Мы принимаем и обрабатываем ваши заявки 24/7.\n"[cite: 6]
        f"Выберите нужное действие в меню ниже:",[cite: 6]
        parse_mode="HTML",[cite: 6]
        reply_markup=kb.get_main_keyboard(is_admin=is_admin)[cite: 6]
    )

@router.message(F.text == "❌ Отмена")
async def cancel_handler(message: types.Message, state: FSMContext):
    await state.clear()[cite: 6]
    is_admin = (message.from_user.id == ADMIN_ID)[cite: 6]
    await message.answer("Действие отменено.", reply_markup=kb.get_main_keyboard(is_admin=is_admin))[cite: 6]

# --- ПОШАГОВЫЙ ОПРОС КЛИЕНТА (FSM) ---

@router.message(F.text == "📝 Оставить заявку")
async def start_form(message: types.Message, state: FSMContext):
    await state.set_state(Form.name)[cite: 6]
    await message.answer("Как к вам обращаться? (Введите имя)", reply_markup=kb.get_cancel_keyboard())[cite: 6]

@router.message(Form.name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)[cite: 6]
    await state.set_state(Form.phone)[cite: 6]
    await message.answer("Укажите ваш номер телефона для связи:")[cite: 6]

@router.message(Form.phone)
async def process_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text)[cite: 6]
    await state.set_state(Form.comment)[cite: 6]
    await message.answer("Опишите коротко вашу задачу или вопрос:")[cite: 6]

@router.message(Form.comment)
async def process_comment(message: types.Message, state: FSMContext, bot: Bot):
    user_data = await state.get_data()[cite: 6]
    name = user_data['name'][cite: 6]
    phone = user_data['phone'][cite: 6]
    comment = message.text[cite: 6]
    
    # 1. Сохраняем в локальную БД SQLite
    db.add_request(message.from_user.id, name, phone, comment)[cite: 6]

    # 2. Автоматическая выгрузка в Google Таблицу
    await send_to_google_sheet({
        "name": name,
        "phone": phone,
        "comment": comment,
        "user_id": message.from_user.id
    })
    
    await state.clear()[cite: 6]
    
    is_admin = (message.from_user.id == ADMIN_ID)[cite: 6]
    await message.answer(
        "✅ <b>Спасибо! Ваша заявка успешно принята.</b>\nМенеджер свяжется с вами в ближайшее время.",[cite: 6]
        parse_mode="HTML",[cite: 6]
        reply_markup=kb.get_main_keyboard(is_admin=is_admin)[cite: 6]
    )

    # 3. Мгновенное уведомление администратору в Telegram
    if ADMIN_ID:
        try:
            username = f"@{message.from_user.username}" if message.from_user.username else "нет username"[cite: 6]
            admin_text = (
                f"🚨 <b>НОВАЯ ЗАЯВКА!</b>\n\n"[cite: 6]
                f"👤 <b>Имя:</b> {name}\n"[cite: 6]
                f"📞 <b>Телефон:</b> {phone}\n"[cite: 6]
                f"💬 <b>Комментарий:</b> {comment}\n"[cite: 6]
                f"🔗 <b>Профиль:</b> {username} (ID: {message.from_user.id})"[cite: 6]
            )
            await bot.send_message(chat_id=ADMIN_ID, text=admin_text, parse_mode="HTML")[cite: 6]
        except Exception as e:
            print(f"Ошибка отправки админу: {e}")[cite: 6]

# --- ИНФОРМАЦИЯ И АДМИНКА ---

@router.message(F.text == "ℹ️ О компании")
async def info_handler(message: types.Message):
    await message.answer("Мы помогаем бизнесу автоматизировать прием заявок и работу с клиентами.")[cite: 6]

@router.message(F.text == "📞 Контакты")
async def contacts_handler(message: types.Message):
    await message.answer("Телефон: +7 (999) 999-99-99\nTelegram: @il_overdrive")[cite: 6]

# --- ВЫДАЧА СПИСКА ЗАЯВОК АДМИНИСТРАТОРУ ---

@router.message(Command("admin"))[cite: 6]
@router.message(F.text == "⚙️ Админ-панель")[cite: 6]
async def admin_panel(message: types.Message):
    if message.from_user.id != ADMIN_ID:[cite: 6]
        await message.answer("⛔ У вас нет доступа к этой команде.")[cite: 6]
        return

    requests = db.get_all_requests(limit=10)[cite: 6]
    if not requests:[cite: 6]
        await message.answer("📭 Заявок пока нет.")[cite: 6]
        return

    text = "📋 <b>Последние 10 заявок:</b>\n\n"[cite: 6]
    for req in requests:[cite: 6]
        req_id, name, phone, comment, created_at = req[cite: 6]
        text += (
            f"<b>#️{req_id}</b> | {created_at}\n"[cite: 6]
            f"👤 {name} | 📞 {phone}\n"[cite: 6]
            f"💬 {comment}\n"[cite: 6]
            f"-------------------------------\n"[cite: 6]
        )

    await message.answer(text, parse_mode="HTML")[cite: 6]