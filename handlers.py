import asyncio
import aiohttp
from aiogram import Router, types, F, Bot
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
import keyboards as kb
import database as db

router = Router()

# 🔴 Твой Telegram USER_ID
ADMIN_ID = 818535227

# 🟢 Ссылка на Google Apps Script
GOOGLE_SHEET_URL = "https://script.google.com/macros/s/AKfycbzQLDGNCvFKvOeYzpW9ZgZx_GpVxdnwPnjXOyXpCOHxP1vFWkJxve1A2OHfTsORGokYlw/exec"

class Form(StatesGroup):
    name = State()
    phone = State()
    comment = State()

class BroadcastForm(StatesGroup):
    text = State()
    confirm = State()

async def send_to_google_sheet(data: dict):
    """Отправка заявки в Google Таблицу"""
    if not GOOGLE_SHEET_URL:
        return
    try:
        async with aiohttp.ClientSession() as session:
            await session.post(GOOGLE_SHEET_URL, json=data)
    except Exception as e:
        print(f"Ошибка отправки в Google Таблицу: {e}")

async def update_google_sheet_status(user_id: int, status_text: str):
    """Обновление статуса заявки в Google Таблице"""
    if not GOOGLE_SHEET_URL:
        return
    try:
        async with aiohttp.ClientSession() as session:
            await session.post(
                GOOGLE_SHEET_URL, 
                json={
                    "action": "update_status",
                    "user_id": user_id,
                    "status": status_text
                }
            )
    except Exception as e:
        print(f"Ошибка обновления статуса в Google Таблице: {e}")

# --- ФОНОВАЯ ЗАДАЧА РАССЫЛКИ ---

async def run_broadcast_task(bot: Bot, text_to_send: str, admin_id: int):
    """Выполняется в фоновом режиме, не блокируя основной поток бота"""
    try:
        users = db.get_all_users()
    except Exception as e:
        await bot.send_message(
            chat_id=admin_id,
            text=f"❌ <b>Ошибка базы данных при рассылке:</b> {e}",
            parse_mode="HTML"
        )
        return

    if not users:
        await bot.send_message(
            chat_id=admin_id,
            text="⚠️ <b>Список пользователей пуст.</b> Рассылка не выполнена.",
            parse_mode="HTML",
            reply_markup=kb.get_main_keyboard(is_admin=True)
        )
        return

    success_count = 0
    failed_count = 0

    for user in users:
        user_id = user[0]
        try:
            await bot.send_message(chat_id=user_id, text=text_to_send, parse_mode="HTML")
            success_count += 1
            await asyncio.sleep(0.05)  # Защита от Flood limits
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after)
            try:
                await bot.send_message(chat_id=user_id, text=text_to_send, parse_mode="HTML")
                success_count += 1
            except Exception:
                failed_count += 1
        except TelegramForbiddenError:
            failed_count += 1
        except Exception as e:
            print(f"Ошибка отправки пользователю {user_id}: {e}")
            failed_count += 1

    await bot.send_message(
        chat_id=admin_id,
        text=(
            f"🎉 <b>РАССЫЛКА ЗАВЕРШЕНА!</b>\n\n"
            f"📨 Успешно доставлено: <b>{success_count}</b>\n"
            f"🚫 Ошибок (заблокировали бота/удалены): <b>{failed_count}</b>"
        ),
        parse_mode="HTML",
        reply_markup=kb.get_main_keyboard(is_admin=True)
    )

# --- КОМАНДЫ И ОБРАБОТЧИКИ ---

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
    await message.answer(
        "Нажмите кнопку ниже, чтобы поделиться контактом, или введите номер вручную:", 
        reply_markup=kb.get_phone_keyboard()
    )

@router.message(Form.phone, F.contact)
@router.message(Form.phone, F.text)
async def process_phone(message: types.Message, state: FSMContext):
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
    client_id = message.from_user.id
    
    # 1. Сохраняем в локальную БД SQLite
    db.add_request(client_id, name, phone, comment)

    # 2. Автоматическая выгрузка в Google Таблицу
    await send_to_google_sheet({
        "name": name,
        "phone": phone,
        "comment": comment,
        "user_id": client_id
    })
    
    await state.clear()
    
    is_admin = (client_id == ADMIN_ID)
    await message.answer(
        "✅ <b>Спасибо! Ваша заявка успешно принята.</b>\nМенеджер свяжется с вами в ближайшее время.",
        parse_mode="HTML",
        reply_markup=kb.get_main_keyboard(is_admin=is_admin)
    )

    # 3. Мгновенное уведомление администратору
    if ADMIN_ID:
        try:
            username = f"@{message.from_user.username}" if message.from_user.username else "нет username"
            admin_text = (
                f"🚨 <b>НОВАЯ ЗАЯВКА!</b>\n\n"
                f"👤 <b>Имя:</b> {name}\n"
                f"📞 <b>Телефон:</b> {phone}\n"
                f"💬 <b>Комментарий:</b> {comment}\n"
                f"🔗 <b>Профиль:</b> {username} (ID: {client_id})"
            )
            
            status_kb = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ В работу", callback_data=f"status_work_{client_id}"),
                    InlineKeyboardButton(text="❌ Отклонить", callback_data=f"status_cancel_{client_id}")
                ]
            ])
            
            await bot.send_message(chat_id=ADMIN_ID, text=admin_text, parse_mode="HTML", reply_markup=status_kb)
        except Exception as e:
            print(f"Ошибка отправки админу: {e}")

# --- ОБРАБОТКА СТАТУСОВ И УВЕДОМЛЕНИЕ КЛИЕНТА ---

@router.callback_query(F.data.startswith("status_"))
async def process_status_change(callback: types.CallbackQuery, bot: Bot):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("У вас нет доступа.", show_alert=True)
        return

    data_parts = callback.data.split("_")
    action_type = data_parts[1]
    target_user_id = int(data_parts[2]) if len(data_parts) > 2 else None

    if action_type == "work":
        status_text = "взята в работу ✅"
        sheet_status = "🟡 В работе"
        user_notify_text = "🟡 <b>Обновление по вашей заявке:</b>\nВаша заявка взята в работу! Менеджер уже занимается вашим вопросом."
    else:
        status_text = "отклонена ❌"
        sheet_status = "🔴 Отклонена"
        user_notify_text = "🔴 <b>Обновление по вашей заявке:</b>\nК сожалению, ваша заявка отклонена. Если у вас возникли вопросы, вы можете связаться с нами через контакты."

    await callback.message.edit_text(
        f"{callback.message.text}\n\n📌 <b>Статус:</b> Заявка {status_text}",
        parse_mode="HTML"
    )
    await callback.answer(f"Заявка {status_text}")

    if target_user_id:
        # 1. Обновляем статус в Google Таблице в фоновом режиме
        asyncio.create_task(update_google_sheet_status(target_user_id, sheet_status))
        
        # 2. Уведомляем клиента в Telegram
        try:
            await bot.send_message(chat_id=target_user_id, text=user_notify_text, parse_mode="HTML")
        except Exception as e:
            print(f"Не удалось отправить уведомление пользователю {target_user_id}: {e}")

# --- МОДУЛЬ РАССЫЛКИ (ПО КНОПКЕ "📢 Сделать рассылку") ---

@router.message(Command("broadcast"))
@router.message(F.text.contains("Сделать рассылку"))
async def start_broadcast(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ У вас нет доступа к этой функции.")
        return

    await state.set_state(BroadcastForm.text)
    await message.answer(
        "📢 <b>Введите текст для рассылки всем пользователям:</b>",
        parse_mode="HTML",
        reply_markup=kb.get_cancel_keyboard()
    )

@router.message(BroadcastForm.text)
async def process_broadcast_text(message: types.Message, state: FSMContext):
    await state.update_data(broadcast_text=message.text)
    await state.set_state(BroadcastForm.confirm)

    confirm_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🚀 Отправить рассылку", callback_data="confirm_broadcast"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_broadcast")
        ]
    ])

    await message.answer(
        f"<b>Проверьте текст рассылки:</b>\n\n{message.text}\n\n<i>Отправить сообщение всем пользователям?</i>",
        parse_mode="HTML",
        reply_markup=confirm_kb
    )

@router.callback_query(F.data.in_(["confirm_broadcast", "cancel_broadcast"]))
async def execute_broadcast(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    if callback.from_user.id != ADMIN_ID:
        return

    if callback.data == "cancel_broadcast":
        await state.clear()
        is_admin = (callback.from_user.id == ADMIN_ID)
        await callback.message.edit_text("❌ Рассылка отменена.")
        await callback.message.answer("Главное меню:", reply_markup=kb.get_main_keyboard(is_admin=is_admin))
        await callback.answer()
        return

    data = await state.get_data()
    text_to_send = data.get("broadcast_text")
    await state.clear()

    # Изменяем сообщение на «Начинаю рассылку...»
    await callback.message.edit_text("⏳ <b>Начинаю рассылку...</b>", parse_mode="HTML")
    await callback.answer()

    # Запускаем фоновую задачу для отправки
    asyncio.create_task(run_broadcast_task(bot, text_to_send, callback.from_user.id))

# --- ИНФОРМАЦИЯ И АДМИНКА ---

@router.message(Command("export"))
@router.message(F.text.contains("Скачать базу"))
async def export_users_handler(message: types.Message):
    """Выгрузка файла со всеми пользователями"""
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ У вас нет доступа к этой команде.")
        return

    msg = await message.answer("⏳ Готовлю файл с базой пользователей...")

    try:
        if hasattr(db, 'export_users_csv'):
            csv_file = db.export_users_csv()
            document = BufferedInputFile(csv_file.getvalue(), filename="users_base.csv")

            await message.answer_document(
                document=document,
                caption="📊 <b>Выгрузка базы пользователей</b>\n\nФайл готов и отформатирован для открытия в Excel."
            )
            await msg.delete()
        else:
            await msg.edit_text("⚠️ Функция export_users_csv еще не добавлена в database.py")
    except Exception as e:
        await message.answer(f"❌ Ошибка при формировании файла: {e}")

@router.message(F.text.contains("О компании"))
async def info_handler(message: types.Message):
    await message.answer(
        "ℹ️ <b>О компании</b>\n\n"
        "Мы помогаем бизнесу автоматизировать прием заявок, работу с клиентами и выгрузку данных в Google Таблицы 24/7.",
        parse_mode="HTML"
    )

@router.message(F.text.contains("Контакты"))
async def contacts_handler(message: types.Message):
    await message.answer(
        "📞 <b>Наши контакты:</b>\n\n"
        "Телефон: +7 (999) 999-99-99\n"
        "Telegram для связи: @il_overdrive",
        parse_mode="HTML"
    )

@router.message(Command("admin"))
@router.message(F.text.contains("Админ-панель"))
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
            f"<b>#{req_id}</b> | {created_at}\n"
            f"👤 {name} | 📞 {phone}\n"
            f"💬 {comment}\n"
            f"-------------------------------\n"
        )

    await message.answer(text, parse_mode="HTML")