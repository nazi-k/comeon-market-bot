from aiogram.dispatcher.middlewares import LifetimeControllerMiddleware

import ssl
ssl_object = ssl.create_default_context()
ssl_object.check_hostname = False
ssl_object.verify_mode = ssl.CERT_NONE


class DbSessionMiddleware(LifetimeControllerMiddleware):
    skip_patterns = ["error", "update"]

    def __init__(self, session_pool):
        super().__init__()
        self.session_pool = session_pool

    async def pre_process(self, obj, data, *args):
        session = self.session_pool(ssl=ssl_object)
        data["session"] = session

    async def post_process(self, obj, data, *args):
        session = data.get("session")
        if session:
            await session.close()
