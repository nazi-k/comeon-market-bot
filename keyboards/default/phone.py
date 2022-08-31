from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def make_phone_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(
        KeyboardButton(text="Поділитись контактом", request_contact=True),
        KeyboardButton(text="Відмінити")
    )
    return keyboard
