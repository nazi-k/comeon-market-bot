import re
from typing import Optional

from aiogram.dispatcher.filters import Text
from aiogram import types, Bot
from aiogram.dispatcher import FSMContext

from sqlalchemy.ext.asyncio import AsyncSession

import sheet
from data.config import ADMINS
from exception import NotEnoughQuantity
from keyboards.default import make_phone_keyboard, make_menu_keyboard
from keyboards.inline.cart import make_cart_keyboard, make_edit_cart_menu_keyboard, make_edit_cart_counter_buttons, \
    make_confirm_order_keyboard

from db.models import Cart, Product, Order

from cbdata.cart import *
from keyboards.inline.order import make_finished_order_keyboard
from states.create_order import CreateOrder

from .utils import change_product_quantity

from loader import dp


@dp.message_handler(Text(equals="🛒 Кошик"), state="*")
async def cart_answer(message: types.Message, session: AsyncSession, state: FSMContext):
    await state.finish()
    cart: Cart = await Cart.get_filter_by(session, customer_id=message.chat.id, finish=False)
    if cart:
        cart_text = await cart.get_cart_text(session)
        if cart_text:
            await message.answer(cart_text, reply_markup=make_cart_keyboard(cart))
            return

    await message.answer("Кошик пустий")


@dp.callback_query_handler(cb_cart.filter(), state="*")
async def cb_cart(call: types.CallbackQuery, session: AsyncSession, state: FSMContext):
    await cart_answer(call.message, session, state)


@dp.callback_query_handler(cb_clear_cart.filter(), state="*")
async def clear_cart(call: types.CallbackQuery, callback_data: dict, session: AsyncSession):
    cart: Cart = await Cart.get_filter_by(session, id=int(callback_data["id"]))
    if cart:
        await session.delete(cart)
        await session.commit()
    await call.message.edit_text("Кошик пустий")


@dp.callback_query_handler(cb_edit_cart_change_product_quantity.filter(), state="*")
async def edit_cart_change_product_quantity(call: types.CallbackQuery, callback_data: dict, session: AsyncSession):
    try:
        result = await change_product_quantity(call, callback_data, session)
    except NotEnoughQuantity:
        await call.answer("Легше... В нас більше немає!", show_alert=True)
        return
    if result:
        _, product, cart_product = result
        call.message.reply_markup.inline_keyboard[0] = make_edit_cart_counter_buttons(cart_product)
        await call.message.edit_caption(
            caption=_make_caption_to_product_in_cart(product, cart_product.quantity),
            reply_markup=call.message.reply_markup
        )


@dp.callback_query_handler(cb_end_edit_cart.filter(), state="*")
async def end_edit_cart(call: types.CallbackQuery, callback_data: dict, session: AsyncSession):
    old_cart_message_id = int(callback_data["old_cart_message_id"])
    cart_id = int(callback_data["cart_id"])
    cart: Cart = await Cart.get_filter_by(session, id=cart_id)
    await call.bot.edit_message_text(await cart.get_cart_text(session), call.message.chat.id, old_cart_message_id)
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
            old_cart_message_id = call.message.reply_markup.inline_keyboard[2][0].callback_data.split(':')[1]
            await call.message.edit_media(
                types.InputMediaPhoto(
                    media=await product.get_photo_file_id(session),
                    caption=_make_caption_to_product_in_cart(product, cart_products[index_product_in_cart].quantity)),
                reply_markup=make_edit_cart_menu_keyboard(cart_products, index_product_in_cart, old_cart_message_id)
            )
        else:
            await call.message.answer_photo(
                photo=await product.get_photo_file_id(session),
                caption=_make_caption_to_product_in_cart(product, cart_products[index_product_in_cart].quantity),
                reply_markup=make_edit_cart_menu_keyboard(cart_products, index_product_in_cart, call.message.message_id)
            )
    else:
        await session.delete(cart)
        await session.commit()
        await call.message.edit_text("Кошик пустий")


@dp.callback_query_handler(cb_create_order.filter(), state="*")
async def region_chosen(call: types.CallbackQuery, callback_data: dict, state: FSMContext):
    await CreateOrder.waiting_for_region.set()
    await call.message.answer("Вкажіть область доставки")
    await state.update_data(cart_id=int(callback_data["cart_id"]))


@dp.message_handler(state=CreateOrder.waiting_for_region)
async def region_chosen(message: types.Message, state: FSMContext):
    await CreateOrder.waiting_for_city.set()
    await message.answer("Вкажіть місто доставки")
    await state.update_data(region=message.text)


@dp.message_handler(state=CreateOrder.waiting_for_city)
async def city_chosen(message: types.Message, state: FSMContext):
    await CreateOrder.waiting_for_nova_poshta_number.set()
    await message.answer("№ відділення Нової Пошти")
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
                         "Або напишіть його нижче у форматі +380999999999", reply_markup=make_phone_keyboard())
    await state.update_data(full_name=message.text)


@dp.message_handler(content_types=types.ContentTypes.TEXT, state=CreateOrder.waiting_for_phone_number)
@dp.message_handler(content_types=types.ContentTypes.CONTACT, state=CreateOrder.waiting_for_phone_number)
async def phone_number_chosen(message: types.Message, session: AsyncSession, state: FSMContext):
    if message.contact:
        await state.update_data(phone_number=message.contact.phone_number)
    else:
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
        f"Все правильно?\n\n{await cart.get_cart_text(session)}\n{order.get_data_to_send_text()}",
        reply_markup=make_confirm_order_keyboard(cart.id)
    )


@dp.callback_query_handler(cb_confirm_order.filter(), state=CreateOrder.waiting_to_confirm)
async def confirm_order(call: types.CallbackQuery, callback_data: dict, session: AsyncSession, state: FSMContext):
    order_dict = await state.get_data()
    cart: Cart = await Cart.get_filter_by(session, id=order_dict["cart_id"])
    if order_dict["cart_id"] != int(callback_data["cart_id"]) or not cart or cart.finish:
        await call.answer("Ця кнопка не працює. Спробуйте щось інше.")
    else:
        try:
            await cart.confirmation_buy(session)
            order = Order(**order_dict)
            if order.total_amount == await cart.get_amount(session):
                session.add(order)
                await session.commit()
                await call.message.edit_reply_markup(reply_markup=make_finished_order_keyboard([cart]))
                await call.message.answer(
                    f"Дякую, номер замовленняа! "
                    f"Наш менеджер зв'яжеться з вами для уточнення всіх деталей.",
                    reply_markup=make_menu_keyboard()
                )
                await state.finish()
                await notify_admin(cart, order, await call.message.chat.get_url(), call.bot, session)
                await sheet.row_record(order, cart.date, session)
            else:
                await call.message.edit_text("Вибачте, цілісність вашого кошика пошкодилась :(")
        except NotEnoughQuantity:
            await call.message.edit_text("Вибачте, хтось щойно купив залишки вашого замовлення, "
                                         "поки ви були зайняті заповненням даних на доставку.")


@dp.callback_query_handler(cb_cancel_order.filter(), state="*")
async def cancel_order(call: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await call.message.edit_text(
        "Ми перемістили вас у головне меню, але ваш кошик на місці", reply_markup=make_menu_keyboard()
    )


def _make_caption_to_product_in_cart(product: Product, quantity: int) -> str:
    return f"{product.name}\n\n{quantity} шт. x {product.price}₴ = {quantity * product.price}₴"


def _get_phone_number(text: str) -> Optional[str]:
    result = re.search(r'\+(380\d{9})', text)
    if result:
        return result.group(0)


async def notify_admin(cart: Cart, order: Order, chat_url: str, bot: Bot, session: AsyncSession):
    order_text = f'{await cart.get_cart_text(session)}\n' \
                 f'Замовник: <a href="{chat_url}">{order.full_name}</a>\n' \
                 f'Номер: +{order.phone_number}\n' \
                 f'{order.get_data_to_send_text()}'
    for admin in ADMINS:
        await bot.send_message(
            chat_id=admin,
            text=order_text
        )
