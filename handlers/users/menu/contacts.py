from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text

from keyboards.inline.manager import make_manager_keyboard
from loader import dp


@dp.message_handler(Text(equals="📱 Контакты"), state="*")
async def question(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer(
        "Вы всегда можете связаться с нашим менеджером, просто нажмите кнопку ниже, для перехода в чат с менеджером",
        reply_markup=make_manager_keyboard()
    )

