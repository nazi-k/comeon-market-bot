from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from data.config import DEFAULT_PHOTO_URL, DEFAULT_PHOTO_FILE_ID


class GetPhotoMixin:
    """
    Дістає дані з таблиці  [__tablename__+'_photo']

    Стовбці [url], [file_id]
    """
    async def get_photo_url(self, session: AsyncSession) -> str:
        photo_url_result = await session.execute(
            select(text(self.__tablename__ + "_photo.url"))
            .select_from(text(self.__tablename__ + "_photo"))
            .where(text(self.__tablename__ + "_photo." + self.__tablename__ + "_id = " + f"{self.id}"))
        )
        photo_url = photo_url_result.scalars().first()
        if photo_url:
            return photo_url
        else:
            return DEFAULT_PHOTO_URL[self.__tablename__]

    async def get_photo_file_id(self, session: AsyncSession) -> str:
        photo_file_id_result = await session.execute(
            select(text(self.__tablename__ + "_photo.file_id"))
            .select_from(text(self.__tablename__ + "_photo"))
            .where(text(self.__tablename__ + "_photo." + self.__tablename__ + "_id = " + f"{self.id}"))
        )
        photo_file_id = photo_file_id_result.scalars().first()
        if photo_file_id:
            return photo_file_id
        else:
            return DEFAULT_PHOTO_FILE_ID[self.__tablename__]
