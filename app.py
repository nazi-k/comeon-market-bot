from aiogram.utils.executor import start_webhook

from db.base import metadata
from loader import dp, engine
import middlewares, handlers

from data.config import WEBHOOK_URL, WEBHOOK_PATH, WEBAPP_HOST, WEBAPP_PORT


async def on_startup(dispatcher):
    # Перевіряє структуру бд
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)

    await dp.bot.set_webhook(WEBHOOK_URL, drop_pending_updates=True)


if __name__ == '__main__':
    start_webhook(
        dispatcher=dp,
        webhook_path=WEBHOOK_PATH,
        skip_updates=True,
        on_startup=on_startup,
        host=WEBAPP_HOST,
        port=WEBAPP_PORT,
    )
