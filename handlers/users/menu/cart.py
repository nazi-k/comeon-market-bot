import re
from datetime import date
from typing import Optional

from aiogram.dispatcher.filters import Text
from aiogram import types
from aiogram.dispatcher import FSMContext

from sqlalchemy.ext.asyncio import AsyncSession

from keyboards.default import make_phone_keyboard, make_menu_keyboard
from keyboards.inline.cart import make_cart_keyboard, make_edit_cart_menu_keyboard, make_edit_cart_counter_buttons

from db.models import Cart, Product, DataToSend

from cbdata.cart import *
from keyboards.inline.cart import make_confirm_order_keyboard
from keyboards.inline.order import make_finished_order_keyboard
from states.create_order import CreateOrder

from .utils import change_product_quantity

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
    if cart:
        await session.delete(cart)
        await session.commit()
    await call.message.edit_text("Корзина пуста")


@dp.callback_query_handler(cb_edit_cart_change_product_quantity.filter(), state="*")
async def edit_cart_change_product_quantity(call: types.CallbackQuery, callback_data: dict, session: AsyncSession):
    result = await change_product_quantity(call, callback_data, session)
    if result:
        _, product, cart_product = result
        call.message.reply_markup.inline_keyboard[0] = make_edit_cart_counter_buttons(cart_product)
        await call.message.edit_caption(
            caption=_make_caption_to_product_in_cart(product, cart_product.quantity),
            reply_markup=call.message.reply_markup
        )


@dp.callback_query_handler(cb_end_edit_cart.filter(), state="*")
async def end_edit_cart(call: types.CallbackQuery):
    await call.message.delete()


@dp.callback_query_handler(cb_edit_cart.filter(), state="*")
async def send_edit_cart_menu(call: types.CallbackQuery, callback_data: dict, session: AsyncSession):
    index_product_in_cart = int(callback_data["enter_index_product_in_cart"])
    cart: Cart = await Cart.get_filter_by(session, id=int(callback_data["cart_id"]))
    cart_products = await cart.get_sorted_cart_products(session)
    if index_product_in_cart >= len(cart_products):
        index_product_in_cart = 0
    elif index_product_in_cart < 0:
        index_product_in_cart = len(cart_products) - 1
    if cart_products:
        product: Product = await cart_products[index_product_in_cart].get_product(session)
        if call.message.photo:
            await call.message.edit_media(
                types.InputMediaPhoto(
                    media=await product.get_photo_file_id(session),
                    caption=_make_caption_to_product_in_cart(product, cart_products[index_product_in_cart].quantity)),
                reply_markup=make_edit_cart_menu_keyboard(cart_products, index_product_in_cart)
            )
        else:
            await call.message.answer_photo(
                photo=await product.get_photo_file_id(session),
                caption=_make_caption_to_product_in_cart(product, cart_products[index_product_in_cart].quantity),
                reply_markup=make_edit_cart_menu_keyboard(cart_products, index_product_in_cart)
            )
    else:
        await session.delete(cart)
        await session.commit()
        await call.message.edit_text("Корзина пуста")


@dp.callback_query_handler(cb_create_order.filter(), state="*")
async def create_order(call: types.CallbackQuery, callback_data: dict, state: FSMContext):
    await CreateOrder.waiting_for_city.set()
    await call.message.answer("Укажите город доставки")
    await state.update_data(cart_id=int(callback_data["cart_id"]))


@dp.message_handler(state=CreateOrder.waiting_for_city)
async def city_chosen(message: types.Message, state: FSMContext):
    await CreateOrder.waiting_for_mail_number.set()
    await message.answer("№ отделения Новой Почты")
    await state.update_data(city=message.text)


@dp.message_handler(state=CreateOrder.waiting_for_mail_number)
async def mail_number_chosen(message: types.Message, state: FSMContext):
    await CreateOrder.waiting_for_full_name.set()
    await message.answer("Фамилия Имя получателя")
    await state.update_data(mail_number=message.text)


@dp.message_handler(state=CreateOrder.waiting_for_full_name)
async def full_name_chosen(message: types.Message, state: FSMContext):
    await CreateOrder.waiting_for_phone_number.set()
    await message.answer("Почти готово! Поделитесь с нами вашим номером телефона, чтобы мы могли связаться с вами. "
                         "Или напишите его ниже в формате +380999999999", reply_markup=make_phone_keyboard())
    await state.update_data(full_name=message.text)


@dp.message_handler(content_types=types.ContentTypes.TEXT, state=CreateOrder.waiting_for_phone_number)
@dp.message_handler(content_types=types.ContentTypes.CONTACT, state=CreateOrder.waiting_for_phone_number)
async def full_name_chosen(message: types.Message, session: AsyncSession, state: FSMContext):
    if message.contact:
        await state.update_data(phone_number=message.contact.phone_number)
    else:
        phone_number = _get_phone_number(message.text)
        if phone_number:
            await state.update_data(phone_number=phone_number)
        else:
            await message.answer("Мы не смогли распознать ваш номер :(\n"
                                 "Пожалуйста, отправьте его в формате +380999999999")
            return

    await CreateOrder.waiting_to_confirm.set()
    data_to_send_dict = await state.get_data()
    cart: Cart = await Cart.get_filter_by(session, id=data_to_send_dict["cart_id"])
    data_to_send = DataToSend.__call__(**data_to_send_dict)
    await message.answer(
        f"Всё верно?\n\n{await cart.get_cart_text(session)}\n{data_to_send.get_text()}",
        reply_markup=make_confirm_order_keyboard(cart.id)
    )


@dp.callback_query_handler(cb_confirm_order.filter(), state=CreateOrder.waiting_to_confirm)
async def confirm_order(call: types.CallbackQuery, callback_data: dict, session: AsyncSession, state: FSMContext):
    data_to_send_dict = await state.get_data()
    cart: Cart = await Cart.get_filter_by(session, id=data_to_send_dict["cart_id"])
    if data_to_send_dict["cart_id"] != int(callback_data["cart_id"]) or not cart or cart.finish:
        await call.answer("Эта кнопка уже не работает. Попробуйте что-то другое.")
    else:
        cart.data = date.today()
        cart.finish = True
        session.add(DataToSend.__call__(**data_to_send_dict))
        await session.commit()
        await call.message.edit_reply_markup(reply_markup=make_finished_order_keyboard([cart]))
        await call.message.answer(
            f"Спасибо, номер заказа {cart.data}-{cart.id}! Наш менеджер свяжется с вами для уточнения всех деталей.",
            reply_markup=make_menu_keyboard()
        )
        await state.finish()


@dp.callback_query_handler(cb_cancel_order.filter(), state="*")
async def cancel_order(call: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await call.message.answer(
        "Мы перебросили вас в главное меню, но ваша корзина на месте", reply_markup=make_menu_keyboard()
    )


def _make_caption_to_product_in_cart(product: Product, quantity: int) -> str:
    return f"{product.name}\n\n{quantity} шт. x {product.price}₴ = {quantity * product.price}₴"


def _get_phone_number(text: str) -> Optional[str]:
    result = re.search(r'\+380\d{9}', text)
    if result:
        return result.group(0)
