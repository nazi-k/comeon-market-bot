from aiogram import types
from aiogram.dispatcher import FSMContext

from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Customer

from keyboards.default import make_menu_keyboard

from loader import dp


@dp.message_handler(state="*", commands="start")
async def bot_start(message: types.Message, session: AsyncSession, state: FSMContext):
    await state.finish()
    await message.answer(f'Привет, {message.from_user.first_name}, рады видеть тебя в нашем боте! '
                         f'Выбирай жидкости для электронных сигарет и электронные сигареты в каталоге, '
                         f'а затем оформляй заказ в корзине :)\n'
                         f'За дополнительной информацией смотри раздел "FAQ"',
                         reply_markup=make_menu_keyboard())
    await Customer.get_or_create(session, telegram_id=int(message.from_user.id))
