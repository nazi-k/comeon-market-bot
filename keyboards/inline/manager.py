from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def make_manager_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton(text="Менеджер", url="https://t.me/garikoff_vape_lutsk")
    )
    return keyboard
