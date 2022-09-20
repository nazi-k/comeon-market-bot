from aiogram import types

from data.config import ADMINS

from loader import dp


@dp.message_handler(content_types=['photo', 'video', 'document'], chat_id=ADMINS)
async def photo_file_id(message: types.Message):
    await message.reply(str(message))
