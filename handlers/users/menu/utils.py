from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Product, Cart, CartProduct

from typing import Optional


async def change_product_quantity(call: CallbackQuery, callback_data: dict, session: AsyncSession) \
        -> Optional[tuple[Cart, Product, CartProduct]]:
    cart: Cart = await Cart.get_filter_by(session, id=int(callback_data['cart_id']))
    if not cart or cart.finish:
        await call.answer("Ця кнопка вже не працює. Спробуйте щось інше.")
    else:
        product: Product = await Product.get_filter_by(session, id=int(callback_data['product_id']))
        if callback_data['add_or_sub'] == 'add':
            cart_product: CartProduct = await cart.add_product(session, product)
        elif callback_data['add_or_sub'] == 'sub':
            cart_product: CartProduct = await cart.sub_product(session, product)
        else:
            raise ValueError("Очікую 'add' або 'sub'")

        if cart_product:
            return cart, product, cart_product
