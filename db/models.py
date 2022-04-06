from typing import Optional

from sqlalchemy import Column, ForeignKey, BigInteger, Text, Integer, Date, Boolean, SmallInteger, text
from sqlalchemy.sql import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from db.base import Base


class GetFilterByMixin:
    @classmethod
    async def get_filter_by(cls, session: AsyncSession, **kwargs):
        instance_result = await session.execute(
            select(cls).where(and_(*(getattr(cls, column_name) == kwargs[column_name] for column_name in kwargs)))
        )
        return instance_result.scalars().first()


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


class Product(Base, GetFilterByMixin):
    __tablename__ = "product"

    id = Column(Integer, primary_key=True)
    price = Column(Integer, nullable=False)
    name = Column(Text, nullable=False)
    quantity = Column(Integer, nullable=False)
    product_folder_id = Column(Integer, ForeignKey("product_folder.id"), nullable=False)

    async def get_url_photo(self, session: AsyncSession) -> str:
        url_photo_result = await session.execute(
            select(ProductPhoto.url).where(ProductPhoto.product_id == self.id)
        )
        url_photo = url_photo_result.scalars().first()
        if url_photo:
            return url_photo
        else:  # TODO стандартне зображення
            return "https://scontent.flwo6-1.fna.fbcdn.net/v/t39.30808-6/266679046_2966535863606892_7419063315773116518_n.jpg?_nc_cat=110&ccb=1-5&_nc_sid=e3f864&_nc_ohc=6ihzWikNgS0AX9LVwTg&_nc_ht=scontent.flwo6-1.fna&oh=00_AT8C03R50kcsiSGk936SPeUsRfEMdpuBV3X42GEbYuXOcA&oe=623C19BA"

    async def get_photo_file_id(self, session: AsyncSession) -> str:
        photo_file_id_result = await session.execute(
            select(ProductPhoto.url).where(ProductPhoto.product_id == self.id)
        )
        photo_file_id = photo_file_id_result.scalars().first()
        if photo_file_id:
            return photo_file_id
        else:  # TODO стандартне зображення
            return "AgACAgIAAxkDAAIGYGJJVKGYIxQ5p_8gVqkf7iRj3unQAALiujEbE90pSjjU3biiWEE4AQADAgADcwADIwQ"


class ProductPhoto(Base):
    __tablename__ = "product_photo"

    file_id = Column(Text, primary_key=True)
    url = Column(Text, nullable=False)
    product_id = Column(Integer, ForeignKey("product.id", ondelete='CASCADE'), nullable=False)


class ProductFolder(Base, GetFilterByMixin):
    __tablename__ = "product_folder"

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    parent_id = Column(Integer, ForeignKey("product_folder.id"), nullable=True)

    async def get_children(self, session: AsyncSession) -> list:
        children_result = await session.execute(
            select(self.__class__).where(self.__class__.parent_id == self.id)
        )
        return children_result.scalars().all()

    async def get_products(self, session: AsyncSession) -> list[Product]:
        products_result = await session.execute(
            select(Product).where(Product.product_folder_id == self.id)
        )
        return products_result.scalars().all()

    @classmethod
    async def get_root_product_folder(cls, session: AsyncSession):
        root_product_folder_result = await session.execute(
            select(cls).where(cls.parent_id.is_(None))
        )
        return root_product_folder_result.scalars().first()


class CartProduct(Base, GetFilterByMixin):
    __tablename__ = "cart_product"

    cart_id = Column(Integer, ForeignKey('cart.id', ondelete='CASCADE'), primary_key=True)
    product_id = Column(Integer, ForeignKey("product.id", ondelete='CASCADE'), primary_key=True)
    quantity = Column(SmallInteger, nullable=False, server_default=text("1"))

    async def change_quantity(self, session: AsyncSession, change_on: int) -> None:
        self.quantity += change_on
        if self.quantity <= 0:
            await session.delete(self)
        await session.commit()

    async def get_product(self, session: AsyncSession) -> Product:
        products_result = await session.execute(
            select(Product).where(Product.id == self.product_id)
        )
        return products_result.scalars().first()


class DataToSend(Base, GetFilterByMixin):
    __tablename__ = "data_to_send"

    cart_id = Column(Integer, ForeignKey("cart.id"), primary_key=True)
    city = Column(Text, nullable=False)
    mail_number = Column(Text, nullable=False)
    full_name = Column(Text, nullable=False)
    phone_number = Column(Text, nullable=False)

    def get_text(self, whith_phone: bool = True) -> str:
        data_to_send_text = f"Город доставки: {self.city}\n" \
                            f"Отделение Новой Почты: {self.mail_number}\n" \
                            f"Получатель: {self.full_name}" \

        return data_to_send_text + f"\n\nКонтакт: {self.phone_number}" if whith_phone else data_to_send_text


class Cart(Base, GetOrCreateMixin):
    __tablename__ = "cart"

    id = Column(Integer, primary_key=True)
    data = Column(Date, nullable=False, server_default=func.now())
    customer_id = Column(BigInteger, ForeignKey("customer.telegram_id"), nullable=False)
    finish = Column(Boolean, nullable=False, server_default=text("False"))
    processed = Column(Boolean, nullable=False, server_default=text("False"))

    async def get_quantity_product_in_cart(self, product: Product, session: AsyncSession) -> int:
        cart_product_result = await session.execute(
            select(CartProduct).where((CartProduct.cart_id == self.id) & (CartProduct.product_id == product.id))
        )
        cart_product: CartProduct = cart_product_result.scalars().first()
        if cart_product:
            return cart_product.quantity
        else:
            return 0

    async def get_amount(self, session: AsyncSession) -> int:
        amount_query = f"select coalesce(SUM(cp.quantity * p.price), 0) AS product_sum " \
                       f"from cart_product cp left join product p on p.id = cp.product_id WHERE cp.cart_id = {self.id}"
        return next(await session.execute(text(amount_query)))[0]

    async def add_product(self, session: AsyncSession, product: Product) -> CartProduct:
        cart_product: CartProduct = await CartProduct.get_filter_by(session, cart_id=self.id, product_id=product.id)
        if cart_product:
            await cart_product.change_quantity(session, +1)
        else:
            cart_product = CartProduct.__call__(cart_id=self.id, product_id=product.id, quantity=1)
            session.add(cart_product)
            await session.commit()

        return cart_product

    async def sub_product(self, session: AsyncSession, product: Product) -> Optional[CartProduct]:
        cart_product: CartProduct = await CartProduct.get_filter_by(session, cart_id=self.id, product_id=product.id)
        if cart_product:
            await cart_product.change_quantity(session, -1)
            return cart_product

    async def get_cart_text(self, session: AsyncSession) -> Optional[str]:
        query = f"select p.name, cp.quantity, p.price from cart_product cp " \
                f"left join product p on p.id = cp.product_id WHERE cp.cart_id = {self.id}"
        cart_text = ""
        amount = 0
        for name, quantity, price in await session.execute(text(query)):
            amount += quantity * price
            cart_text += f"\n{name}\n{quantity} шт. x {price}₴"
        if cart_text:
            cart_text = "Корзина\n\n-----" + cart_text + f"\n-----\n\nИтого: {amount}₴"
            return cart_text
        else:
            return None

    async def get_sorted_cart_products(self, session: AsyncSession) -> list[Optional[CartProduct]]:
        sorted_cart_products_result = await session.execute(
            select(CartProduct).where(CartProduct.cart_id == self.id).order_by(CartProduct.product_id)
        )
        cart_products = sorted_cart_products_result.scalars().all()
        return cart_products

    async def get_data_to_send(self, session: AsyncSession) -> Optional[DataToSend]:
        data_to_send_result = await session.execute(
            select(DataToSend).where(DataToSend.cart_id == self.id)
        )
        data_to_send = data_to_send_result.scalars().first()
        return data_to_send

    async def set_copy(self, session: AsyncSession, cart: 'Cart') -> None:
        old_cart_products = await self.get_sorted_cart_products(session)
        for old_cart_product in old_cart_products:
            await session.delete(old_cart_product)
        copy_cart_products = await cart.get_sorted_cart_products(session)
        new_cart_products = []
        for copy_cart_product in copy_cart_products:
            copy_cart_product.cart_id = self.id
            new_cart_products.append(copy_cart_product)
        session.add_all(new_cart_products)
        await session.commit()


class Customer(Base, GetOrCreateMixin):
    __tablename__ = "customer"

    telegram_id = Column(BigInteger, primary_key=True)

    async def get_finished_carts(self, session: AsyncSession) -> list[Optional[Cart]]:
        finished_carts_result = await session.execute(
            select(Cart).where(Cart.customer_id == self.telegram_id)
        )
        finished_carts = finished_carts_result.scalars().all()
        return finished_carts
