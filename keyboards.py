from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_keyboard(is_admin: bool = False) -> ReplyKeyboardMarkup:
    """Главная клавиатура с премиум-оформлением"""
    keyboard = [
        # Главный призыв к действию (большая акцентная кнопка)
        [KeyboardButton(text="🚀 Оставить заявку")],
        # Вспомогательное меню в один ряд для симметрии
        [
            KeyboardButton(text="🏢 О компании"),
            KeyboardButton(text="💎 Контакты")
        ]
    ]

    # Дополнительные кнопки для администратора
    if is_admin:
        keyboard.append([KeyboardButton(text="📢 Сделать рассылку")])
        keyboard.append([KeyboardButton(text="⚙️ Админ-панель")])

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        persistent=True  # Клавиатура не прячется случайно
    )

def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура отмены во время заполнения формы"""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отменить заполнение")]],
        resize_keyboard=True
    )

def get_phone_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для отправки контакта"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Поделиться контактом", request_contact=True)],
            [KeyboardButton(text="❌ Отменить заполнение")]
        ],
        resize_keyboard=True
    )