"""Populate an empty catalog with fictional demo products: python -m app.seed."""

import asyncio

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.database.models import Category, Item, MainCategory, async_main, async_session, engine


async def seed_catalog(sessions: async_sessionmaker[AsyncSession] = async_session) -> bool:
    async with sessions.begin() as session:
        # Refuse to mix demo data with any existing catalog, even an incomplete one.
        for model in (MainCategory, Category, Item):
            if await session.scalar(select(func.count()).select_from(model)):
                return False
        session.add_all(
            [
                MainCategory(id=1, name="Спортивная одежда"),
                MainCategory(id=2, name="Аксессуары"),
            ]
        )
        await session.flush()
        session.add_all(
            [
                Category(id=1, name="Футболки", main_category="1"),
                Category(id=2, name="Инвентарь", main_category="2"),
            ]
        )
        await session.flush()
        session.add_all(
            [
                Item(
                    id=1,
                    name="Футболка GYM RATS",
                    description="Демонстрационный товар: хлопковая футболка для тренировок.",
                    price=1900,
                    category=1,
                    main_category="1",
                ),
                Item(
                    id=2,
                    name="Скакалка",
                    description="Демонстрационный товар: скакалка для разминки.",
                    price=700,
                    category=2,
                    main_category="2",
                ),
            ]
        )
    return True


async def main() -> None:
    try:
        await async_main()
        added = await seed_catalog()
        print("Демокаталог создан." if added else "Каталог уже содержит данные. Изменений нет.")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
