# bot/ui.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.schema import TABLES, SUBMENUS

def main_menu():
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    # Таблицы по 2 кнопки в ряду
    row = []
    for name in TABLES:
        row.append(InlineKeyboardButton(text=name, callback_data=f"table:{name}"))
        if len(row) == 2:
            kb.inline_keyboard.append(row)
            row = []
    if row:
        kb.inline_keyboard.append(row)
    # Подменю
    kb.inline_keyboard.append([
        InlineKeyboardButton(text="Задачи ▾", callback_data="submenu:Задачи"),
        InlineKeyboardButton(text="Объекты ▾", callback_data="submenu:Объекты"),
    ])
    kb.inline_keyboard.append([
        InlineKeyboardButton(text="Отчетность ▾", callback_data="submenu:Отчетность"),
    ])
    return kb

def submenu(name: str):
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for item in SUBMENUS.get(name, []):
        kb.inline_keyboard.append([InlineKeyboardButton(text=item, callback_data=f"action:{name}:{item}")])
    kb.inline_keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back:main")])
    return kb
