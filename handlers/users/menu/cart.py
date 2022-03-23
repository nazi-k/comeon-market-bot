from aiogram.dispatcher.filters import Text
from aiogram import types
from aiogram.dispatcher import FSMContext

from sqlalchemy.ext.asyncio import AsyncSession

from keyboards.inline import make_cart_keyboard, make_edit_cart_menu_keyboard
from db.models import Cart, Product, CartProduct

from cbdata.cart import *

from loader import dp


@dp.message_handler(Text(equals="🛒 Корзина"), state="*")
async def cart_answer(message: types.Message, session: AsyncSession, state: FSMContext):
    await state.finish()
    cart: Cart = await Cart.get_filter_by(session, customer_id=message.chat.id, finish=False)
    if cart:
        cart_text = await cart.get_cart_text(session)
        if cart_text:
            await message.answer(cart_text, reply_markup=make_cart_keyboard(cart))
            return

    await message.answer("Корзина пуста")


@dp.callback_query_handler(cb_cart.filter(), state="*")
async def cb_cart(call: types.CallbackQuery, session: AsyncSession, state: FSMContext):
    await cart_answer(call.message, session, state)


@dp.callback_query_handler(cb_clear_cart.filter(), state="*")
async def clear_cart(call: types.CallbackQuery, callback_data: dict, session: AsyncSession):
    cart: Cart = await Cart.get_filter_by(session, id=int(callback_data["id"]))
    await session.delete(cart)
    await session.commit()
    await call.message.edit_text("Корзина пуста")


@dp.callback_query_handler(cb_end_edit_cart.filter(), state="*")
async def end_edit_cart(call: types.CallbackQuery):
    await call.message.delete()


@dp.callback_query_handler(cb_edit_cart.filter(), state="*")
async def send_edit_cart_menu(call: types.CallbackQuery, callback_data: dict, session: AsyncSession):
    enter_index_product_in_cart = int(callback_data["enter_index_product_in_cart"])
    cart: Cart = await Cart.get_filter_by(session, id=int(callback_data["cart_id"]))
    cart_products = await cart.get_sorted_cart_products(session)
    if enter_index_product_in_cart > len(cart_products):
        enter_index_product_in_cart = 0
    if enter_index_product_in_cart < 0:
        enter_index_product_in_cart = len(cart_products) - 1
    if cart_products:
        product: Product = await cart_products[enter_index_product_in_cart].get_product(session)
        # TODO зробити по file_id
        await call.message.answer_photo(
            types.InputFile(await product.get_url_photo(session)),
            caption=get_product_caption(product, cart_products[enter_index_product_in_cart].quantity),
            reply_markup=make_edit_cart_menu_keyboard(cart_products, enter_index_product_in_cart)
        )
    else:
        await session.delete(cart)
        await session.commit()
        await call.message.edit_text("Корзина пуста")


def get_product_caption(product: Product, quantity: int) -> str:
    return f"{product.name}\n\n{quantity} шт. x {product.price}₴ = {quantity*product.price}₴"
