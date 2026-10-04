import aiohttp
from aiogram import Router, types, F, Bot
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import keyboards as kb
import database as db

router = Router()

# 🔴 Твой Telegram USER_ID
ADMIN_ID = 818535227

# 🟢 Твоя ссылка на Google Apps Script для выгрузки в Google Таблицу
GOOGLE_SHEET_URL = "https://script.google.com/macros/s/AKfycbzQLDGNCvFKvOeYzpW9ZgZx_GpVxdnwPnjXOyXpCOHxP1vFWkJxve1A2OHfTsORGokYlw/exec"

class Form(StatesGroup):
    name = State()
    phone = State()
    comment = State()

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
    db.add_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    is_admin = (message.from_user.id == ADMIN_ID)
    
    await message.answer(
        f"Здравствуйте, <b>{message.from_user.first_name}</b>! 👋\n\n"
        f"Добро пожаловать. Мы принимаем и обрабатываем ваши заявки 24/7.\n"
        f"Выберите нужное действие в меню ниже:",
        parse_mode="HTML",
        reply_markup=kb.get_main_keyboard(is_admin=is_admin)
    )

@router.message(F.text == "❌ Отмена")
async def cancel_handler(message: types.Message, state: FSMContext):
    await state.clear()
    is_admin = (message.from_user.id == ADMIN_ID)
    await message.answer("Действие отменено.", reply_markup=kb.get_main_keyboard(is_admin=is_admin))

# --- ПОШАГОВЫЙ ОПРОС КЛИЕНТА (FSM) ---

@router.message(F.text == "📝 Оставить заявку")
async def start_form(message: types.Message, state: FSMContext):
    await state.set_state(Form.name)
    await message.answer("Как к вам обращаться? (Введите имя)", reply_markup=kb.get_cancel_keyboard())

@router.message(Form.name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(Form.phone)
    # Показываем кнопку отправки контакта
    await message.answer(
        "Нажмите кнопку ниже, чтобы поделиться контактом, или введите номер вручную:", 
        reply_markup=kb.get_phone_keyboard()
    )

@router.message(Form.phone, F.contact)
@router.message(Form.phone, F.text)
async def process_phone(message: types.Message, state: FSMContext):
    # Получаем телефон через кнопку или из введенного текста
    if message.contact:
        phone = message.contact.phone_number
    else:
        phone = message.text

    await state.update_data(phone=phone)
    await state.set_state(Form.comment)
    await message.answer("Опишите коротко вашу задачу или вопрос:", reply_markup=kb.get_cancel_keyboard())

@router.message(Form.comment)
async def process_comment(message: types.Message, state: FSMContext, bot: Bot):
    user_data = await state.get_data()
    name = user_data['name']
    phone = user_data['phone']
    comment = message.text
    
    # 1. Сохраняем в локальную БД SQLite
    db.add_request(message.from_user.id, name, phone, comment)

    # 2. Автоматическая выгрузка в Google Таблицу
    await send_to_google_sheet({
        "name": name,
        "phone": phone,
        "comment": comment,
        "user_id": message.from_user.id
    })
    
    await state.clear()
    
    is_admin = (message.from_user.id == ADMIN_ID)
    await message.answer(
        "✅ <b>Спасибо! Ваша заявка успешно принята.</b>\nМенеджер свяжется с вами в ближайшее время.",
        parse_mode="HTML",
        reply_markup=kb.get_main_keyboard(is_admin=is_admin)
    )

    # 3. Мгновенное уведомление администратору с инлайн-кнопками статуса
    if ADMIN_ID:
        try:
            username = f"@{message.from_user.username}" if message.from_user.username else "нет username"
            admin_text = (
                f"🚨 <b>НОВАЯ ЗАЯВКА!</b>\n\n"
                f"👤 <b>Имя:</b> {name}\n"
                f"📞 <b>Телефон:</b> {phone}\n"
                f"💬 <b>Комментарий:</b> {comment}\n"
                f"🔗 <b>Профиль:</b> {username} (ID: {message.from_user.id})"
            )
            
            # Инлайн-кнопки управления заявкой прямо из чата
            status_kb = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ В работу", callback_data="status_work"),
                    InlineKeyboardButton(text="❌ Отклонить", callback_data="status_cancel")
                ]
            ])
            
            await bot.send_message(chat_id=ADMIN_ID, text=admin_text, parse_mode="HTML", reply_markup=status_kb)
        except Exception as e:
            print(f"Ошибка отправки админу: {e}")

# --- ОБРАБОТКА ИНЛАЙН-КНОПОК СТАТУСА ДЛЯ АДМИНА ---

@router.callback_query(F.data.startswith("status_"))
async def process_status_change(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("У вас нет доступа.", show_alert=True)
        return

    status_text = "взята в работу ✅" if callback.data == "status_work" else "отклонена ❌"
    
    # Обновляем текст сообщения, убирая кнопки
    await callback.message.edit_text(
        f"{callback.message.text}\n\n📌 <b>Статус:</b> Заявка {status_text}",
        parse_mode="HTML"
    )
    await callback.answer(f"Заявка {status_text}")

# --- ИНФОРМАЦИЯ И АДМИНКА ---

@router.message(F.text == "ℹ️ О компании")
async def info_handler(message: types.Message):
    await message.answer("Мы помогаем бизнесу автоматизировать прием заявок и работу с клиентами.")

@router.message(F.text == "📞 Контакты")
async def contacts_handler(message: types.Message):
    await message.answer("Телефон: +7 (999) 999-99-99\nTelegram: @il_overdrive")

# --- ВЫДАЧА СПИСКА ЗАЯВОК АДМИНИСТРАТОРУ ---

@router.message(Command("admin"))
@router.message(F.text == "⚙️ Админ-панель")
async def admin_panel(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ У вас нет доступа к этой команде.")
        return

    requests = db.get_all_requests(limit=10)
    if not requests:
        await message.answer("📭 Заявок пока нет.")
        return

    text = "📋 <b>Последние 10 заявок:</b>\n\n"
    for req in requests:
        req_id, name, phone, comment, created_at = req
        text += (
            f"<b>#️{req_id}</b> | {created_at}\n"
            f"👤 {name} | 📞 {phone}\n"
            f"💬 {comment}\n"
            f"-------------------------------\n"
        )

    await message.answer(text, parse_mode="HTML")