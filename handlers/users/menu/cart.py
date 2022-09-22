import re
from typing import Optional

from aiogram.dispatcher.filters import Text
from aiogram import types, Bot
from aiogram.dispatcher import FSMContext
from aiogram.types import InputMediaPhoto
from aiogram.utils.exceptions import MessageToDeleteNotFound

from sqlalchemy.ext.asyncio import AsyncSession

import sheet
from data.config import ADMINS
from exception import NotEnoughQuantity
from keyboards.default import make_menu_keyboard
from keyboards.inline.cart import make_cart_keyboard, make_edit_cart_menu_keyboard, make_edit_cart_counter_buttons, \
    make_confirm_order_keyboard

from db.models import Cart, Order, ProductModification

from cbdata.cart import *
from keyboards.inline.order import make_finished_order_keyboard, make_customer_link
from states.create_order import CreateOrder

from .utils import change_product_quantity

from loader import dp


@dp.message_handler(Text(equals="🛒 Кошик"), state="*")
async def cart_answer(message: types.Message, session: AsyncSession, state: FSMContext):
    await state.finish()
    cart: Cart = await Cart.get_filter_by(session, customer_id=message.chat.id, finish=False)
    await send_message_cart(message, cart, session)


@dp.callback_query_handler(cb_cart.filter(), state="*")
async def cb_cart(call: types.CallbackQuery, session: AsyncSession):
    cart: Cart = await Cart.get_filter_by(session, customer_id=call.message.chat.id, finish=False)
    await send_message_cart(call.message, cart, session, edit=True)
    await call.answer()


@dp.callback_query_handler(cb_clear_cart.filter(), state="*")
async def clear_cart(call: types.CallbackQuery, callback_data: dict, session: AsyncSession):
    cart: Cart = await Cart.get_filter_by(session, id=int(callback_data["id"]))
    await call.message.delete()
    new_message = await call.message.answer("Кошик пустий")
    if cart:
        await cart.clear(session)
        cart.message_id = new_message.message_id
        await session.commit()
    await call.answer()


@dp.callback_query_handler(cb_edit_cart_change_product_quantity.filter(), state="*")
async def edit_cart_change_product_quantity(call: types.CallbackQuery, callback_data: dict, session: AsyncSession):
    try:
        result = await change_product_quantity(call, callback_data, session)
    except NotEnoughQuantity as e:
        await call.answer(e.message, show_alert=True)
        return
    if result:
        _, product, cart_product = result
        call.message.reply_markup.inline_keyboard[0] = make_edit_cart_counter_buttons(cart_product)
        await call.message.edit_caption(
            caption=await _make_caption_to_product_in_cart(product, cart_product.quantity, session),
            reply_markup=call.message.reply_markup
        )
    await call.answer()


@dp.callback_query_handler(cb_end_edit_cart.filter(), state="*")
async def end_edit_cart(call: types.CallbackQuery, callback_data: dict, session: AsyncSession):
    cart_id = int(callback_data["cart_id"])
    cart: Cart = await Cart.get_filter_by(session, id=cart_id)
    await send_message_cart(call.message, cart, session, edit=True)
    await call.answer()


@dp.callback_query_handler(cb_edit_cart.filter(), state="*")
async def send_edit_cart_menu(call: types.CallbackQuery, callback_data: dict, session: AsyncSession, state: FSMContext):
    await state.finish()
    index_product_in_cart = int(callback_data["selected_index_product_in_cart"])
    cart: Cart = await Cart.get_filter_by(session, id=int(callback_data["cart_id"]))
    cart_product_modifications = await cart.get_sorted_cart_products(session)
    if index_product_in_cart >= len(cart_product_modifications):
        index_product_in_cart = 0
    elif index_product_in_cart < 0:
        index_product_in_cart = len(cart_product_modifications) - 1
    if cart_product_modifications:
        product_modification: ProductModification = \
            await cart_product_modifications[index_product_in_cart].get_product_modification(session)
        await call.message.edit_media(
            InputMediaPhoto(
                media=await product_modification.get_photo_file_id(session),
                caption=await _make_caption_to_product_in_cart(
                    product_modification, cart_product_modifications[index_product_in_cart].quantity, session
                )
            ),
            reply_markup=make_edit_cart_menu_keyboard(cart_product_modifications, index_product_in_cart)
        )
    else:
        await call.message.delete()
        new_message = await call.message.answer("Кошик пустий")
        cart.message_id = new_message.message_id
        await session.commit()
    await call.answer()


@dp.callback_query_handler(cb_create_order.filter(), state="*")
async def delivery_info_start(call: types.CallbackQuery, callback_data: dict, state: FSMContext):
    await CreateOrder.waiting_for_region.set()
    await call.message.answer("Вкажіть область доставки")
    await state.update_data(cart_id=int(callback_data["cart_id"]))
    await call.answer()


@dp.message_handler(state=CreateOrder.waiting_for_region)
async def region_chosen(message: types.Message, state: FSMContext):
    await CreateOrder.waiting_for_city.set()
    await message.answer("Вкажіть місто доставки")
    await state.update_data(region=message.text)


@dp.message_handler(state=CreateOrder.waiting_for_city)
async def city_chosen(message: types.Message, state: FSMContext):
    await CreateOrder.waiting_for_nova_poshta_number.set()
    await message.answer("№ відділення Нової Пошти або № поштомата")
    await state.update_data(city=message.text)


@dp.message_handler(state=CreateOrder.waiting_for_nova_poshta_number)
async def nova_poshta_number_chosen(message: types.Message, state: FSMContext):
    await CreateOrder.waiting_for_full_name.set()
    await message.answer("Призвище Ім'я отримувача")
    await state.update_data(nova_poshta_number=message.text)


@dp.message_handler(state=CreateOrder.waiting_for_full_name)
async def full_name_chosen(message: types.Message, state: FSMContext):
    await CreateOrder.waiting_for_phone_number.set()
    await message.answer("Майже готово! Поділіться з нами номером вашого телефону, щоб ми могли зв'язатися з вами. "
                         "Напишіть його нижче у форматі +380999999999")
    await state.update_data(full_name=message.text)


@dp.message_handler(content_types=types.ContentTypes.TEXT, state=CreateOrder.waiting_for_phone_number)
async def phone_number_chosen(message: types.Message, session: AsyncSession, state: FSMContext):
    phone_number = _get_phone_number(message.text)
    if phone_number:
        await state.update_data(phone_number=phone_number)
    else:
        await message.answer("Ми не змогли розпізнати ваш номер :(\n"
                             "Будь ласка, відправте його у форматі +380999999999")
        return

    await CreateOrder.waiting_to_confirm.set()
    order_dict = await state.get_data()
    cart: Cart = await Cart.get_filter_by(session, id=order_dict["cart_id"])
    order_dict["total_amount"] = await cart.get_amount(session)
    await state.update_data(total_amount=order_dict["total_amount"])
    order = Order(**order_dict)
    await message.answer(
        f"Все правильно?\n{await cart.get_cart_text(session)}\n{order.get_data_to_send_text()}",
        reply_markup=make_confirm_order_keyboard(cart.id)
    )


@dp.callback_query_handler(cb_confirm_order.filter(), state=CreateOrder.waiting_to_confirm)
async def confirm_order(call: types.CallbackQuery, callback_data: dict, session: AsyncSession, state: FSMContext):
    order_dict = await state.get_data()
    cart: Cart = await Cart.get_filter_by(session, id=order_dict["cart_id"])
    if order_dict["cart_id"] != int(callback_data["cart_id"]) or not cart or cart.finish:
        await call.answer("Ця кнопка не працює. Спробуйте щось інше.")
    else:
        if await cart.confirmation_buy(session):
            order = Order(**order_dict)
            if order.total_amount == await cart.get_amount(session):
                session.add(order)
                await session.commit()
                await call.message.edit_text(call.message.text.replace("Все правильно?\n", ""),
                                             reply_markup=make_finished_order_keyboard([cart]))
                await call.message.answer(
                    f"Дякую, за замовлення! "
                    f"Наш менеджер зв'яжеться з вами для уточнення всіх деталей.",
                    reply_markup=make_menu_keyboard()
                )
                await state.finish()
                await notify_admin(cart, order, await call.message.chat.get_url(), call.bot, session)
                await sheet.row_record(order, cart.date_time, session)
            else:
                await call.message.edit_text("Вибачте, цілісність вашого кошика пошкодилась :(")
        else:
            await call.message.edit_text("Вибачте, хтось щойно купив залишки вашого замовлення, "
                                         "поки ви були зайняті заповненням даних на доставку.")
    await call.answer()


@dp.callback_query_handler(cb_cancel_order.filter(), state="*")
async def cancel_order(call: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await call.message.delete()
    await call.message.answer("Ми перемістили вас у головне меню, але ваш кошик на місці",
                              reply_markup=make_menu_keyboard())
    await call.answer()


async def _make_caption_to_product_in_cart(product_modification: ProductModification,
                                           quantity: int,
                                           session: AsyncSession) -> str:
    return f"{await product_modification.get_name_with_value(session)}\n\n{quantity} шт. x " \
           f"{product_modification.price}₴ = {quantity * product_modification.price}₴"


def _get_phone_number(text: str) -> Optional[str]:
    result = re.search(r'\+(380\d{9})', text)
    if result:
        return result.group(0)


async def notify_admin(cart: Cart, order: Order, chat_url: str, bot: Bot, session: AsyncSession):
    order_text = f'{await cart.get_cart_text(session)}\n' \
                 f'{order.get_data_to_send_text()}'
    for admin in ADMINS:
        await bot.send_message(
            chat_id=admin,
            text=order_text,
            reply_markup=make_customer_link(chat_url)
        )


async def send_message_cart(message: types.Message, cart: Cart, session: AsyncSession, edit: bool = False):
    if cart:
        if cart.message_id and not (cart.message_id == message.message_id):
            try:
                await message.bot.delete_message(cart.customer_id, cart.message_id)
            except MessageToDeleteNotFound:
                pass
        cart_text = await cart.get_cart_text(session)
        if cart_text:
            if edit:
                new_cart_message = await message.edit_media(
                    media=InputMediaPhoto(
                        cart.get_photo_file_id(),
                        caption=cart_text,
                    ),
                    reply_markup=make_cart_keyboard(cart)
                )
            else:
                await message.delete()
                new_cart_message = await message.answer_photo(
                    photo=cart.get_photo_file_id(),
                    caption=cart_text,
                    reply_markup=make_cart_keyboard(cart)
                )
            cart.message_id = new_cart_message.message_id
            await session.commit()
            return

    await message.delete()

    new_cart_message = await message.answer("Кошик пустий")
    cart = await Cart.get_or_create(session, customer_id=int(message.chat.id), finish=False)
    cart.message_id = new_cart_message.message_id
    await session.commit()
