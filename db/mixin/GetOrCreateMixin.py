from sqlalchemy.ext.asyncio import AsyncSession


class GetOrCreateMixin:
    @classmethod
    async def get_or_create(cls, session: AsyncSession, **field_value):
        instance = await session.query(cls).filter_by(**field_value).first()
        if instance:
            return instance
        else:
            instance = cls(**field_value)
            session.add(instance)
            await session.commit()
            return instance
