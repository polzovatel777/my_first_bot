import asyncio
import aiohttp
import re
import os
import pandas as pd
from aiogram import Router, types, F, Bot
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
import keyboards as kb
import database as db

router = Router()

ADMIN_ID = 818535227
GOOGLE_SHEET_URL = "https://script.google.com/macros/s/AKfycbzQLDGNCvFKvOeYzpW9ZgZx_GpVxdnwPnjXOyXpCOHxP1vFWkJxve1A2OHfTsORGokYlw/exec"

class Form(StatesGroup):
    name = State()
    phone = State()
    comment = State()

class BroadcastForm(StatesGroup):
    text = State()
    confirm = State()

async def send_to_google_sheet(data: dict):
    """Отправка данных в Google Таблицу"""
    if not GOOGLE_SHEET_URL:
        return
    try:
        async with aiohttp.ClientSession() as session:
            await session.post(GOOGLE_SHEET_URL, json=data)
    except Exception as e:
        print(f"Ошибка отправки в Google Таблицу: {e}")

# --- ФОНОВАЯ ЗАДАЧА РАССЫЛКИ ---

async def run_broadcast_task(bot: Bot, text_to_send: str, admin_id: int):
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
            await asyncio.sleep(0.05)
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

# --- ГЛОБАЛЬНАЯ ОТМЕНА И МЕНЮ ---

@router.message(F.text.in_(["❌ Отмена", "❌ Отменить заполнение"]))
async def cancel_handler(message: types.Message, state: FSMContext):
    await state.clear()
    is_admin = (message.from_user.id == ADMIN_ID)
    await message.answer("✨ Действие отменено.", reply_markup=kb.get_main_keyboard(is_admin=is_admin))

@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    db.add_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    is_admin = (message.from_user.id == ADMIN_ID)
    
    await message.answer(
        f"Здравствуйте, <b>{message.from_user.first_name}</b>! 👋\n\n"
        f"Это <b>демо-бот системы автоматизации продаж</b> и приема заявок 24/7.\n\n"
        f"💡 <b>Как это работает:</b>\n"
        f"Вы можете протестировать отправку заявки через кнопку ниже. Данные мгновенно попадут в Google Таблицу и админ-панель!\n\n"
        f"👇 <b>Выберите действие в меню:</b>",
        parse_mode="HTML",
        reply_markup=kb.get_main_keyboard(is_admin=is_admin)
    )

@router.message(F.text.in_(["ℹ️ О компании", "🏢 О компании"]))
async def info_handler(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🏢 <b>Автоматизация продаж & TG-боты под ключ</b>\n\n"
        "Вы теряете до 30% клиентов, если заявки обрабатываются вручную или «на бумажке». "
        "Эта система превращает Telegram в автономный отдел продаж 24/7.\n\n"
        "🔥 <b>Что умеет эта система:</b>\n"
        "• <b>Мгновенный учет:</b> Лиды за 1 секунду улетают в Google Таблицы (бесплатная CRM).\n"
        "• <b>Управление в 1 клик:</b> Меняйте статус заявки прямо в Telegram — клиенту уйдет уведомление, а в таблице обновятся данные.\n"
        "• <b>Защита от спама и ошибок:</b> Умная проверка номеров телефонов и данных. Никакого мусора в базе.\n"
        "• <b>Выгрузка базы:</b> Формирование Excel-файлов с контактами клиентов в любой момент.\n\n"
        "🎯 <b>Адаптация под любую нишу:</b>\n"
        "Услуги, e-commerce, автосервисы, салоны, недвижимость, онлайн-школы, общепит.\n\n"
        "💡 <b>Хотите внедрить такую систему и не терять ни одной заявки?</b>\n"
        "Напишите мне для бесплатного разбора вашей ниши: @il_overdrive",
        parse_mode="HTML"
    )

@router.message(F.text.in_(["📞 Контакты", "💎 Контакты"]))
async def contacts_handler(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "💎 <b>Наши контакты:</b>\n\n"
        "📲 <b>Телефон:</b> +7 (999) 999-99-99\n"
        "💬 <b>Telegram:</b> @il_overdrive\n"
        "⏰ <b>Режим работы:</b> Круглосуточно",
        parse_mode="HTML"
    )

# --- ПОШАГОВЫЙ ОПРОС КЛИЕНТА (FSM) С ВАЛИДАЦИЕЙ ---

@router.message(F.text.in_(["📝 Оставить заявку", "🚀 Оставить заявку"]))
async def start_form(message: types.Message, state: FSMContext):
    await state.set_state(Form.name)
    await message.answer("👋 <b>Как к вам обращаться?</b> (Введите ваше имя)", parse_mode="HTML", reply_markup=kb.get_cancel_keyboard())

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
    # ПЕРЕХВАТ НАЖАТИЙ КНОПОК МЕНЮ ВО ВРЕМЯ ВВОДА ТЕЛЕФОНА
    menu_buttons = [
        "ℹ️ О компании", "🏢 О компании",
        "📞 Контакты", "💎 Контакты",
        "📝 Оставить заявку", "🚀 Оставить заявку",
        "📢 Сделать рассылку", "⚙️ Админ-панель"
    ]
    
    if message.text in menu_buttons:
        await state.clear()
        if message.text in ["ℹ️️ О компании", "🏢 О компании"]:
            await info_handler(message, state)
        elif message.text in ["📞 Контакты", "💎 Контакты"]:
            await contacts_handler(message, state)
        return

    if message.contact:
        phone = message.contact.phone_number
    else:
        raw_phone = message.text
        # ВАЛИДАЦИЯ ТЕЛЕФОНА: оставляем только цифры
        digits = re.sub(r"\D", "", raw_phone)
        if not (10 <= len(digits) <= 12):
            await message.answer(
                "⚠️ <b>Некорректный номер телефона!</b>\n"
                "Пожалуйста, введите номер в формате: <code>+79991234567</code> или нажмите кнопку ниже.",
                parse_mode="HTML",
                reply_markup=kb.get_phone_keyboard()
            )
            return
        phone = raw_phone

    await state.update_data(phone=phone)
    await state.set_state(Form.comment)
    await message.answer("💬 <b>Опишите коротко вашу задачу или вопрос:</b>", parse_mode="HTML", reply_markup=kb.get_cancel_keyboard())

@router.message(Form.comment)
async def process_comment(message: types.Message, state: FSMContext, bot: Bot):
    user_data = await state.get_data()
    name = user_data.get('name', 'Не указано')
    phone = user_data.get('phone', 'Не указано')
    comment = message.text
    client_id = message.from_user.id
    
    db.add_request(client_id, name, phone, comment)

    # Выгрузка в Google Таблицу (с явным указанием action)
    await send_to_google_sheet({
        "action": "add_request",
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

# --- ИЗМЕНЕНИЕ СТАТУСА (И В GOOGLE ТАБЛИЦЕ) ---

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
        google_status = "🟡 В работе"
        user_notify_text = "🟡 <b>Обновление по вашей заявке:</b>\nВаша заявка взята в работу! Менеджер уже занимается вашим вопросом."
    else:
        status_text = "отклонена ❌"
        google_status = "🔴 Отклонена"
        user_notify_text = "🔴 <b>Обновление по вашей заявке:</b>\nК сожалению, ваша заявка отклонена. Если у вас возникли вопросы, вы можете связаться с нами через контакты."

    # Изменяем текст у админа
    await callback.message.edit_text(
        f"{callback.message.text}\n\n📌 <b>Статус:</b> Заявка {status_text}",
        parse_mode="HTML"
    )
    await callback.answer(f"Заявка {status_text}")

    # Обновляем статус в Google Таблице
    if target_user_id:
        await send_to_google_sheet({
            "action": "update_status",
            "user_id": target_user_id,
            "new_status": google_status
        })
        try:
            await bot.send_message(chat_id=target_user_id, text=user_notify_text, parse_mode="HTML")
        except Exception as e:
            print(f"Не удалось отправить уведомление пользователю {target_user_id}: {e}")

# --- РАССЫЛКА ---

@router.message(Command("broadcast"))
@router.message(F.text == "📢 Сделать рассылку")
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

    await callback.message.edit_text("⏳ <b>Начинаю рассылку...</b>", parse_mode="HTML")
    await callback.answer()

    asyncio.create_task(run_broadcast_task(bot, text_to_send, callback.from_user.id))

# --- АДМИН-ПАНЕЛЬ И ЭКСПОРТ БАЗЫ ---

@router.message(Command("admin"))
@router.message(F.text == "⚙️ Админ-панель")
async def admin_panel(message: types.Message, state: FSMContext):
    await state.clear()
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ У вас нет доступа к этой команде.")
        return

    requests = db.get_all_requests(limit=10)
    
    export_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📥 Скачать базу клиентов (.xlsx)", callback_data="export_users")]
    ])

    if not requests:
        await message.answer("📭 Заявок пока нет.", reply_markup=export_kb)
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

    await message.answer(text, parse_mode="HTML", reply_markup=export_kb)

@router.callback_query(F.data == "export_users")
async def export_users_excel(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("У вас нет доступа.", show_alert=True)
        return

    users = db.get_all_users_full()
    if not users:
        await callback.answer("База клиентов пуста.", show_alert=True)
        return

    # Создаем DataFrame и сохраняем в Excel
    df = pd.DataFrame(users, columns=["User ID", "Username", "Имя"])
    file_path = "users_export.xlsx"
    df.to_excel(file_path, index=False)

    # Отправляем файл админу
    await callback.message.answer_document(
        document=FSInputFile(file_path),
        caption="📊 <b>Экспорт базы пользователей бота</b>",
        parse_mode="HTML"
    )
    await callback.answer()

    # Удаляем временный файл
    if os.path.exists(file_path):
        os.remove(file_path)