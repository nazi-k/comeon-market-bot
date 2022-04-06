from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def make_phone_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(
        KeyboardButton(text="Запросить контакт", request_contact=True),
        KeyboardButton(text="Отмена")
    )
    return keyboard
