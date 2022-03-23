from aiogram.types import InlineKeyboardButton
from aiogram.utils.callback_data import CallbackData
from db.models import CartProduct


def get_counter_buttons(callback_data_obj: CallbackData, cart_product: CartProduct) -> list[InlineKeyboardButton]:
    return [
        InlineKeyboardButton(
            text="➖",
            callback_data=callback_data_obj.new(
                product_id=cart_product.product_id, cart_id=cart_product.cart_id, add_or_sub="sub"
            )
        ),
        InlineKeyboardButton(
            text=f"{cart_product.quantity} шт.",  # TODO добавити callback_data і відповідь на неї
            callback_data="quantity_in_cart"
        ),
        InlineKeyboardButton(
            text="➕",
            callback_data=callback_data_obj.new(
                product_id=cart_product.product_id, cart_id=cart_product.cart_id, add_or_sub="add"
            )
        )
    ]
