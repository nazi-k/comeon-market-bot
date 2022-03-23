from sqlalchemy.ext.asyncio import AsyncSession


class GetFilterByMixin:
    @classmethod
    async def get_filter_by(cls, session: AsyncSession, **field_value):
        instance = await session.query(cls).filter_by(**field_value).first()
        return instance
