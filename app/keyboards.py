"""Keyboard builders receive catalog data; navigation carries its own IDs."""

from aiogram.types import (
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.database.models import Category, Item, MainCategory, User

CATALOG_BUTTON = "🛍Каталог"
main = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text=CATALOG_BUTTON)]],
    resize_keyboard=True,
    input_field_placeholder="Выберите каталог или введите /help",
)


def main_categories(categories: list[MainCategory]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for category in categories:
        builder.button(text=category.name, callback_data=f"main_{category.id}")
    return builder.adjust(1).as_markup()


def categories(entries: list[Category]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for category in entries:
        builder.button(text=category.name, callback_data=f"category_{category.id}")
    builder.button(text="🔼На главную", callback_data="go_start")
    return builder.adjust(1).as_markup()


def items(entries: list[Item], main_category_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for entry in entries:
        builder.button(text=f"{entry.name} — {entry.price} ₽", callback_data=f"item_{entry.id}")
    builder.button(text="◀️Назад", callback_data=f"main_{main_category_id}")
    builder.button(text="🔼На главную", callback_data="go_start")
    return builder.adjust(1).as_markup()


def item(entry: Item) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🛒Купить", callback_data=f"buy_{entry.id}")
    builder.button(text="◀️Назад", callback_data=f"category_{entry.category}")
    builder.button(text="🔼На главную", callback_data="go_start")
    return builder.adjust(1).as_markup()


def helper(user: User | None, field: str) -> ReplyKeyboardMarkup | ReplyKeyboardRemove:
    value = getattr(user, field, None) if user else None
    if not value:
        return ReplyKeyboardRemove()
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=value)]],
        one_time_keyboard=True,
        resize_keyboard=True,
    )
