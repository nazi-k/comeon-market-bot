from aiogram import types
from aiogram.dispatcher import FSMContext

from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Customer

from keyboards.default import make_menu_keyboard

from loader import dp


@dp.message_handler(state="*", commands="start")
async def bot_start(message: types.Message, session: AsyncSession, state: FSMContext):
    await state.finish()
    await message.answer(f'Привіт, {message.from_user.first_name}, раді бачити тебе у нашому боті! '
                         f'Вибирай рідини для електронних сигарет та електронні сигарети в каталозі, '
                         f'а потім оформляй замовлення у кошику :)\n'
                         f'За додатковою інформацією дивись розділ "FAQ"',
                         reply_markup=make_menu_keyboard())
    await Customer.get_or_create(session, telegram_id=int(message.from_user.id))
