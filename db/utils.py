from data import config


def make_connection_string(async_fallback: bool = False) -> str:
    result = config.DATABASE_URL.replace("postgres", "postgresql+asyncpg", 1)
    if async_fallback:
        result += "?async_fallback=True"
    return result
