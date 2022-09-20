#  TODO добавити гортання товарів і категорій якщо більше 10
from typing import Optional

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from sqlalchemy.ext.asyncio import AsyncSession

from cbdata.catalog import *
from cbdata.cart import cb_cart

from db.models import Category, Product, Cart, CartProductModification, ProductModification

from .utils import make_counter_buttons

MAX_BUTTONS_MODIFICATIONS = 3


async def make_catalog_keyboard(category: Category, session: AsyncSession) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(row_width=2)
    buttons = []
    for category_child in await category.get_children(session):
        buttons.append(InlineKeyboardButton(
            text=category_child.name,
            callback_data=cb_category.new(id=category_child.id)
        ))
    for product in await category.get_products(session):
        indexes_and_product_modification = product.indexes_and_product_modifications_with_positive_quantity
        if indexes_and_product_modification:  # Якщо є хоч 1 модифікація з кількість > 0
            first_index_with_positive_quantity = indexes_and_product_modification[0]['index']
            buttons.append(InlineKeyboardButton(
                text=f"{product.name}",
                callback_data=cb_product.new(
                    id=product.id,
                    selected_index_product_modifications=first_index_with_positive_quantity
                )
            ))
    keyboard.add(*buttons)
    if category.parent_id:
        keyboard.add(_make_back_button(category.parent_id))

    return keyboard


async def make_product_keyboard(product: Product, cart: Cart, selected_index_product_modifications: int,
                                session: AsyncSession) -> InlineKeyboardMarkup:
    keyboard = await _meke_keyboard_product_modifications(
        product.indexes_and_product_modifications_with_positive_quantity,
        selected_index_product_modifications,
        session
    )
    keyboard.add(await _make_buy_button(product, cart, selected_index_product_modifications, session))
    keyboard.add(await _make_cart_button(cart, session))
    keyboard.add(_make_back_button(product.category_id))

    return keyboard


async def make_buy_product_keyboard(old_keyboard: list[list[InlineKeyboardButton]],
                                    cart_product_modification: CartProductModification,
                                    cart: Cart,
                                    session: AsyncSession) -> InlineKeyboardMarkup:
    keyboard = old_keyboard[:-3]
    keyboard.append(make_counter_buttons(cb_buy_change_product_quantity, cart_product_modification))
    keyboard.append([await _make_cart_button(cart=cart, session=session)])
    keyboard.append(old_keyboard[-1])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


async def _make_buy_button(product: Product,
                           cart: Cart,
                           selected_index_product_modifications: int,
                           session: AsyncSession) -> InlineKeyboardButton:
    quantity_product_in_cart = await cart.get_quantity_product_in_cart(
        product.product_modifications[selected_index_product_modifications], session
    )
    if quantity_product_in_cart:
        product_button_text = f"{product.product_modifications[selected_index_product_modifications].price}₴ | " \
                              f"В кошику ({quantity_product_in_cart} шт.)"
    else:
        product_button_text = f"{product.product_modifications[selected_index_product_modifications].price}₴ Купити "
    return InlineKeyboardButton(
            text=product_button_text,
            callback_data=cb_buy_product.new(
                product_modification_id=product.product_modifications[selected_index_product_modifications].id
            )
        )


async def _make_cart_button(cart: Cart, session: AsyncSession) -> InlineKeyboardButton:
    return InlineKeyboardButton(
        text=f"🛍️ {await cart.get_amount(session)}₴",
        callback_data=cb_cart.new()
    )


def _make_back_button(category_id: int) -> InlineKeyboardButton:
    return InlineKeyboardButton(
        text="↩Назад",
        callback_data=cb_category.new(id=category_id)
    )


async def _meke_keyboard_product_modifications(
        indexes_end_product_modifications: tuple[dict[str, ProductModification]],
        selected_index_product_modifications: int,
        session: AsyncSession) -> InlineKeyboardMarkup:
    if len(indexes_end_product_modifications) > 1:
        keyboard = await _make_product_modifications_keyboard(
            indexes_end_product_modifications=indexes_end_product_modifications,
            selected_index_product_modifications=selected_index_product_modifications,
            session=session
        )
    else:
        keyboard = InlineKeyboardMarkup()
    return keyboard


async def _make_product_modifications_keyboard(indexes_end_product_modifications: tuple[dict[str, ProductModification]],
                                               selected_index_product_modifications: int,
                                               session: AsyncSession) -> InlineKeyboardMarkup:
    inline_keyboard = InlineKeyboardMarkup(row_width=3)
    if (len(indexes_end_product_modifications) % MAX_BUTTONS_MODIFICATIONS) == 1:
        inline_keyboard.add(
            *await _make_buttons_list(
                indexes_end_product_modifications=indexes_end_product_modifications[:-2],
                selected_index_product_modifications=selected_index_product_modifications,
                session=session
            )
        )
        inline_keyboard.add(
            *await _make_buttons_list(
                indexes_end_product_modifications=indexes_end_product_modifications[-2:],
                selected_index_product_modifications=selected_index_product_modifications,
                session=session,
                start_enumerate=len(indexes_end_product_modifications) - 2
            )
        )
    else:
        inline_keyboard.add(
            *await _make_buttons_list(
                indexes_end_product_modifications=indexes_end_product_modifications,
                selected_index_product_modifications=selected_index_product_modifications,
                session=session
            )
        )
    inline_keyboard.row_width = 1
    return inline_keyboard


async def _make_product_modification_button(product_modifications: ProductModification,
                                            session: AsyncSession,
                                            index: int,
                                            is_selected: bool = False) -> InlineKeyboardButton:
    return InlineKeyboardButton(
        text=f'{"✅" if is_selected else ""}' + ' '.join(await product_modifications.get_modifications_value(session)),
        callback_data=cb_product.new(id=product_modifications.product_id, selected_index_product_modifications=index)
    )


async def _make_buttons_list(indexes_end_product_modifications: tuple[dict[str, ProductModification]],
                             selected_index_product_modifications: int,
                             session: AsyncSession,
                             start_enumerate: int = 0) -> list[InlineKeyboardButton]:
    buttons = []
    for index_and_product_modification in indexes_end_product_modifications[start_enumerate:]:
        buttons.append(
            await _make_product_modification_button(
                product_modifications=index_and_product_modification['product_modification'],
                session=session,
                index=index_and_product_modification['index'],
                is_selected=(index_and_product_modification['index'] == selected_index_product_modifications)
            )
        )
    return buttons
