from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text

from keyboards.default import make_menu_keyboard

from loader import dp


@dp.message_handler(Text(equals="Відмінити"), state="*")
async def cancel(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("ok", reply_markup=make_menu_keyboard())
