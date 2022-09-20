from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Cart, CartProductModification, ProductModification

from typing import Optional


async def change_product_quantity(call: CallbackQuery, callback_data: dict, session: AsyncSession) \
        -> Optional[tuple[Cart, ProductModification, CartProductModification]]:
    cart: Cart = await Cart.get_filter_by(session, id=int(callback_data['cart_id']))
    if not cart or cart.finish:
        await call.answer("Ця кнопка вже не працює. Спробуйте щось інше.")
    else:
        product_modification: ProductModification = await ProductModification.get_filter_by(
            session, id=int(callback_data['product_modification_id'])
        )
        if callback_data['add_or_sub'] == 'add':
            cart_product_modification: CartProductModification = await cart.add_product_modification(
                session, product_modification
            )
        elif callback_data['add_or_sub'] == 'sub':
            cart_product_modification: CartProductModification = await cart.sub_product_modification(
                session, product_modification
            )
        else:
            raise ValueError("Очікую 'add' або 'sub'")

        if cart_product_modification:
            return cart, product_modification, cart_product_modification

