from aiogram.dispatcher.filters import Text
from aiogram import types
from aiogram.dispatcher import FSMContext

from sqlalchemy.ext.asyncio import AsyncSession

from cbdata.order import cb_edit_shipping_address
from exception import NotEnoughQuantity, InvoicePayloadToLong
from keyboards.inline.cart import make_cart_keyboard, make_edit_cart_menu_keyboard, make_edit_cart_counter_buttons

from db.models import Cart, Product

from cbdata.cart import *
from keyboards.inline.payment import make_payment_keyboard
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
async def city_chosen(message: types.Message, state: FSMContext):
    await CreateOrder.waiting_for_city.set()
    await message.answer("Вкажіть місто доставки")
    await state.update_data(region=message.text)


@dp.message_handler(state=CreateOrder.waiting_for_city)
async def nova_poshta_number_chosen(message: types.Message, state: FSMContext):
    await CreateOrder.waiting_for_nova_poshta_number.set()
    await message.answer("№ відділення Нової Пошти")
    await state.update_data(city=message.text)


@dp.message_handler(state=CreateOrder.waiting_for_nova_poshta_number)
async def send_invoice(message: types.Message, session: AsyncSession, state: FSMContext):
    cart: Cart = await Cart.get_filter_by(session, customer_id=message.chat.id, finish=False)
    await state.update_data(nova_poshta_number=message.text)
    try:
        await message.bot.send_invoice(
            chat_id=message.chat.id,
            reply_markup=make_payment_keyboard(cart_id=cart.id, cart_amount=await cart.get_amount(session)),
            **(await cart.get_data_to_invoice(session=session, **(await state.get_data())))
        )
        await state.finish()
    except InvoicePayloadToLong:
        cart_id = (await state.get_data())["cart_id"]
        await state.finish()
        new_state = dp.get_current().current_state(chat=message.chat.id, user=message.from_user.id)
        await message.answer("Адреса доставки надто довга, щоб бути схожою на правду😵‍💫\nПочнемо спочатку.")
        await new_state.update_data(cart_id=cart_id)
        await new_state.set_state(CreateOrder.waiting_for_region)
        await message.answer("Вкажіть область доставки")


@dp.callback_query_handler(cb_edit_shipping_address.filter(), state="*")
async def edit_shipping_address(call: types.CallbackQuery, callback_data: dict, state: FSMContext):
    await region_chosen(call, callback_data, state)


def _make_caption_to_product_in_cart(product: Product, quantity: int) -> str:
    return f"{product.name}\n\n{quantity} шт. x {product.price}₴ = {quantity * product.price}₴"
