from aiogram.dispatcher.filters import Text
from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.utils.markdown import hide_link

from sqlalchemy.ext.asyncio import AsyncSession

from keyboards.inline import make_catalog_keyboard, make_product_keyboard, make_buy_product_keyboard
from db.models import ProductFolder, Product, Cart, CartProduct

from cbdata.catalog import *

from loader import dp


@dp.message_handler(Text(equals="📘 Каталог"), state="*")
async def catalog(message: types.Message, session: AsyncSession, state: FSMContext):
    await state.finish()
    root_product_folder: ProductFolder = await ProductFolder.get_root_product_folder(session)
    await message.answer(root_product_folder.name,  # "Смотри, что у нас есть :)"
                         reply_markup=await make_catalog_keyboard(
                             root_product_folder, session)
                         )


@dp.callback_query_handler(cb_product_folder.filter(), state="*")
async def catalog_product_folder(call: types.CallbackQuery, callback_data: dict, session: AsyncSession):
    product_folder: ProductFolder = await ProductFolder.get_filter_by(session, id=int(callback_data['id']))
    await call.message.edit_text(product_folder.name, reply_markup=await make_catalog_keyboard(product_folder, session))


@dp.callback_query_handler(cb_product.filter(), state="*")
async def catalog_product(call: types.CallbackQuery, callback_data: dict, session: AsyncSession):
    product: Product = await Product.get_filter_by(session, id=int(callback_data['id']))
    cart: Cart = await Cart.get_or_create(session, customer_id=int(call.message.chat.id), finish=False)
    await call.message.edit_text(text=product.name + hide_link(await product.get_url_photo(session)),
                                 reply_markup=await make_product_keyboard(product, cart, session)
                                 )


@dp.callback_query_handler(cb_buy_product.filter(), state="*")
async def catalog_buy_product(call: types.CallbackQuery, callback_data: dict, session: AsyncSession):
    product: Product = await Product.get_filter_by(session, id=int(callback_data['product_id']))
    cart: Cart = await Cart.get_or_create(session, customer_id=int(call.message.chat.id), finish=False)
    cart_product: CartProduct = await cart.add_product(session, product)
    await call.message.edit_text(text=product.name + hide_link(await product.get_url_photo(session)),
                                 reply_markup=await make_buy_product_keyboard(cart, product, cart_product, session)
                                 )


@dp.callback_query_handler(cb_buy_change_product_quantity.filter(), state="*")
async def catalog_change_product_quantity(call: types.CallbackQuery, callback_data: dict, session: AsyncSession):
    cart: Cart = await Cart.get_filter_by(session, id=int(callback_data['cart_id']))
    if cart.finish:
        await call.answer("Этот заказ уже оформлен, начните оформлять новый")
    else:
        product: Product = await Product.get_filter_by(session, id=int(callback_data['product_id']))
        cart_product: CartProduct = await CartProduct.get_filter_by(session, cart_id=cart.id, product_id=product.id)
        if callback_data['add_or_sub'] == 'add':
            await cart_product.change_quantity(session, change_on=+1)
        elif callback_data['add_or_sub'] == 'sub':
            await cart_product.change_quantity(session, change_on=-1)
        else:
            raise ValueError("Очікую 'add' або 'sub'")
        await call.message.edit_reply_markup(
            reply_markup=await make_buy_product_keyboard(cart, product, cart_product, session)
        )
