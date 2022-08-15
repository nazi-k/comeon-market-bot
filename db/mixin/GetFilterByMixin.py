from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_


class GetFilterByMixin:
    @classmethod
    async def get_filter_by(cls, session: AsyncSession, **kwargs):
        instance_result = await session.execute(
            select(cls).where(and_(*(getattr(cls, column_name) == kwargs[column_name] for column_name in kwargs)))
        )
        return instance_result.scalars().first()
