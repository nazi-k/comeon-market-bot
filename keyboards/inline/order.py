from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from cbdata.order import *

from db.models import Cart


def make_finished_order_keyboard(carts: list[Cart]) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(row_width=2)
    buttons = [
        InlineKeyboardButton(
            text=f"{cart.data}-{cart.id}",
            callback_data=cb_finished_order.new(cart_id=cart.id)
        )
        for cart in carts
    ]
    keyboard.add(*buttons)

    return keyboard


def make_copy_cart_keyboard(cart: Cart) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton(
            text="Копіювати кошик",
            callback_data=cb_copy_cart.new(cart_id=cart.id)
        )
    )
    return keyboard
