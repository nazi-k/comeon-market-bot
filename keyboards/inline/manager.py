from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from data.config import MANAGER_USERNAME


def make_manager_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(row_width=1)
    buttons = [
        InlineKeyboardButton(text="Менеджер", url=f"https://t.me/{MANAGER_USERNAME}")
    ]
    keyboard.add(*buttons)
    return keyboard
