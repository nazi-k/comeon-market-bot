from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.redis import RedisStorage2

from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from db.utils import make_connection_string

from middlewares.db import DbSessionMiddleware

from data import config

# Creating bot and its dispatcher and storage
bot = Bot(token=config.BOT_TOKEN, parse_mode=types.ParseMode.HTML)
storage = RedisStorage2(host=config.REDIS_HOST, port=config.REDIS_PORT, password=config.REDIS_PASSWORD, db=0)
dp = Dispatcher(bot, storage=storage)


# Creating DB engine for PostgreSQL
engine = create_async_engine(
    make_connection_string(),
    future=True,
    echo=False
)

# Creating DB connections pool
db_pool = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


# Register middlewares
dp.middleware.setup(DbSessionMiddleware(db_pool))
