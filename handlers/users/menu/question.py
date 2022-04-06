from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text

from loader import dp


@dp.message_handler(Text(equals="❓ FAQ"), state="*")
async def question(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer(
        "Варианты доставки:\n\n"
        "В данный момент доступна только доставка Новой Почтой на отделение, как по Киеву так и в другие города\n\n"
        "Варианты оплаты:\n\n"
        "- Наложенный платеж\n"
        "- Оплата на карту по согласованию с менеджером"
    )
