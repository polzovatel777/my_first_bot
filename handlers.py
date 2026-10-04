from aiogram import Router, types, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
import keyboards as kb
import database as db

router = Router()

# Состояния формы заявки
class Form(StatesGroup):
    name = State()
    phone = State()
    comment = State()

@router.message(CommandStart())
async def cmd_start(message: types.Message):
    db.add_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    await message.answer(
        f"Здравствуйте, <b>{message.from_user.first_name}</b>! 👋\n\nДобро пожаловать в сервис.",
        parse_mode="HTML",
        reply_markup=kb.get_main_keyboard()
    )

@router.message(F.text == "❌ Отмена")
async def cancel_handler(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Действие отменено.", reply_markup=kb.get_main_keyboard())

# --- Пошаговая форма (FSM) ---

@router.message(F.text == "📝 Оставить заявку")
async def start_form(message: types.Message, state: FSMContext):
    await state.set_state(Form.name)
    await message.answer("Как к вам обращаться? (Введите имя)", reply_markup=kb.get_cancel_keyboard())

@router.message(Form.name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(Form.phone)
    await message.answer("Введите ваш номер телефона:")

@router.message(Form.phone)
async def process_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await state.set_state(Form.comment)
    await message.answer("Напишите краткое описание вашего вопроса или задачи:")

@router.message(Form.comment)
async def process_comment(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    db.add_request(message.from_user.id, user_data['name'], user_data['phone'], message.text)
    
    await state.clear()
    await message.answer(
        "✅ <b>Спасибо! Ваша заявка принята.</b>\nМы свяжемся с вами в ближайшее время.",
        parse_mode="HTML",
        reply_markup=kb.get_main_keyboard()
    )

@router.message(F.text == "ℹ️ О сервисе")
async def info_handler(message: types.Message):
    await message.answer("Мы предоставляем профессиональные решения на Python и aiogram 3.")

@router.message(F.text == "📞 Контакты")
async def contacts_handler(message: types.Message):
    await message.answer("Поддержка: @your_username\nПн-Пт с 9:00 до 18:00")