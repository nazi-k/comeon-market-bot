from sqlalchemy.ext.asyncio import AsyncSession

from db.mixin import GetFilterByMixin


class GetOrCreateMixin(GetFilterByMixin):
    @classmethod
    async def get_or_create(cls, session: AsyncSession, **kwargs):
        instance = await cls.get_filter_by(session, **kwargs)
        if instance:
            return instance
        else:
            instance = cls.__call__(**kwargs)
            session.add(instance)
            await session.commit()
            return instance
