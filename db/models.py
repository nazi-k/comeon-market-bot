from datetime import datetime
from typing import Optional, Union

from sqlalchemy import Column, ForeignKey, BigInteger, Text, Integer, Boolean, SmallInteger, text, Unicode, \
    UnicodeText, TIMESTAMP,  delete
from sqlalchemy.orm.collections import attribute_mapped_collection
from sqlalchemy.sql import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import relationship, selectinload

from data.config import DEFAULT_PHOTO_URL, DEFAULT_PHOTO_FILE_ID
from db.base import Base

from db.mixin import GetFilterByMixin, GetOrCreateMixin, GetPhotoMixin

from exception import NotEnoughQuantity


class Product(Base, GetFilterByMixin):
    __tablename__ = "product"

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    category_id = Column(Integer, ForeignKey("category.id"), nullable=False)
    product_modifications = relationship("ProductModification", order_by="ProductModification.id")

    @classmethod
    async def get_filter_by(cls, session: AsyncSession, **kwargs):
        instance_result = await session.execute(
            select(cls)
            .where(and_(*(getattr(cls, column_name) == kwargs[column_name] for column_name in kwargs)))
            .options(selectinload(cls.product_modifications))

        )
        return instance_result.scalars().first()

    @property
    def indexes_and_product_modifications_with_positive_quantity(self) -> \
            Union[tuple[dict[str, Union[int, 'ProductModification']], ...], tuple]:
        return tuple(
            dict(index=index, product_modification=product_modification)
            for (index, product_modification) in enumerate(self.product_modifications)
            if product_modification.quantity > 0
        )

    def get_min_product_modification_price(self) -> int:
        return min((indexes_and_product_modification['product_modification'].price
                    for indexes_and_product_modification
                    in self.indexes_and_product_modifications_with_positive_quantity))


class ProductModification(Base, GetFilterByMixin, GetPhotoMixin):
    __tablename__ = "product_modification"

    id = Column(Integer, primary_key=True)
    product_id = Column(ForeignKey("product.id", ondelete='CASCADE'))
    price = Column(Integer, nullable=False)
    quantity = Column(Integer, nullable=False)
    description = Column(Text, nullable=False)

    modifications = relationship(
        "Modification", collection_class=attribute_mapped_collection("key")
    )

    async def get_modifications_value(self, session: AsyncSession) -> list[str]:
        children_result = await session.execute(
            select(Modification.value).where(Modification.product_modification_id == self.id)
        )
        return children_result.scalars().all()

    async def get_name_with_value(self, session: AsyncSession) -> str:
        query = "select (p.name || ' ' || rez.modifications) as name_with_value " \
                "from (select array_to_string(ARRAY_AGG(m.value), ' ') as modifications, " \
                "      MAX(pm.product_id) as product_id " \
                "      from product_modification pm " \
                "      left join modification m on pm.id = m.product_modification_id " \
                f"     where pm.id = {self.id} " \
                "      group by m.product_modification_id) rez " \
                "left join product p on p.id = rez.product_id"
        instance_result = await session.execute(text(query))
        return instance_result.scalars().first()

    def buy(self, quantity: int):
        if self.quantity < quantity:
            raise NotEnoughQuantity
        self.quantity = self.quantity - quantity


class Modification(Base):
    __tablename__ = "modification"

    product_modification_id = Column(ForeignKey("product_modification.id"), primary_key=True)
    key = Column(Unicode(64), primary_key=True)
    value = Column(UnicodeText, nullable=False)


class ProductModificationPhoto(Base):
    __tablename__ = "product_modification_photo"

    file_id = Column(Text, nullable=False)
    url = Column(Text, nullable=True)
    product_modification_id = Column(Integer,
                                     ForeignKey("product_modification.id", ondelete='CASCADE'),
                                     primary_key=True)


class CategoryPhoto(Base):
    __tablename__ = "category_photo"

    file_id = Column(Text, primary_key=True)
    url = Column(Text, nullable=True)
    category_id = Column(Integer, ForeignKey("category.id", ondelete='CASCADE'), nullable=False)


class Category(Base, GetFilterByMixin, GetPhotoMixin):
    __tablename__ = "category"

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    parent_id = Column(Integer, ForeignKey("category.id"), nullable=True)

    async def get_children(self, session: AsyncSession) -> list['Category']:
        children_result = await session.execute(
            select(self.__class__).where(self.__class__.parent_id == self.id)
        )
        return children_result.scalars().all()

    async def get_products(self, session: AsyncSession) -> list[Product]:
        products_result = await session.execute(
            select(Product).where(Product.category_id == self.id).options(selectinload(Product.product_modifications))
        )
        return products_result.scalars().all()

    async def get_min_product_price(self, session: AsyncSession) -> list[Product]:
        products = await self.get_products(session)
        if products:
            return min((product.get_min_product_modification_price() for product in products))
        else:
            return None
    
    @classmethod
    async def get_root(cls, session: AsyncSession):
        root_category_result = await session.execute(
            select(cls).where(cls.parent_id.is_(None))
        )
        return root_category_result.scalars().first()


class CartProductModification(Base, GetFilterByMixin):
    __tablename__ = "cart_product_modification"

    cart_id = Column(Integer, ForeignKey('cart.id', ondelete='CASCADE'), primary_key=True)
    product_modification_id = Column(ForeignKey("product_modification.id", ondelete='CASCADE'), primary_key=True)
    quantity = Column(SmallInteger, nullable=False, server_default=text("1"))

    async def change_quantity(self, session: AsyncSession, change_on: int) -> None:
        self.quantity += change_on
        if self.quantity <= 0:
            await session.delete(self)

    async def get_product_modification(self, session: AsyncSession) -> ProductModification:
        products_result = await session.execute(
            select(ProductModification).where(ProductModification.id == self.product_modification_id)
        )
        return products_result.scalars().first()


class Order(Base, GetFilterByMixin):
    __tablename__ = "order"

    id = Column(Integer, primary_key=True)
    cart_id = Column(Integer, ForeignKey("cart.id"), nullable=False)
    region = Column(Text, nullable=False)
    city = Column(Text, nullable=False)
    nova_poshta_number = Column(Text, nullable=False)
    full_name = Column(Text, nullable=False)
    phone_number = Column(Text, nullable=False)
    total_amount = Column(Integer, nullable=False)

    def get_data_to_send_text(self) -> str:
        data_to_send_text = f"Область: {self.region}\n" \
                            f"Місто: {self.city}\n" \
                            f"Відділення Нової Пошти: {self.nova_poshta_number}\n" \
                            f"Одержувач: {self.full_name}\n" \
                            f"Номер одержувача: {self.phone_number}\n"
        return data_to_send_text


class Cart(Base, GetOrCreateMixin):
    __tablename__ = "cart"

    id = Column(Integer, primary_key=True)
    date_time = Column(TIMESTAMP, nullable=False, server_default=func.now())
    customer_id = Column(BigInteger, ForeignKey("customer.telegram_id"), nullable=False)
    message_id = Column(Integer, nullable=True)
    finish = Column(Boolean, nullable=False, server_default=text("False"))

    async def clear(self, session: AsyncSession, commit: bool = False):
        stmt = (
            delete(CartProductModification).
            where(CartProductModification.cart_id == self.id)
        )
        await session.execute(stmt)
        if commit:
            await session.commit()

    async def get_quantity_product_in_cart(self, product_modification: ProductModification, session: AsyncSession) \
            -> int:
        cart_product_quantity_result = await session.execute(
            select(CartProductModification.quantity)
            .where((CartProductModification.cart_id == self.id) &
                   (CartProductModification.product_modification_id == product_modification.id))
        )
        cart_product_quantity: CartProductModification = cart_product_quantity_result.scalars().first()
        if cart_product_quantity:
            return cart_product_quantity
        else:
            return 0

    async def get_amount(self, session: AsyncSession) -> int:
        amount_query = f"select coalesce(SUM(cpm.quantity * pm.price), 0) AS product_sum " \
                       f"from cart_product_modification cpm left join " \
                       f"product_modification pm on pm.id = cpm.product_modification_id WHERE cpm.cart_id = {self.id}"
        return next(await session.execute(text(amount_query)))[0]

    async def add_product_modification(self, session: AsyncSession, product_modification: ProductModification) \
            -> CartProductModification:
        cart_product_modification: CartProductModification = await CartProductModification.get_filter_by(
            session, cart_id=self.id, product_modification_id=product_modification.id)
        if cart_product_modification:
            await cart_product_modification.change_quantity(session, +1)
        else:
            cart_product_modification = CartProductModification(
                cart_id=self.id,
                product_modification_id=product_modification.id,
                quantity=1
            )
            session.add(cart_product_modification)
        if product_modification.quantity < cart_product_modification.quantity:
            raise NotEnoughQuantity
        await session.commit()
        return cart_product_modification

    async def sub_product_modification(self, session: AsyncSession, product_modification: ProductModification) -> \
            Optional[CartProductModification]:
        cart_product_modification: CartProductModification = await CartProductModification.get_filter_by(
            session, cart_id=self.id, product_modification_id=product_modification.id)
        if cart_product_modification:
            await cart_product_modification.change_quantity(session, -1)
            await session.commit()
            return cart_product_modification

    async def get_cart_text(self, session: AsyncSession) -> Optional[str]:
        query = "select (c.name || ' ' || p.name || ' ' || rez.modifications) as product_modification_name, rez.quantity, rez.price " \
                "from (select MAX(pm.product_id) as product_id, " \
                "      array_to_string(ARRAY_AGG(m.value), ' ') as modifications, " \
                "      MAX(cpm.quantity) as quantity, MAX(pm.price) as price " \
                "      from product_modification pm " \
                "      left join modification m on pm.id = m.product_modification_id " \
                "      left join cart_product_modification cpm on pm.id = cpm.product_modification_id " \
                f"     where cpm.cart_id = {self.id} " \
                "      group by m.product_modification_id) rez " \
                "left join product p on rez.product_id = p.id " \
                "left join category c on p.category_id = c.id"
        cart_text = ""
        amount = 0
        for product_modification_name, quantity, price in await session.execute(text(query)):
            amount += quantity * price
            cart_text += f"\n{product_modification_name}\n{quantity} шт. x {price}₴"
        if cart_text:
            cart_text = cart_text + "\n-----\n" + f"\nРазом: {amount}₴"
            return cart_text
        else:
            return None

    async def get_sorted_cart_products(self, session: AsyncSession) -> list[Optional[CartProductModification]]:
        sorted_cart_products_result = await session.execute(
            select(CartProductModification)
            .where(CartProductModification.cart_id == self.id)
            .order_by(CartProductModification.product_modification_id)
        )
        cart_products = sorted_cart_products_result.scalars().all()
        return cart_products

    async def get_order(self, session: AsyncSession) -> Optional[Order]:
        order_result = await session.execute(
            select(Order).where(Order.cart_id == self.id)
        )
        order = order_result.scalars().first()
        return order

    async def set_copy(self, session: AsyncSession, cart: 'Cart') -> None:
        await self.clear(session)
        copy_cart_products = await cart.get_sorted_cart_products(session)
        for copy_cart_product in copy_cart_products:
            session.add(CartProductModification(cart_id=self.id,
                                                product_modification_id=copy_cart_product.product_modification_id,
                                                quantity=copy_cart_product.quantity))
            await session.commit()

    async def confirmation_buy(self, session: AsyncSession) -> bool:
        try:
            cart_products = await self.get_sorted_cart_products(session)
            for cart_product in cart_products:
                product_odification = await ProductModification.get_filter_by(
                    session, id=cart_product.product_modification_id
                )
                product_odification.buy(cart_product.quantity)
            self.date_time = datetime.now()
            self.finish = True
            return True
        except NotEnoughQuantity:
            return False

    @property
    def date(self) -> datetime.date:
        return self.date_time.date()

    @classmethod
    def get_photo_url(cls) -> str:
        return DEFAULT_PHOTO_URL[cls.__tablename__]

    @classmethod
    def get_photo_file_id(cls) -> str:
        return DEFAULT_PHOTO_FILE_ID[cls.__tablename__]


class Customer(Base, GetOrCreateMixin):
    __tablename__ = "customer"

    telegram_id = Column(BigInteger, primary_key=True)

    async def get_finished_carts(self, session: AsyncSession) -> list[Optional[Cart]]:
        finished_carts_result = await session.execute(
            select(Cart).where((Cart.customer_id == self.telegram_id) & (Cart.finish == True))
        )
        finished_carts = finished_carts_result.scalars().all()
        return finished_carts
