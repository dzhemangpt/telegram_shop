"""SQLite models. Existing catalog tables retain their original schema."""

from datetime import UTC, datetime

from sqlalchemy import ForeignKey, LargeBinary, String
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.config import database_url

engine = create_async_engine(database_url())
async_session = async_sessionmaker(engine, expire_on_commit=False)


class Base(AsyncAttrs, DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    tg_id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(30))
    name: Mapped[str] = mapped_column(String(25))
    phone: Mapped[str] = mapped_column(String(15))
    email: Mapped[str] = mapped_column(String(50))


class MainCategory(Base):
    __tablename__ = "maincategories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(30))


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(25))
    # Legacy SQLite catalogs store these references as strings.
    main_category: Mapped[str] = mapped_column(String(20), ForeignKey("maincategories.id"))


class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    description: Mapped[str] = mapped_column(String(300))
    price: Mapped[int]
    category: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    picture: Mapped[bytes | None] = mapped_column(LargeBinary)
    main_category: Mapped[str] = mapped_column(String(20), ForeignKey("maincategories.id"))


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    checkout_key: Mapped[str] = mapped_column(String(32), unique=True)
    tg_id: Mapped[int] = mapped_column(ForeignKey("users.tg_id"))
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"))
    username: Mapped[str]
    name: Mapped[str]
    phone: Mapped[str]
    email: Mapped[str]
    item_name: Mapped[str]
    item_description: Mapped[str]
    price: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    notified: Mapped[bool] = mapped_column(default=False)


async def async_main() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
