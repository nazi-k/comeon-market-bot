from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from cbdata.cart import *
from cbdata.catalog import cb_catalog

from db.models import Cart, CartProductModification

from .utils import make_counter_buttons


def make_cart_keyboard(cart: Cart) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(row_width=2)
    buttons = [
        InlineKeyboardButton(
            text="✏️Редагувати",
            callback_data=cb_edit_cart.new(cart_id=cart.id, selected_index_product_in_cart=0)
        ),
        InlineKeyboardButton(
            text="❌ Очистити",
            callback_data=cb_clear_cart.new(id=cart.id)
        ),
        InlineKeyboardButton(
            text="✅ Оформити замовлення",
            callback_data=cb_create_order.new(cart_id=cart.id)
        )
    ]
    keyboard.add(InlineKeyboardButton(
            text="💰Продовжити покупки",
            callback_data=cb_catalog.new(cart_id=cart.id)
        )
    )
    keyboard.add(*buttons)

    return keyboard


def make_edit_cart_menu_keyboard(cart_products: list[CartProductModification],
                                 selected_index_product_in_cart: int) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(row_width=3)
    keyboard.add(*make_edit_cart_counter_buttons(cart_products[selected_index_product_in_cart]))
    if len(cart_products) > 1:
        buttons = [
            InlineKeyboardButton(
                text="⬅️",
                callback_data=cb_edit_cart.new(
                    cart_id=cart_products[selected_index_product_in_cart].cart_id,
                    selected_index_product_in_cart=selected_index_product_in_cart - 1)
            ),
            InlineKeyboardButton(
                text=f"{selected_index_product_in_cart + 1}/{len(cart_products)}",
                callback_data="this/all"
            ),
            InlineKeyboardButton(
                text="➡️",
                callback_data=cb_edit_cart.new(
                    cart_id=cart_products[selected_index_product_in_cart].cart_id,
                    selected_index_product_in_cart=selected_index_product_in_cart + 1)
            )
        ]
        keyboard.add(*buttons)
    keyboard.add(
        InlineKeyboardButton(
            text="✅ Завершити редагування",
            callback_data=cb_end_edit_cart.new(cart_id=cart_products[selected_index_product_in_cart].cart_id)
        )
    )

    return keyboard


def make_confirm_order_keyboard(cart_id: int) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton(
            text="Так",
            callback_data=cb_confirm_order.new(cart_id=cart_id)
        ),
        InlineKeyboardButton(
            text="Ні, відмінити",
            callback_data=cb_cancel_order.new()
        )
    )
    return keyboard


def make_edit_cart_counter_buttons(cart_product: CartProductModification) -> list[InlineKeyboardButton]:
    return make_counter_buttons(cb_edit_cart_change_product_quantity, cart_product)
