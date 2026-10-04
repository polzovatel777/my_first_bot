from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

def get_main_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.button(text="📝 Оставить заявку")
    builder.button(text="ℹ️ О сервисе")
    builder.button(text="📞 Контакты")
    builder.adjust(1, 2)
    return builder.as_markup(resize_keyboard=True)

def get_cancel_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.button(text="❌ Отмена")
    return builder.as_markup(resize_keyboard=True)