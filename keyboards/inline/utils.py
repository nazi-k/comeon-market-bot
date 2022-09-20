from aiogram.types import InlineKeyboardButton
from aiogram.utils.callback_data import CallbackData
from db.models import CartProductModification


def make_counter_buttons(callback_data_obj: CallbackData, cart_product_modification: CartProductModification)\
        -> list[InlineKeyboardButton]:
    return [
        InlineKeyboardButton(
            text="➖",
            callback_data=callback_data_obj.new(
                product_modification_id=cart_product_modification.product_modification_id,
                cart_id=cart_product_modification.cart_id, add_or_sub="sub"
            )
        ),
        InlineKeyboardButton(
            text=f"{cart_product_modification.quantity} шт.",  # TODO добавити callback_data і відповідь на неї
            callback_data="quantity_in_cart"
        ),
        InlineKeyboardButton(
            text="➕",
            callback_data=callback_data_obj.new(
                product_modification_id=cart_product_modification.product_modification_id,
                cart_id=cart_product_modification.cart_id, add_or_sub="add"
            )
        )
    ]
