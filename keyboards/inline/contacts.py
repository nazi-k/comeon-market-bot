from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from cbdata.contacts import cd_social_networks


def make_contacts_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(row_width=2)
    buttons = [
        InlineKeyboardButton(text="Менеджер", url="https://t.me/garikoff_vape_lutsk"),
        InlineKeyboardButton(text="Соц. мережі", callback_data=cd_social_networks.new())
    ]
    keyboard.add(*buttons)
    return keyboard


def make_social_networks_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(row_width=1)
    buttons = [
        InlineKeyboardButton(text="TikTok Київ", url="https://t.me/garikoff_vape_lutsk"),
        InlineKeyboardButton(text="TikTok Луцьк", url="https://www.tiktok.com/@garikoff.lutsk"),
        InlineKeyboardButton(text="TikTok Ківерці", url="https://t.me/garikoff_vape_lutsk"),
        InlineKeyboardButton(text="Instagram", url="https://www.instagram.com/garikoff_vape_lutsk_/"),
        InlineKeyboardButton(text="garikoff.net", url="https://garikoff.net/")
    ]
    keyboard.add(*buttons)
    return keyboard
