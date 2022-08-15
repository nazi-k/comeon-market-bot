from aiogram import types, Bot
from aiogram.types import ContentTypes
from sqlalchemy.ext.asyncio import AsyncSession

import sheet
from db.models import Order, Cart
from exception import NotEnoughQuantity

from data.config import ADMINS

from loader import dp, bot


@dp.pre_checkout_query_handler(lambda query: True)
async def checkout(pre_checkout_query: types.PreCheckoutQuery, session: AsyncSession):
    cart_id, region, city, nova_poshta_number = pre_checkout_query.invoice_payload.split(':')
    cart_id = int(cart_id)
    order: Order = await Order.get_filter_by(session, cart_id=cart_id)
    if order:
        await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=False,
                                            error_message="Це замовлення вже оплачено!")
        return
    order: Order = Order(
        cart_id=cart_id,
        region=region,
        city=city,
        nova_poshta_number=nova_poshta_number,
        full_name=pre_checkout_query.order_info.name,
        phone_number=pre_checkout_query.order_info.phone_number,
        total_amount=pre_checkout_query.total_amount,
        raw_payload=pre_checkout_query.invoice_payload,
    )
    try:
        payment_is_ok = await order.payment(session)
        if payment_is_ok:
            session.add(order)
            await session.commit()
        await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=payment_is_ok,
                                            error_message="Вибачте, цілісність вашого кошика пошкодилась :(")
    except NotEnoughQuantity:
        await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=False,
                                            error_message="Вибачте, хтось щойно купив залишки вашого замовлення, "
                                                          "поки ви були зайняті заповненням своїх платіжних даних.")
        await session.rollback()


@dp.message_handler(content_types=ContentTypes.SUCCESSFUL_PAYMENT)
async def got_payment(message: types.Message, session: AsyncSession):
    await message.answer("Дякуємо за покупку!")
    cart_id = int(message.successful_payment.invoice_payload.split(':')[0])
    order: Order = await Order.get_filter_by(session,
                                             cart_id=cart_id,
                                             telegram_payment_charge_id=None,
                                             provider_payment_charge_id=None)
    cart: Cart = await Cart.get_filter_by(session, id=cart_id)

    await set_payment_charge_id(order,
                                message.successful_payment.telegram_payment_charge_id,
                                message.successful_payment.provider_payment_charge_id,
                                session)

    await notify_admin(cart, order, await message.chat.get_url(), message.bot, session)

    await sheet.row_record(order, cart.date, session)


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


async def set_payment_charge_id(order: Order,
                                telegram_payment_charge_id: str,
                                provider_payment_charge_id: str,
                                session: AsyncSession):
    order.telegram_payment_charge_id = telegram_payment_charge_id
    order.provider_payment_charge_id = provider_payment_charge_id
    await session.commit()
