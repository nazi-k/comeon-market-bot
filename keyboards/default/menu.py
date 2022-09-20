from aiogram.types import ReplyKeyboardMarkup


def make_menu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = ["📘 Каталог", "🛒 Кошик", "📜 Мої замовлення", "🤙 Менеджер"]
    keyboard.add(*buttons)
    return keyboard
