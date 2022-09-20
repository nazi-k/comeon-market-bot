from aiogram.dispatcher.filters import Text
from aiogram import types, Bot
from aiogram.dispatcher import FSMContext
from aiogram.types import InputMediaPhoto
from aiogram.utils.exceptions import BadRequest

from sqlalchemy.ext.asyncio import AsyncSession

from exception import NotEnoughQuantity
from keyboards.inline.cart import make_cart_keyboard
from keyboards.inline.catalog import make_catalog_keyboard, make_product_keyboard, make_buy_product_keyboard
from db.models import Category, Product, Cart, CartProductModification, ProductModification

from cbdata.catalog import *

from .utils import change_product_quantity

from loader import dp


@dp.message_handler(Text(equals="📘 Каталог"), state="*")
async def catalog(message: types.Message, session: AsyncSession, state: FSMContext):
    await state.finish()
    root_category: Category = await Category.get_root(session)
    await message.answer_photo(
        photo=await root_category.get_photo_file_id(session),
        caption=root_category.name,
        reply_markup=await make_catalog_keyboard(root_category, session)
    )
    await message.delete()


@dp.callback_query_handler(cb_category.filter(), state="*")
async def catalog_category(call: types.CallbackQuery, callback_data: dict, session: AsyncSession):
    category: Category = await Category.get_filter_by(session, id=int(callback_data['id']))
    await call.message.edit_media(
        media=InputMediaPhoto(
            await category.get_photo_file_id(session),
            caption=category.name
        ),
        reply_markup=await make_catalog_keyboard(category, session)
    )
    await call.answer()


@dp.callback_query_handler(cb_product.filter(), state="*")
async def catalog_product(call: types.CallbackQuery, callback_data: dict, session: AsyncSession):
    product: Product = await Product.get_filter_by(session, id=int(callback_data['id']))
    cart: Cart = await Cart.get_or_create(session, customer_id=int(call.message.chat.id), finish=False)
    product_modification = product.product_modifications[
        int(callback_data['selected_index_product_modifications'])]
    await call.message.edit_media(
        media=InputMediaPhoto(
            await product_modification.get_photo_file_id(session),
            caption=product_modification.description
        ),
        reply_markup=await make_product_keyboard(
            product=product,
            cart=cart,
            selected_index_product_modifications=int(callback_data['selected_index_product_modifications']),
            session=session
        )
    )
    await call.answer()


@dp.callback_query_handler(cb_buy_product.filter(), state="*")
async def catalog_buy_product(call: types.CallbackQuery, callback_data: dict, session: AsyncSession):
    product_modification: ProductModification = await ProductModification.get_filter_by(
        session, id=int(callback_data['product_modification_id'])
    )
    cart: Cart = await Cart.get_or_create(session, customer_id=int(call.message.chat.id), finish=False)
    cart_product_modification = await CartProductModification.get_filter_by(
        session=session,
        cart_id=cart.id,
        product_modification_id=product_modification.id
    )
    if not cart_product_modification:
        try:
            cart_product_modification = await cart.add_product_modification(session, product_modification)
            await _update_message_cart(call.bot, cart, session)
        except NotEnoughQuantity as e:
            await call.answer(e.message, show_alert=True)
            return
    await call.message.edit_reply_markup(
        reply_markup=await make_buy_product_keyboard(
            old_keyboard=call.message.reply_markup.inline_keyboard,
            cart_product_modification=cart_product_modification,
            cart=cart,
            session=session
        )
    )
    await call.answer()


@dp.callback_query_handler(cb_buy_change_product_quantity.filter(), state="*")
async def catalog_change_product_quantity(call: types.CallbackQuery, callback_data: dict, session: AsyncSession):
    try:
        result = await change_product_quantity(call, callback_data, session)
    except NotEnoughQuantity as e:
        await call.answer(e.message, show_alert=True)
        return
    if result:
        cart, _, cart_product_modification = result
        await call.message.edit_reply_markup(
            reply_markup=await make_buy_product_keyboard(
                old_keyboard=call.message.reply_markup.inline_keyboard,
                cart_product_modification=cart_product_modification,
                cart=cart,
                session=session
            )
        )
        await _update_message_cart(call.bot, cart, session)
    await call.answer()


async def _update_message_cart(bot: Bot, cart: Cart, session: AsyncSession):
    if cart.message_id:
        try:
            await bot.edit_message_caption(
                chat_id=cart.customer_id,
                message_id=cart.message_id,
                caption=await cart.get_cart_text(session),
                reply_markup=make_cart_keyboard(cart)
            )
        except BadRequest as error:
            if "There is no caption in the message to edit" in error.args:
                await bot.delete_message(chat_id=cart.customer_id, message_id=cart.message_id)
                cart.message_id = None
                await session.commit()
