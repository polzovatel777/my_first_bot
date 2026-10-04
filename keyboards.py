from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

def get_main_keyboard(is_admin: bool = False):
    builder = ReplyKeyboardBuilder()
    builder.button(text="📝 Оставить заявку")
    builder.button(text="ℹ️ О компании")
    builder.button(text="📞 Контакты")
    if is_admin:
        builder.button(text="⚙️ Админ-панель")
    builder.adjust(1, 2, 1 if is_admin else 0)
    return builder.as_markup(resize_keyboard=True)

def get_cancel_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.button(text="❌ Отмена")
    return builder.as_markup(resize_keyboard=True)