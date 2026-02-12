"""Category selection handlers: /tags command and inline keyboard (apply/reset/toggle)."""

from types import SimpleNamespace

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    CallbackQuery,
)

from database.db import get_db
from database.models import Category
from .repository import CategoryRepository, UserRepository

router = Router()


def categories_keyboard(
    categories: list[Category] | list[SimpleNamespace],
    selected_ids: set[int],
) -> InlineKeyboardMarkup:
    """
    Build an inline keyboard: one button per category (with checkmark if selected),
    plus Apply and Reset buttons.

    Args:
        categories: List of objects with .id and .name (Category or SimpleNamespace).
        selected_ids: Set of category ids currently selected.

    Returns:
        InlineKeyboardMarkup for the category selection dialog.
    """
    keyboard: list[list[InlineKeyboardButton]] = []

    for category in categories:
        icon = "✅" if category.id in selected_ids else "⬜"
        keyboard.append([
            InlineKeyboardButton(
                text=f"{icon} {category.name}",
                callback_data=f"category_toggle:{category.id}",
            )
        ])

    keyboard.append([
        InlineKeyboardButton(text="Apply", callback_data="categories_apply"),
        InlineKeyboardButton(text="Reset", callback_data="categories_reset"),
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


@router.message(F.text == "/tags")
async def cmd_tags(message: Message, state: FSMContext) -> None:
    """
    Handle /tags: show category selection keyboard with current user subscriptions.
    Loads enabled categories and user's selected ids, stores them in FSM state.
    """
    async with get_db() as db:
        users_repo = UserRepository(db)
        categories_repo = CategoryRepository(db)

        user = await users_repo.get_by_chat_id(message.chat.id)
        categories = await categories_repo.get_enabled_categories()

        selected_ids = {c.id for c in user.categories} if user else set()

        await state.update_data(
            all_categories=[{"id": c.id, "name": c.name} for c in categories],
            selected=list(selected_ids),
        )

    await message.answer(
        "Select topics of interest:",
        reply_markup=categories_keyboard(categories, selected_ids),
    )


@router.callback_query(F.data.startswith("category_toggle:"))
async def toggle_category(cb: CallbackQuery, state: FSMContext) -> None:
    """Toggle one category in FSM state and refresh the inline keyboard."""
    category_id = int(cb.data.split(":")[1])

    data = await state.get_data()
    selected = set(data.get("selected", []))
    all_categories = data.get("all_categories", [])

    if category_id in selected:
        selected.remove(category_id)
    else:
        selected.add(category_id)

    await state.update_data(selected=list(selected))

    categories = [
        SimpleNamespace(id=c["id"], name=c["name"])
        for c in all_categories
    ]

    await cb.message.edit_reply_markup(
        reply_markup=categories_keyboard(categories, selected)
    )
    await cb.answer()


@router.callback_query(F.data == "categories_apply")
async def apply_categories(cb: CallbackQuery, state: FSMContext) -> None:
    """
    Handle Apply: persist selected category ids for the user and clear FSM state.
    """
    data = await state.get_data()
    selected_ids = set(data.get("selected", []))

    async with get_db() as db:
        users_repo = UserRepository(db)
        categories_repo = CategoryRepository(db)

        user = await users_repo.get_by_chat_id(cb.from_user.id)
        if not user:
            await cb.answer("User not found", show_alert=True)
            return

        categories = await categories_repo.get_categories_by_ids(selected_ids)
        await users_repo.update_user_categories(user, categories)

    await state.clear()
    await cb.message.edit_text("Settings saved ✅")


@router.callback_query(F.data == "categories_reset")
async def reset_categories(cb: CallbackQuery, state: FSMContext) -> None:
    """
    Handle Reset: toggle between all selected and none; update keyboard and state.
    """
    data = await state.get_data()
    all_categories = data.get("all_categories", [])
    current_selected = set(data.get("selected", []))

    all_ids = {c["id"] for c in all_categories}

    if current_selected == all_ids:
        new_selected = set()
        text = "All topics deselected"
    else:
        new_selected = all_ids
        text = "All topics selected"

    await state.update_data(selected=list(new_selected))

    categories = [
        SimpleNamespace(id=c["id"], name=c["name"])
        for c in all_categories
    ]

    await cb.message.edit_reply_markup(
        reply_markup=categories_keyboard(categories, new_selected)
    )
    await cb.answer(text)
