from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)


# =========================================================
# 1. ГЛАВНОЕ МЕНЮ
# =========================================================

main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="➕ Добавить расход"),
            KeyboardButton(text="📆 Период"),
        ],
        [
            KeyboardButton(text="📊 Статистика"),
            KeyboardButton(text="💼 Бюджет"),
        ],
        [
            KeyboardButton(text="🎯 Лимиты"),
            KeyboardButton(text="🔁 Регулярные"),
        ],
        [
            KeyboardButton(text="🗑 Удалить расход"),
            KeyboardButton(text="✏️ Редактировать расход"),
        ],
    ],
    resize_keyboard=True,
)


# =========================================================
# 2. КАТЕГОРИИ
# =========================================================

category_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="🍔 Еда"),
            KeyboardButton(text="🚕 Транспорт"),
        ],
        [
            KeyboardButton(text="🚬 Табак"),
            KeyboardButton(text="🎮 Развлечения"),
        ],
        [
            KeyboardButton(text="🛒 Покупки"),
            KeyboardButton(text="✍️ Другое"),
        ],
    ],
    resize_keyboard=True,
    one_time_keyboard=True,
)


# =========================================================
# 3. ОТМЕНА РАСХОДА
# =========================================================

def get_undo_keyboard(
    expense_id: int,
) -> InlineKeyboardMarkup:
    """
    Создаёт inline-кнопку для отмены
    конкретного добавленного расхода.
    """

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="↩️ Отменить",
                    callback_data=f"undo_expense:{expense_id}",
                )
            ]
        ]
    )


# =========================================================
# 4. ПЕРИОД
# =========================================================

def get_period_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора периода расходов."""

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Сегодня",
                    callback_data="period:today",
                )
            ],
            [
                InlineKeyboardButton(
                    text="Последние 7 дней",
                    callback_data="period:week",
                )
            ],
            [
                InlineKeyboardButton(
                    text="Этот месяц",
                    callback_data="period:month",
                )
            ],
        ]
    )


# =========================================================
# 5. БЮДЖЕТ
# =========================================================

def get_budget_keyboard() -> InlineKeyboardMarkup:
    """Главное меню месячного бюджета."""

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ Установить / изменить",
                    callback_data="budget:set",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📊 Посмотреть бюджет",
                    callback_data="budget:show",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗑 Удалить бюджет",
                    callback_data="budget:delete",
                )
            ],
        ]
    )


# =========================================================
# 6. ЛИМИТЫ
# =========================================================

def get_limits_keyboard() -> InlineKeyboardMarkup:
    """Главное меню лимитов по категориям."""

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ Установить / изменить",
                    callback_data="limit:set",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📊 Мои лимиты",
                    callback_data="limit:list",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗑 Удалить лимит",
                    callback_data="limit:delete_menu",
                )
            ],
        ]
    )


def get_delete_limits_keyboard(
    limits,
) -> InlineKeyboardMarkup:
    """Создаёт список лимитов для удаления."""

    buttons = []

    for limit_id, category, amount in limits:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{category} — {amount:.2f} ₽",
                    callback_data=f"limit_delete:{limit_id}",
                )
            ]
        )

    return InlineKeyboardMarkup(
        inline_keyboard=buttons
    )


# =========================================================
# 7. РЕГУЛЯРНЫЕ РАСХОДЫ
# =========================================================

def get_recurring_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню регулярных расходов."""

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ Добавить",
                    callback_data="recurring:add",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📋 Мои регулярные",
                    callback_data="recurring:list",
                )
            ],
            [
                InlineKeyboardButton(
                    text="✅ Отметить оплаченным",
                    callback_data="recurring:pay_menu",
                )
            ],
            [
                InlineKeyboardButton(
                    text="✏️ Редактировать",
                    callback_data="recurring:edit_menu",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗑 Удалить",
                    callback_data="recurring:delete_menu",
                )
            ],
        ]
    )


def get_recurring_pay_keyboard(
    expenses,
) -> InlineKeyboardMarkup:
    """Создаёт список регулярных расходов для оплаты."""

    buttons = []

    for (
        recurring_id,
        name,
        amount,
        category,
        day,
    ) in expenses:

        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"✅ {name} — {amount:.2f} ₽",
                    callback_data=f"recurring_pay:{recurring_id}",
                )
            ]
        )

    return InlineKeyboardMarkup(
        inline_keyboard=buttons
    )


def get_recurring_edit_keyboard(
    expenses,
) -> InlineKeyboardMarkup:
    """Создаёт список регулярных расходов для редактирования."""

    buttons = []

    for (
        recurring_id,
        name,
        amount,
        category,
        day,
    ) in expenses:

        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"✏️ {name} — {amount:.2f} ₽",
                    callback_data=f"recurring_edit:{recurring_id}",
                )
            ]
        )

    return InlineKeyboardMarkup(
        inline_keyboard=buttons
    )


def get_recurring_edit_fields_keyboard(
    recurring_id: int,
) -> InlineKeyboardMarkup:
    """Выбор поля регулярного расхода для изменения."""

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📝 Название",
                    callback_data=f"rec_edit_name:{recurring_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="💰 Сумму",
                    callback_data=f"rec_edit_amount:{recurring_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏷 Категорию",
                    callback_data=f"rec_edit_category:{recurring_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📅 День оплаты",
                    callback_data=f"rec_edit_day:{recurring_id}",
                )
            ],
        ]
    )


def get_recurring_delete_keyboard(
    expenses,
) -> InlineKeyboardMarkup:
    """Создаёт список регулярных расходов для удаления."""

    buttons = []

    for (
        recurring_id,
        name,
        amount,
        category,
        day,
    ) in expenses:

        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"🗑 {name} — {amount:.2f} ₽",
                    callback_data=f"recurring_delete:{recurring_id}",
                )
            ]
        )

    return InlineKeyboardMarkup(
        inline_keyboard=buttons
    )


# =========================================================
# 8. ОБЫЧНЫЕ РАСХОДЫ
# =========================================================

def get_delete_expenses_keyboard(
    expenses,
) -> InlineKeyboardMarkup:
    """Создаёт список обычных расходов для удаления."""

    buttons = []

    for (
        expense_id,
        amount,
        category,
        created_at,
    ) in expenses:

        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{category} — {amount:.2f} ₽",
                    callback_data=f"delete:{expense_id}",
                )
            ]
        )

    return InlineKeyboardMarkup(
        inline_keyboard=buttons
    )


def get_edit_expenses_keyboard(
    expenses,
) -> InlineKeyboardMarkup:
    """Создаёт список обычных расходов для редактирования."""

    buttons = []

    for (
        expense_id,
        amount,
        category,
        created_at,
    ) in expenses:

        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{category} — {amount:.2f} ₽",
                    callback_data=f"edit:{expense_id}",
                )
            ]
        )

    return InlineKeyboardMarkup(
        inline_keyboard=buttons
    )


def get_edit_expense_fields_keyboard(
    expense_id: int,
) -> InlineKeyboardMarkup:
    """Выбор поля обычного расхода для изменения."""

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💰 Изменить сумму",
                    callback_data=f"edit_amount:{expense_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏷 Изменить категорию",
                    callback_data=f"edit_category:{expense_id}",
                )
            ],
        ]
    )