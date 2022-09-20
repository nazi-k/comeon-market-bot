from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text

from keyboards.inline.manager import make_manager_keyboard
from loader import dp


@dp.message_handler(Text(equals="🤙 Менеджер"), state="*")
async def contacts(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer(
        "Ви завжди можете зв'язатися з нашим менеджером, просто натисніть кнопку нижче для переходу в чат з менеджером",
        reply_markup=make_manager_keyboard()
    )
