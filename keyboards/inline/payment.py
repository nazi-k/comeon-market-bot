from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from cbdata.order import cb_edit_shipping_address


def make_payment_keyboard(cart_id: int, cart_amount: int) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(row_width=1)
    buttons = [
        InlineKeyboardButton(
            text=f"Оплатити {cart_amount},00UAH",
            pay=True
        ),
        InlineKeyboardButton(
            text="📦Змінити адресу доставки",
            callback_data=cb_edit_shipping_address.new(cart_id=cart_id)
        ),
    ]
    keyboard.add(*buttons)

    return keyboard
