from aiogram.utils.keyboard import ReplyKeyboardBuilder

def get_main_keyboard(is_admin: bool = False):
    """Главное меню бота"""
    builder = ReplyKeyboardBuilder()
    builder.button(text="📝 Оставить заявку")
    builder.button(text="ℹ️ О компании")
    builder.button(text="📞 Контакты")
    if is_admin:
        builder.button(text="⚙️ Админ-панель")
    builder.adjust(1, 2, 1 if is_admin else 0)
    return builder.as_markup(resize_keyboard=True)

def get_phone_keyboard():
    """Клавиатура с кнопкой отправки номера телефона в 1 клик"""
    builder = ReplyKeyboardBuilder()
    builder.button(text="📱 Отправить номер телефона", request_contact=True)
    builder.button(text="❌ Отмена")
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)

def get_cancel_keyboard():
    """Простая кнопка отмены"""
    builder = ReplyKeyboardBuilder()
    builder.button(text="❌ Отмена")
    return builder.as_markup(resize_keyboard=True)