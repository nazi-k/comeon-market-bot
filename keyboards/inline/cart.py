from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from sqlalchemy.ext.asyncio import AsyncSession

from cbdata.cart import *

from db.models import ProductFolder, Product, Cart, CartProduct

from .utils import get_counter_buttons


def make_cart_keyboard(cart: Cart) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(row_width=2)
    buttons = [
        InlineKeyboardButton(
            text="✏️Редактировать",
            callback_data=cb_edit_cart.new(cart_id=cart.id, enter_index_product_in_cart=0)
        ),
        InlineKeyboardButton(
            text="❌ Очистить",
            callback_data=cb_clear_cart.new(id=cart.id)
        ),
        InlineKeyboardButton(
            text="✅ Оформить заказ",
            callback_data=cb_finish_cart.new(id=cart.id)
        )
    ]
    keyboard.add(*buttons)

    return keyboard


def make_edit_cart_menu_keyboard(cart_products: list[CartProduct], enter_index_product_in_cart: int) \
        -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(row_width=3)
    keyboard.add(*get_counter_buttons(cb_edit_cart_change_product_quantity, cart_products[enter_index_product_in_cart]))
    if len(cart_products) > 1:
        buttons = [
            InlineKeyboardButton(
                text="⬅️",
                callback_data=cb_edit_cart.new(
                    cart_id=cart_products[enter_index_product_in_cart].cart_id,
                    enter_index_product_in_cart=enter_index_product_in_cart - 1)
            ),
            InlineKeyboardButton(
                text=f"{enter_index_product_in_cart + 1}/{len(cart_products)}",
                callback_data="TODO"
            ),
            InlineKeyboardButton(
                text="➡️",
                callback_data=cb_edit_cart.new(
                    cart_id=cart_products[enter_index_product_in_cart].cart_id,
                    enter_index_product_in_cart=enter_index_product_in_cart + 1)
            )
        ]
        keyboard.add(*buttons)
    keyboard.add(InlineKeyboardButton(
        text="✅ Завершить редактирование",
        callback_data=cb_end_edit_cart.new()
    )
    )

    return keyboard
