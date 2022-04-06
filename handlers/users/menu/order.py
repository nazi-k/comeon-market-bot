from aiogram.dispatcher.filters import Text
from aiogram import types
from aiogram.dispatcher import FSMContext

from sqlalchemy.ext.asyncio import AsyncSession

from keyboards.inline.cart import make_cart_keyboard
from keyboards.inline.order import make_finished_order_keyboard, make_copy_cart_keyboard
from db.models import Cart, Customer, DataToSend

from cbdata.order import *

from loader import dp


@dp.message_handler(Text(equals="📜 Заказы"), state="*")
async def order_answer(message: types.Message, session: AsyncSession, state: FSMContext):
    await state.finish()
    carts = await Customer.__call__(telegram_id=message.chat.id).get_finished_carts(session)
    if carts:
        await message.answer("Ваши заказы:", reply_markup=make_finished_order_keyboard(carts))
    else:
        await message.answer("Сделай заказ, чтобы увидеть его здесь!")


@dp.callback_query_handler(cb_finished_order.filter(), state="*")
async def show_order(call: types.CallbackQuery, callback_data: dict, session: AsyncSession):
    cart: Cart = await Cart.get_filter_by(session, id=int(callback_data["cart_id"]))
    data_to_send: DataToSend = await cart.get_data_to_send(session)
    await call.message.answer(
        f"{await cart.get_cart_text(session)}\n{data_to_send.get_text()}",
        reply_markup=make_copy_cart_keyboard(cart)
    )


@dp.callback_query_handler(cb_copy_cart.filter(), state="*")
async def copy_cart(call: types.CallbackQuery, callback_data: dict, session: AsyncSession):
    cart: Cart = await Cart.get_or_create(session, customer_id=call.message.chat.id, finish=False)
    cart_who_copy = await Cart.get_filter_by(session, id=int(callback_data["cart_id"]))
    await cart.set_copy(session, cart_who_copy)
    await call.message.answer(await cart.get_cart_text(session), reply_markup=make_cart_keyboard(cart))
