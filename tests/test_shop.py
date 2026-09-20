"""Exercise real aiogram routing and SQLite; Telegram transport is replaced."""

import asyncio
import importlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from aiogram import Bot, Dispatcher
from aiogram.client.session.base import BaseSession
from aiogram.exceptions import TelegramForbiddenError
from aiogram.fsm.storage.memory import SimpleEventIsolation
from aiogram.methods import AnswerCallbackQuery, SendMessage, SendPhoto
from aiogram.types import Update
from sqlalchemy import delete, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.database.requests as req
import app.handlers as handlers
from app.database.models import Base, Category, Item, MainCategory, Order
from app.seed import seed_catalog


class FakeTelegram(BaseSession):
    def __init__(self):
        super().__init__()
        self.calls = []
        self.fail_admin = False

    async def close(self):
        pass

    async def make_request(self, bot, method, timeout=None):
        self.calls.append(method)
        if self.fail_admin and isinstance(method, SendMessage) and method.chat_id == 999:
            raise TelegramForbiddenError(method=method, message="Bot blocked")
        return True

    async def stream_content(self, url, **kwargs):
        raise AssertionError("Tests must not access the network")
        yield b""


class ShopTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.engine = create_async_engine(f"sqlite+aiosqlite:///{Path(self.temp.name) / 'test.db'}")
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        await seed_catalog(self.sessions)
        self.db_patch = patch.object(req, "async_session", self.sessions)
        self.db_patch.start()
        importlib.reload(handlers)
        self.telegram = FakeTelegram()
        self.bot = Bot(token="123456:TEST_TOKEN_FOR_OFFLINE_TESTS", session=self.telegram)
        self.dp = Dispatcher(events_isolation=SimpleEventIsolation())
        self.dp.include_router(handlers.router)
        self.sequence = 0

    async def asyncTearDown(self):
        await self.dp.storage.close()
        await self.dp.fsm.events_isolation.close()
        await self.bot.session.close()
        self.db_patch.stop()
        await self.engine.dispose()
        self.temp.cleanup()

    async def send(self, text=None, *, user=101, callback=None, chat_type="private"):
        self.sequence += 1
        person = {"id": user, "is_bot": False, "first_name": "Buyer"}
        message = {
            "message_id": self.sequence,
            "date": 1700000000,
            "chat": {"id": user, "type": chat_type},
            "from": person,
        }
        if text is not None:
            message["text"] = text
        else:
            message["photo"] = [
                {"file_id": "photo", "file_unique_id": "unique", "width": 1, "height": 1}
            ]
        if callback is None:
            payload = {"message": message}
        else:
            payload = {
                "callback_query": {
                    "id": str(self.sequence),
                    "from": person,
                    "chat_instance": "test",
                    "data": callback,
                    "message": message,
                }
            }
        return await self.dp.feed_update(
            self.bot,
            Update.model_validate({"update_id": self.sequence, **payload}),
            admin_chat_id=999,
        )

    def state(self, user=101):
        return self.dp.fsm.get_context(bot=self.bot, chat_id=user, user_id=user)

    async def checkout(self, user=101, item=1):
        await self.send(callback=f"buy_{item}", user=user)
        await self.send("Анна", user=user)
        await self.send("89991234567", user=user)
        await self.send("buyer@example.com", user=user)

    async def orders(self):
        async with self.sessions() as session:
            return list(await session.scalars(select(Order).order_by(Order.id)))

    def messages(self):
        return [call for call in self.telegram.calls if isinstance(call, SendMessage)]

    async def test_full_checkout_without_username(self):
        await self.checkout()
        orders = await self.orders()
        self.assertEqual(len(orders), 1)
        order = orders[0]
        self.assertEqual((order.item_name, order.price), ("Футболка GYM RATS", 1900))
        self.assertEqual(order.phone, "+79991234567")
        self.assertEqual(order.username, "")
        self.assertTrue(order.notified)
        self.assertIsNone(await self.state().get_state())
        user = await req.get_user(101)
        self.assertEqual(user.email, "buyer@example.com")
        self.assertTrue(any(call.chat_id == 999 for call in self.messages()))

    async def test_returning_customer_gets_saved_fields(self):
        await self.checkout()
        await self.send(callback="buy_2")
        self.assertEqual(self.messages()[-1].reply_markup.keyboard[0][0].text, "Анна")
        await self.send("Мария")
        self.assertEqual(self.messages()[-1].reply_markup.keyboard[0][0].text, "+79991234567")
        await self.send("+79997654321")
        self.assertEqual(self.messages()[-1].reply_markup.keyboard[0][0].text, "buyer@example.com")
        await self.send("new@example.com")
        self.assertEqual((await req.get_user(101)).name, "Мария")
        self.assertEqual((await self.orders())[0].name, "Анна")

    async def test_non_text_and_invalid_input_do_not_advance(self):
        await self.send(callback="buy_1")
        for text in (None, " ", "a" * 26):
            await self.send(text)
            self.assertEqual(await self.state().get_state(), "Checkout:name")
        await self.send("Анна")
        for text in (None, "123"):
            await self.send(text)
            self.assertEqual(await self.state().get_state(), "Checkout:phone")
        await self.send("+79991234567")
        for text in (None, "bad@", "a@-example.com"):
            await self.send(text)
            self.assertEqual(await self.state().get_state(), "Checkout:email")
        self.assertEqual(await self.orders(), [])

    async def test_commands_work_at_every_step(self):
        for state in (handlers.Checkout.name, handlers.Checkout.phone, handlers.Checkout.email):
            for command in ("/cancel", "/start", "/shop", "🛍Каталог"):
                await self.state().set_state(state)
                await self.state().update_data(name="Old")
                await self.send(command)
                self.assertIsNone(await self.state().get_state())
                self.assertEqual(await self.state().get_data(), {})

    async def test_help_and_unknown_command_preserve_checkout(self):
        await self.send(callback="buy_1")
        for command in ("/help", "/unknown"):
            await self.send(command)
            self.assertEqual(await self.state().get_state(), "Checkout:name")
        self.assertNotIn("name", await self.state().get_data())

    async def test_navigation_is_independent_for_two_customers(self):
        await self.send(callback="main_1", user=101)
        await self.send(callback="main_2", user=202)
        await self.send(callback="category_1", user=101)
        back = self.messages()[-1].reply_markup.inline_keyboard[-2][0]
        self.assertEqual(back.callback_data, "main_1")
        await self.send(callback="category_2", user=202)
        back = self.messages()[-1].reply_markup.inline_keyboard[-2][0]
        self.assertEqual(back.callback_data, "main_2")
        await self.send(callback="buy_1", user=101)
        await self.send(callback="buy_2", user=202)
        self.assertEqual((await self.state(101).get_data())["item_id"], 1)
        self.assertEqual((await self.state(202).get_data())["item_id"], 2)

    async def test_catalog_and_photo_optional(self):
        await self.send("/shop")
        self.assertEqual(len(self.messages()[-1].reply_markup.inline_keyboard), 2)
        await self.send(callback="item_1")
        self.assertIn("1900", self.messages()[-1].text)
        self.assertFalse(any(isinstance(call, SendPhoto) for call in self.telegram.calls))
        async with self.sessions.begin() as session:
            entry = await session.get(Item, 1)
            entry.picture = b"fake image for mocked transport"
        await self.send(callback="item_1")
        self.assertTrue(any(isinstance(call, SendPhoto) for call in self.telegram.calls))

    async def test_missing_products_and_malformed_callbacks(self):
        for callback in (
            "item_999",
            "buy_999",
            "category_999",
            "buy_bad",
            "item_-1",
            "item_" + "9" * 50,
            "go_back",
            "category",
        ):
            count = len(self.telegram.calls)
            await self.send(callback=callback)
            calls = self.telegram.calls[count:]
            self.assertTrue(any(isinstance(call, AnswerCallbackQuery) for call in calls))
        self.assertIsNone(await self.state().get_state())

    async def test_product_removed_during_checkout(self):
        await self.send(callback="buy_1")
        await self.send("Анна")
        await self.send("+79991234567")
        async with self.sessions.begin() as session:
            await session.execute(delete(Item).where(Item.id == 1))
        await self.send("buyer@example.com")
        self.assertEqual(await self.orders(), [])
        self.assertIsNone(await self.state().get_state())

    async def test_admin_failure_keeps_order_and_clears_form(self):
        self.telegram.fail_admin = True
        with self.assertLogs("app.handlers", level="ERROR"):
            await self.checkout()
        order = (await self.orders())[0]
        self.assertFalse(order.notified)
        self.assertIsNone(await self.state().get_state())
        self.assertIn("временно не доставлено", self.messages()[-1].text)

    async def test_database_failure_allows_retry(self):
        await self.send(callback="buy_1")
        await self.send("Анна")
        await self.send("+79991234567")
        with patch.object(req, "create_order", side_effect=SQLAlchemyError("test")):
            with self.assertLogs("app.handlers", level="ERROR"):
                await self.send("buyer@example.com")
        self.assertEqual(await self.state().get_state(), "Checkout:email")
        self.assertEqual(await self.orders(), [])
        await self.send("buyer@example.com")
        self.assertEqual(len(await self.orders()), 1)

    async def test_duplicate_email_updates_create_only_one_order(self):
        await self.send(callback="buy_1")
        await self.send("Анна")
        await self.send("+79991234567")
        await asyncio.gather(self.send("buyer@example.com"), self.send("buyer@example.com"))
        self.assertEqual(len(await self.orders()), 1)
        self.assertEqual(sum(call.chat_id == 999 for call in self.messages()), 1)

    async def test_order_creation_is_idempotent_and_snapshots_product(self):
        params = dict(
            checkout_key="same",
            item_id=1,
            tg_id=101,
            username=None,
            name="Анна",
            phone="+79991234567",
            email="buyer@example.com",
        )
        first = await req.create_order(**params)
        async with self.sessions.begin() as session:
            item = await session.get(Item, 1)
            item.price = 3000
        second = await req.create_order(**params)
        self.assertEqual(first.id, second.id)
        self.assertEqual(second.price, 1900)
        self.assertEqual(len(await self.orders()), 1)

    async def test_concurrent_repository_submissions_share_order(self):
        params = dict(
            checkout_key="parallel",
            item_id=1,
            tg_id=101,
            username=None,
            name="Анна",
            phone="+79991234567",
            email="buyer@example.com",
        )
        first, second = await asyncio.gather(
            req.create_order(**params),
            req.create_order(**params),
        )
        self.assertEqual(first.id, second.id)
        self.assertEqual(len(await self.orders()), 1)

    async def test_photo_with_long_description_uses_separate_text(self):
        async with self.sessions.begin() as session:
            entry = await session.get(Item, 1)
            entry.picture = b"fake image"
            entry.description = "x" * 4500
        await self.send(callback="item_1")
        photos = [call for call in self.telegram.calls if isinstance(call, SendPhoto)]
        self.assertEqual(len(photos), 1)
        self.assertIsNone(photos[0].caption)
        self.assertTrue(all(len(call.text) <= 4000 for call in self.messages()))
        self.assertIsNotNone(self.messages()[-1].reply_markup)

    async def test_missing_item_does_not_create_customer(self):
        order = await req.create_order(
            checkout_key="missing",
            item_id=999,
            tg_id=101,
            username=None,
            name="A",
            phone="8",
            email="a@b.co",
        )
        self.assertIsNone(order)
        self.assertIsNone(await req.get_user(101))

    async def test_empty_catalog(self):
        async with self.sessions.begin() as session:
            await session.execute(delete(Item))
            await session.execute(delete(Category))
            await session.execute(delete(MainCategory))
        await self.send("/shop")
        self.assertIn("пока пуст", self.messages()[-1].text)

    async def test_seed_is_idempotent(self):
        self.assertFalse(await seed_catalog(self.sessions))
        async with self.sessions() as session:
            self.assertEqual(await session.scalar(select(func.count()).select_from(Item)), 2)

    async def test_group_messages_do_not_start_checkout(self):
        await self.send("/shop", chat_type="group")
        await self.send(callback="buy_1", chat_type="group")
        self.assertEqual(self.telegram.calls, [])

    async def test_incomplete_checkout_is_reset(self):
        await self.state().set_state(handlers.Checkout.email)
        await self.send("buyer@example.com")
        self.assertIsNone(await self.state().get_state())
        self.assertEqual(await self.orders(), [])


if __name__ == "__main__":
    unittest.main()
