"""Short-lived database sessions and atomic order creation."""

from sqlalchemy import select, update
from sqlalchemy.dialects.sqlite import insert

from app.database.models import Category, Item, MainCategory, Order, User, async_session


async def get_user(tg_id: int) -> User | None:
    async with async_session() as session:
        return await session.get(User, tg_id)


async def get_maincategories() -> list[MainCategory]:
    async with async_session() as session:
        return list(await session.scalars(select(MainCategory).order_by(MainCategory.id)))


async def get_categories(main_category_id: int) -> list[Category]:
    async with async_session() as session:
        query = select(Category).where(Category.main_category == str(main_category_id))
        return list(await session.scalars(query.order_by(Category.id)))


async def get_category(category_id: int) -> Category | None:
    async with async_session() as session:
        return await session.get(Category, category_id)


async def get_items(category_id: int) -> list[Item]:
    async with async_session() as session:
        query = select(Item).where(Item.category == category_id).order_by(Item.id)
        return list(await session.scalars(query))


async def get_item(item_id: int) -> Item | None:
    async with async_session() as session:
        return await session.get(Item, item_id)


async def create_order(
    *,
    checkout_key: str,
    item_id: int,
    tg_id: int,
    username: str | None,
    name: str,
    phone: str,
    email: str,
) -> Order | None:
    """Save customer and product snapshots together; repeated submissions reuse the order."""
    async with async_session.begin() as session:
        existing = await session.scalar(select(Order).where(Order.checkout_key == checkout_key))
        if existing:
            return existing
        item = await session.get(Item, item_id)
        if item is None:
            return None
        customer = dict(tg_id=tg_id, username=username or "", name=name, phone=phone, email=email)
        user_insert = insert(User).values(**customer)
        await session.execute(
            user_insert.on_conflict_do_update(
                index_elements=[User.tg_id],
                set_=customer,
            )
        )
        order_insert = insert(Order).values(
            **customer,
            checkout_key=checkout_key,
            item_id=item.id,
            item_name=item.name,
            item_description=item.description,
            price=item.price,
        )
        await session.execute(
            order_insert.on_conflict_do_nothing(index_elements=[Order.checkout_key])
        )
        return await session.scalar(select(Order).where(Order.checkout_key == checkout_key))


async def mark_order_notified(order_id: int) -> None:
    async with async_session.begin() as session:
        await session.execute(update(Order).where(Order.id == order_id).values(notified=True))
