#  TODO добавити гортання товарів і категорій якщо більше 10
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from sqlalchemy.ext.asyncio import AsyncSession

from cbdata.catalog import *
from cbdata.cart import cb_cart

from db.models import ProductFolder, Product, Cart, CartProduct

from .utils import make_counter_buttons


async def make_catalog_keyboard(product_folder: ProductFolder, session: AsyncSession) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(row_width=2)
    buttons = []
    for product_folder_child in await product_folder.get_children(session):
        buttons.append(InlineKeyboardButton(
            text=product_folder_child.name,
            callback_data=cb_product_folder.new(id=product_folder_child.id)
        ))
    for product in await product_folder.get_products(session):
        buttons.append(InlineKeyboardButton(
            text=f"{product.name} {product.price}₴",
            callback_data=cb_product.new(id=product.id)
        ))
    keyboard.add(*buttons)
    if product_folder.parent_id:
        keyboard.add(_make_back_button(product_folder.parent_id))

    return keyboard


async def make_product_keyboard(product: Product, cart: Cart, session: AsyncSession) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(row_width=1)
    product_button_text = f"{product.price}₴ Купити {product.name}"
    quantity_product_in_cart = await cart.get_quantity_product_in_cart(product, session)
    if quantity_product_in_cart:
        product_button_text = f"{quantity_product_in_cart} шт. | " + product_button_text
    keyboard.add(InlineKeyboardButton(
        text=product_button_text,
        callback_data=cb_buy_product.new(product_id=product.id, cart_id=cart.id)
    ))
    keyboard.add(await _make_cart_button(cart, session))
    keyboard.add(_make_back_button(product.product_folder_id))

    return keyboard


async def make_buy_product_keyboard(cart: Cart, product: Product, cart_product: CartProduct, session: AsyncSession) \
        -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(row_width=3)
    keyboard.add(*make_counter_buttons(cb_buy_change_product_quantity, cart_product))
    keyboard.add(await _make_cart_button(cart, session))
    keyboard.add(_make_back_button(product.product_folder_id))

    return keyboard


async def _make_cart_button(cart: Cart, session: AsyncSession) -> InlineKeyboardButton:
    return InlineKeyboardButton(
        text=f"🛍️ {await cart.get_amount(session)}₴",
        callback_data=cb_cart.new()
    )


def _make_back_button(product_folder_id: int) -> InlineKeyboardButton:
    return InlineKeyboardButton(
        text="↩Назад",
        callback_data=cb_product_folder.new(id=product_folder_id)
    )
