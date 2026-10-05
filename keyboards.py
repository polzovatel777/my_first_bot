from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_keyboard(is_admin: bool = False) -> ReplyKeyboardMarkup:
    """Главное меню (для админа добавляется кнопка рассылки)"""
    keyboard = [
        [KeyboardButton(text="📝 Оставить заявку")],
        [KeyboardButton(text="ℹ️ О компании"), KeyboardButton(text="📞 Контакты")]
    ]
    
    if is_admin:
        keyboard.append([KeyboardButton(text="📢 Сделать рассылку")])
        keyboard.append([KeyboardButton(text="⚙️ Админ-панель")])
        
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        persistent=True
    )

def get_phone_keyboard() -> ReplyKeyboardMarkup:
    """Кнопка отправки номера телефона"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Поделиться контактом", request_contact=True)],
            [KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True
    )

def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Кнопка отмены"""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True
    )