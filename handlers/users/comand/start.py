from aiogram import types
from aiogram.dispatcher import FSMContext

from aiogram.utils.deep_linking import decode_payload

from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Customer, Product, Cart, Category

from keyboards.default import make_menu_keyboard
from keyboards.inline.catalog import make_product_keyboard, make_catalog_keyboard

from loader import dp


@dp.message_handler(state="*", commands="start")
async def bot_start(message: types.Message, session: AsyncSession, state: FSMContext):
    await state.finish()
    customer: Customer = await Customer.get_filter_by(session, telegram_id=int(message.from_user.id))
    is_answer = False
    if not customer:
        is_answer = await _answer_start(message)
        session.add(Customer(telegram_id=int(message.from_user.id)))
        await session.commit()
    is_answer = await _answer_deep_link(message, session) or is_answer
    if not is_answer:
        await _answer_start(message)


async def _answer_deep_link(message: types.Message, session: AsyncSession) -> bool:
    args = message.get_args()
    if args:
        try:
            payload = decode_payload(args)
            product: Product = await Product.get_filter_by(session, id=int(payload))
            try:
                if product:
                    enumerate_product_modification = product.indexes_and_product_modifications_with_positive_quantity[0]
                    await message.answer_photo(
                        photo=await enumerate_product_modification['product_modification'].get_photo_file_id(session),
                        caption=enumerate_product_modification['product_modification'].description,
                        reply_markup=await make_product_keyboard(
                            product=product,
                            cart=await Cart.get_or_create(session, customer_id=int(message.from_user.id)),
                            selected_index_product_modifications=enumerate_product_modification['index'],
                            session=session
                        )
                    )
                    return True
            except IndexError:
                category: Category = await Category.get_filter_by(session, id=product.category_id)
                await message.answer_photo(
                    photo=await category.get_photo_file_id(session),
                    caption=category.name,
                    reply_markup=await make_catalog_keyboard(category, session)
                )
                return True
        except ValueError:
            return False
    else:
        return False


async def _answer_start(message: types.Message) -> True:
    await message.answer(f'Привіт, {message.from_user.first_name}, раді бачити тебе у нашому боті! '
                         f'Вибирай рідини для електронних сигарет та електронні сигарети в каталозі, '
                         f'а потім оформляй замовлення у кошику :)',
                         reply_markup=make_menu_keyboard())
    return True
