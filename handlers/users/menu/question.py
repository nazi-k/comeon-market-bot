from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text

from loader import dp


@dp.message_handler(Text(equals="❓ FAQ"), state="*")
async def question(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer(
        "Варіанти доставки:\n\n"
        "На даний момент доступна тільки доставка Новою Поштою на відділення, як по Києву, так і в інші міста.\n\n"
        "Варіанти оплати:\n\n"
        "- Оплата на картку за погодженням з менеджером"
    )
