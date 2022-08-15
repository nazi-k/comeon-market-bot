from datetime import date
from typing import Optional

from aiogram.types import LabeledPrice
from sqlalchemy import Column, ForeignKey, BigInteger, Text, Integer, Date, Boolean, SmallInteger, text
from sqlalchemy.sql import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from db.base import Base

from data.config import PROVIDER_TOKEN, DEFAULT_PRODUCT_PHOTO_FILE_ID, DEFAULT_PRODUCT_PHOTO_URL

from exception import NotEnoughQuantity, InvoicePayloadToLong

MAX_LEN_DESCRIPTION: int = 255


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
        else:
            return DEFAULT_PRODUCT_PHOTO_URL

    async def get_photo_file_id(self, session: AsyncSession) -> str:
        photo_file_id_result = await session.execute(
            select(ProductPhoto.url).where(ProductPhoto.product_id == self.id)
        )
        photo_file_id = photo_file_id_result.scalars().first()
        if photo_file_id:
            return photo_file_id
        else:
            return DEFAULT_PRODUCT_PHOTO_FILE_ID

    def buy(self, quantity: int):
        if self.quantity < quantity:
            raise NotEnoughQuantity
        self.quantity = self.quantity - quantity


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
            select(Product).where((Product.product_folder_id == self.id) & (Product.quantity > 0))
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

    async def get_product(self, session: AsyncSession) -> Product:
        products_result = await session.execute(
            select(Product).where(Product.id == self.product_id)
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
    raw_payload = Column(Text, nullable=False)
    telegram_payment_charge_id = Column(Text, nullable=True)
    provider_payment_charge_id = Column(Text, nullable=True)

    def get_data_to_send_text(self) -> str:
        data_to_send_text = f"Область: {self.region}\n" \
                            f"Місто: {self.city}\n" \
                            f"Відділення Нової Пошти: {self.nova_poshta_number}\n"
        return data_to_send_text

    async def payment(self, session: AsyncSession) -> bool:
        cart: Cart = await Cart.get_filter_by(session, id=self.cart_id, finish=False)
        if not cart:
            return False
        if self.total_amount != (await cart.get_amount(session) * 100):
            return False
        cart_products = await cart.get_sorted_cart_products(session)
        for cart_product in cart_products:
            product = await Product.get_filter_by(session, id=cart_product.product_id)
            product.buy(cart_product.quantity)
        cart.data = date.today()
        cart.finish = True
        return True


class Cart(Base, GetOrCreateMixin):
    __tablename__ = "cart"

    id = Column(Integer, primary_key=True)
    data = Column(Date, nullable=False, server_default=func.now())
    customer_id = Column(BigInteger, ForeignKey("customer.telegram_id"), nullable=False)
    finish = Column(Boolean, nullable=False, server_default=text("False"))

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
            cart_product = CartProduct(cart_id=self.id, product_id=product.id, quantity=1)
            session.add(cart_product)
        if product.quantity < cart_product.quantity:
            raise NotEnoughQuantity
        await session.commit()
        return cart_product

    async def sub_product(self, session: AsyncSession, product: Product) -> Optional[CartProduct]:
        cart_product: CartProduct = await CartProduct.get_filter_by(session, cart_id=self.id, product_id=product.id)
        if cart_product:
            await cart_product.change_quantity(session, -1)
            await session.commit()
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
            cart_text = "Кошик\n\n-----" + cart_text + "\n-----\n" + f"\nРазом: {amount}₴"
            return cart_text
        else:
            return None

    async def get_sorted_cart_products(self, session: AsyncSession) -> list[Optional[CartProduct]]:
        sorted_cart_products_result = await session.execute(
            select(CartProduct).where(CartProduct.cart_id == self.id).order_by(CartProduct.product_id)
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
        copy_cart_products = await cart.get_sorted_cart_products(session)
        for copy_cart_product in copy_cart_products:
            await session.merge(CartProduct(cart_id=self.id,
                                            product_id=copy_cart_product.product_id,
                                            quantity=copy_cart_product.quantity))
        await session.commit()

    async def get_data_to_invoice(self,
                                  region: str,
                                  city: str,
                                  nova_poshta_number: str,
                                  session: AsyncSession, **kwargs) -> dict:
        cart_products = await self.get_sorted_cart_products(session)
        prices = []
        product_name_and_quantity = []
        for cart_product in cart_products:
            product = await cart_product.get_product(session)
            prices.append(
                LabeledPrice(label=f"{product.name} "
                                   f"{' x ' + str(cart_product.quantity) if cart_product.quantity > 1 else ''}",
                             amount=(cart_product.quantity * product.price) * 100)
            )
            product_name_and_quantity.append(
                product.name + ' x ' + str(cart_product.quantity) if cart_product.quantity > 1 else product.name
            )
        description = ', '.join(product_name_and_quantity)
        if len(description) > MAX_LEN_DESCRIPTION:
            description = description[:(MAX_LEN_DESCRIPTION - 3)] + '...'
        payload = f"{self.id}:" \
                  f"{region.replace(':', '{..}')}:" \
                  f"{city.replace(':', '{..}')}:" \
                  f"{nova_poshta_number.replace(':', '{..}')}"
        if len(payload.encode('utf-8')) > 128:
            raise InvoicePayloadToLong
        data_to_invoice = {
            "title": f"Замовлення #{self.id}",
            "description": description,
            "payload": payload,
            "provider_token": PROVIDER_TOKEN,
            "currency": "uah",
            "prices": prices,
            "need_name": True,
            "need_phone_number": True,
            "send_phone_number_to_provider": True
        }
        if len(cart_products) == 1:
            product = await cart_products[0].get_product(session)
            data_to_invoice["photo_url"] = await product.get_url_photo(session)
        else:
            data_to_invoice["photo_url"] = DEFAULT_PRODUCT_PHOTO_URL
        return data_to_invoice


class Customer(Base, GetOrCreateMixin):
    __tablename__ = "customer"

    telegram_id = Column(BigInteger, primary_key=True)

    async def get_finished_carts(self, session: AsyncSession) -> list[Optional[Cart]]:
        finished_carts_result = await session.execute(
            select(Cart).where((Cart.customer_id == self.telegram_id) & (Cart.finish == True))
        )
        finished_carts = finished_carts_result.scalars().all()
        return finished_carts
