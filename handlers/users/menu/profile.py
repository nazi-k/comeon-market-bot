from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text

from loader import dp


@dp.message_handler(Text(equals="💨 Профіль"), state="*")
async def question(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("В розробці ⚙️")
