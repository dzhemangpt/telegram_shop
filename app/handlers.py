"""Catalog navigation and a three-step checkout in private chats."""

import logging
from uuid import uuid4

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from sqlalchemy.exc import SQLAlchemyError

import app.database.requests as req
import app.keyboards as kb
from app.validation import normalize_phone, valid_email, valid_name

logger = logging.getLogger(__name__)
router = Router()
router.message.filter(F.chat.type == "private")
router.callback_query.filter(F.message.chat.type == "private")


class Checkout(StatesGroup):
    name = State()
    phone = State()
    email = State()


# Commands precede state handlers so the customer can always leave checkout.
@router.message(CommandStart())
async def start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "😊 Вас приветствует спортивный магазин GYM RATS!\n"
        "Откройте каталог, чтобы выбрать товар. Подсказки: /help.",
        reply_markup=kb.main,
    )


@router.message(Command("cancel"))
async def cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "Оформление отменено. Вы можете вернуться в каталог.", reply_markup=kb.main
    )


@router.message(Command("help"))
async def help_command(message: Message) -> None:
    await message.answer(
        "/shop — открыть каталог\n/start — главное меню\n"
        "/cancel — отменить оформление\n/help — помощь\n\n"
        "Выберите раздел, категорию и товар, затем нажмите «Купить». "
        "Укажите имя, телефон и email. Заказ передаётся менеджеру; "
        "оплата в боте не производится. Во время оформления /help сохраняет ваш текущий шаг."
    )


async def show_catalog(message: Message) -> None:
    entries = await req.get_maincategories()
    await message.answer(
        "🛍 Выберите раздел каталога" if entries else "Каталог пока пуст. Загляните позже!",
        reply_markup=kb.main_categories(entries) if entries else kb.main,
    )


@router.message(Command("shop"))
@router.message(F.text == kb.CATALOG_BUTTON)
async def catalog(message: Message, state: FSMContext) -> None:
    await state.clear()
    await show_catalog(message)


@router.message(F.text.startswith("/"))
async def unknown_command(message: Message) -> None:
    await message.answer("Неизвестная команда. Список команд: /help. Отмена заказа: /cancel.")


def callback_id(callback: CallbackQuery) -> int:
    return int(callback.data.split("_", 1)[1])


@router.callback_query(F.data.regexp(r"^main_[1-9][0-9]{0,17}$"))
async def select_main_category(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not isinstance(callback.message, Message):
        return
    await state.clear()
    entries = await req.get_categories(callback_id(callback))
    await callback.message.answer(
        "🛒 Выберите категорию / бренд" if entries else "В этом разделе пока нет категорий.",
        reply_markup=kb.categories(entries),
    )


@router.callback_query(F.data.regexp(r"^category_[1-9][0-9]{0,17}$"))
async def select_category(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not isinstance(callback.message, Message):
        return
    await state.clear()
    category = await req.get_category(callback_id(callback))
    if category is None:
        await callback.message.answer("Категория не найдена. Откройте /shop.")
        return
    entries = await req.get_items(category.id)
    await callback.message.answer(
        "🛒 Выберите товар" if entries else "В этой категории пока нет товаров.",
        reply_markup=kb.items(entries, category.main_category),
    )


@router.callback_query(F.data.regexp(r"^item_[1-9][0-9]{0,17}$"))
async def show_item(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not isinstance(callback.message, Message):
        return
    await state.clear()
    entry = await req.get_item(callback_id(callback))
    if entry is None:
        await callback.message.answer("Товар больше недоступен. Откройте /shop.")
        return
    text = f"{entry.name}\n\n{entry.description}\n\nЦена: {entry.price} ₽"
    markup = kb.item(entry)
    if entry.picture:
        photo = BufferedInputFile(entry.picture, filename="product.jpg")
        # Old SQLite catalogs may contain descriptions beyond the declared String limit.
        if len(text) <= 1024:
            await callback.message.answer_photo(photo, caption=text, reply_markup=markup)
            return
        await callback.message.answer_photo(photo)
    for offset in range(0, len(text), 4000):
        await callback.message.answer(
            text[offset : offset + 4000],
            reply_markup=markup if offset + 4000 >= len(text) else None,
        )


@router.callback_query(F.data == "go_start")
async def go_start(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if isinstance(callback.message, Message):
        await state.clear()
        await show_catalog(callback.message)


@router.callback_query(F.data.regexp(r"^buy_[1-9][0-9]{0,17}$"))
async def begin_checkout(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not isinstance(callback.message, Message):
        return
    entry = await req.get_item(callback_id(callback))
    if entry is None:
        await callback.message.answer("Товар больше недоступен. Откройте /shop.")
        return
    await state.clear()
    await state.update_data(item_id=entry.id, checkout_key=uuid4().hex)
    await state.set_state(Checkout.name)
    user = await req.get_user(callback.from_user.id)
    await callback.message.answer(
        "😊 Как к вам обращаться? Введите имя (до 25 символов).\nОтмена: /cancel.",
        reply_markup=kb.helper(user, "name"),
    )


@router.message(Checkout.name)
async def get_name(message: Message, state: FSMContext) -> None:
    if not valid_name(message.text):
        await message.answer("Введите имя текстом: от 1 до 25 символов.")
        return
    await state.update_data(name=message.text.strip())
    await state.set_state(Checkout.phone)
    user = await req.get_user(message.from_user.id)
    await message.answer(
        "📱 Введите телефон: +79991234567 или 89991234567.",
        reply_markup=kb.helper(user, "phone"),
    )


@router.message(Checkout.phone)
async def get_phone(message: Message, state: FSMContext) -> None:
    phone = normalize_phone(message.text)
    if phone is None:
        await message.answer("Неверный телефон. Введите +79991234567 или 89991234567.")
        return
    await state.update_data(phone=phone)
    await state.set_state(Checkout.email)
    user = await req.get_user(message.from_user.id)
    await message.answer(
        "✉️ Введите email (до 50 символов), например buyer@example.com.",
        reply_markup=kb.helper(user, "email"),
    )


@router.message(Checkout.email)
async def finish_checkout(
    message: Message,
    state: FSMContext,
    bot: Bot,
    admin_chat_id: int,
) -> None:
    if not valid_email(message.text):
        await message.answer("Неверный email. Пример: buyer@example.com (до 50 символов).")
        return
    data = await state.get_data()
    if not {"item_id", "checkout_key", "name", "phone"} <= data.keys():
        await state.clear()
        await message.answer(
            "Оформление устарело. Выберите товар заново: /shop.", reply_markup=kb.main
        )
        return
    try:
        order = await req.create_order(
            checkout_key=data["checkout_key"],
            item_id=data["item_id"],
            tg_id=message.from_user.id,
            username=message.from_user.username,
            name=data["name"],
            phone=data["phone"],
            email=message.text.strip(),
        )
    except SQLAlchemyError:
        logger.error("Could not save order")
        await message.answer("Не удалось сохранить заказ. Попробуйте отправить email ещё раз.")
        return
    if order is None:
        await state.clear()
        await message.answer("Товар больше недоступен. Откройте /shop.", reply_markup=kb.main)
        return

    # Persist before any network calls. Failed notifications remain discoverable in the DB.
    notified = order.notified
    if not notified:
        admin_text = (
            f"✉️ Заказ №{order.id}\nTelegram ID: {order.tg_id}\n"
            f"Username: {('@' + order.username) if order.username else 'не указан'}\n"
            f"Имя: {order.name}\nТелефон: {order.phone}\nEmail: {order.email}\n"
            f"Товар: {order.item_name}\nЦена: {order.price} ₽"
        )
        try:
            await bot.send_message(chat_id=admin_chat_id, text=admin_text)
            await req.mark_order_notified(order.id)
            notified = True
        except (TelegramAPIError, SQLAlchemyError) as exc:
            logger.error("Order %s notification failed (%s)", order.id, type(exc).__name__)
    await state.clear()
    status = (
        "Менеджер свяжется с вами для уточнения покупки."
        if notified
        else "Уведомление менеджеру временно не доставлено. Заявка сохранена; "
        "пожалуйста, не оформляйте её повторно."
    )
    await message.answer(
        f"✅ Заказ №{order.id} сохранён\nТовар: {order.item_name}\n"
        f"Цена: {order.price} ₽\n\n{status}",
        reply_markup=kb.main,
    )


@router.callback_query()
async def outdated_button(callback: CallbackQuery) -> None:
    await callback.answer("Эта кнопка устарела. Откройте /shop.", show_alert=True)
