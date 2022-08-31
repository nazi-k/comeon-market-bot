from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text

from keyboards.inline.contacts import make_contacts_keyboard, make_social_networks_keyboard
from loader import dp

from cbdata.contacts import cd_social_networks


@dp.message_handler(Text(equals="🤙 Менеджер"), state="*")
async def contacts(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer(
        "Ви завжди можете зв'язатися з нашим менеджером, просто натисніть кнопку нижче для переходу в чат з менеджером",
        reply_markup=make_contacts_keyboard()
    )


@dp.callback_query_handler(cd_social_networks.filter(), state="*")
async def social_networks(call: types.CallbackQuery):
    await call.message.edit_text("Зберігайте та не губіть 💓", reply_markup=make_social_networks_keyboard())
