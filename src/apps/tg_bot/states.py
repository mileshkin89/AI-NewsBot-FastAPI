"""FSM states for the Telegram bot (e.g. category selection flow)."""

from aiogram.fsm.state import StatesGroup, State


class CategorySelection(StatesGroup):
    """State group for the category selection dialog."""

    selected = State()