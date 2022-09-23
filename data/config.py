from environs import Env
import os

import re

env = Env()
env.read_env()

BOT_TOKEN = env.str("BOT_TOKEN")  # Забираем значение типа str
ADMINS = env.list("ADMINS")  # Тут у нас будет список из админов
MANAGER_USERNAME = env.str("manager_username")

DATABASE_URL = os.environ.get('DATABASE_URL')

REDIS_PASSWORD, REDIS_HOST, REDIS_PORT = re.findall(r"//:(.+)@(.+):(\d+)", os.environ.get('REDIS_URL'))[0]

HEROKU_APP_NAME = env.str("app_name")

WEBHOOK_HOST = f'https://{HEROKU_APP_NAME}.herokuapp.com'
WEBHOOK_PATH = f'/webhook/{BOT_TOKEN}'
WEBHOOK_URL = f'{WEBHOOK_HOST}{WEBHOOK_PATH}'

# webserver settings
WEBAPP_HOST = env.str("ip")
WEBAPP_PORT = int(os.environ.get('PORT', 5000))

DEFAULT_PHOTO_FILE_ID = env.dict(
    "default_photo_file_id", subcast_values=str
)
DEFAULT_PHOTO_URL = env.dict(
    "default_photo_url", subcast_values=str
)
CREDENTIALS_FILE = env.path("credentials_file")
SPREADSHEET_ID = env.str("spreadsheet_id")
