import asyncio
import os
import aiohttp

from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from dotenv import load_dotenv

from database import (
    init_db,
    add_expense,
    get_recent_expenses,
    delete_expense,
    update_expense_amount,
    update_expense_category,
    get_expenses_by_period,
    set_category_limit,
    get_category_limits,
    get_category_limit,
    delete_category_limit,
)

from categories import normalize_category


# =========================================================
# НАСТРОЙКИ
# =========================================================

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")

dp = Dispatcher()


# =========================================================
# FSM СОСТОЯНИЯ
# =========================================================

class AddExpense(StatesGroup):
    waiting_for_amount = State()
    waiting_for_category = State()

    waiting_for_edit_amount = State()
    waiting_for_edit_category = State()

    waiting_for_limit_category = State()
    waiting_for_limit_amount = State()


# =========================================================
# ГЛАВНОЕ МЕНЮ
# =========================================================

main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="➕ Добавить расход"),
            KeyboardButton(text="📆 Период"),
        ],
        [
            KeyboardButton(text="🎯 Лимиты"),
        ],
        [
            KeyboardButton(text="🗑 Удалить расход"),
            KeyboardButton(text="✏️ Редактировать расход"),
        ],
    ],
    resize_keyboard=True,
)


# =========================================================
# КАТЕГОРИИ
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
# TELEGRAM SESSION
# =========================================================

class TrustedEnvSession(AiohttpSession):
    async def create_session(self):
        if self._should_reset_connector:
            await self.close()

        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                connector=self._connector_type(
                    **self._connector_init
                ),
                trust_env=True,
            )

            self._should_reset_connector = False

        return self._session


# =========================================================
# /START
# =========================================================

@dp.message(CommandStart())
async def start_handler(message: Message):
    await message.answer(
        "Привет 👋\n\n"
        "Я KashBot — бот для учёта расходов.\n\n"
        "Выбирай действие ниже 👇",
        reply_markup=main_keyboard,
    )


# =========================================================
# ДОБАВЛЕНИЕ РАСХОДА
# =========================================================

@dp.message(Command("add"))
async def add_handler(
    message: Message,
    state: FSMContext,
):
    await state.set_state(
        AddExpense.waiting_for_amount
    )

    await message.answer(
        "💰 Сколько потратил?\n\n"
        "Например: 500",
        reply_markup=ReplyKeyboardRemove(),
    )


@dp.message(
    lambda message:
    message.text == "➕ Добавить расход"
)
async def add_button_handler(
    message: Message,
    state: FSMContext,
):
    await state.set_state(
        AddExpense.waiting_for_amount
    )

    await message.answer(
        "💰 Сколько потратил?\n\n"
        "Например: 500",
        reply_markup=ReplyKeyboardRemove(),
    )


# =========================================================
# ПОЛУЧАЕМ СУММУ
# =========================================================

@dp.message(AddExpense.waiting_for_amount)
async def process_amount(
    message: Message,
    state: FSMContext,
):
    amount_text = message.text

    if not amount_text:
        await message.answer(
            "❌ Отправь сумму текстом.\n"
            "Например: 500"
        )
        return

    try:
        amount = float(
            amount_text.replace(",", ".")
        )

    except ValueError:
        await message.answer(
            "❌ Некорректная сумма.\n"
            "Например: 500"
        )
        return

    if amount <= 0:
        await message.answer(
            "❌ Сумма должна быть больше нуля."
        )
        return

    await state.update_data(
        amount=amount
    )

    await state.set_state(
        AddExpense.waiting_for_category
    )

    await message.answer(
        "🏷️ Выбери категорию или напиши свою:",
        reply_markup=category_keyboard,
    )


# =========================================================
# ПОЛУЧАЕМ КАТЕГОРИЮ
# =========================================================

@dp.message(AddExpense.waiting_for_category)
async def process_category(
    message: Message,
    state: FSMContext,
):
    category = message.text

    if not category:
        await message.answer(
            "❌ Отправь категорию."
        )
        return

    category = category.strip()

    button_categories = {
        "🍔 Еда": "Еда",
        "🚕 Транспорт": "Транспорт",
        "🚬 Табак": "Табак",
        "🎮 Развлечения": "Развлечения",
        "🛒 Покупки": "Покупки",
        "✍️ Другое": "Другое",
    }

    if category in button_categories:
        category = button_categories[category]

    else:
        category = normalize_category(
            category
        )

    data = await state.get_data()

    amount = data["amount"]
    user_id = message.from_user.id

    add_expense(
        user_id=user_id,
        amount=amount,
        category=category,
    )

    await state.clear()

    text = (
        "✅ Расход добавлен!\n\n"
        f"💰 Сумма: {amount:.2f} ₽\n"
        f"🏷️ Категория: {category}"
    )

    # =====================================================
    # ПРОВЕРКА ЛИМИТА ПОСЛЕ ДОБАВЛЕНИЯ
    # =====================================================

    limit = get_category_limit(
        user_id=user_id,
        category=category,
    )

    if limit is not None:
        today = datetime.now().date()

        start_date = today.replace(
            day=1
        )

        expenses = get_expenses_by_period(
            user_id=user_id,
            start_date=start_date.isoformat(),
            end_date=today.isoformat(),
        )

        spent = sum(
            expense_amount
            for (
                expense_amount,
                expense_category,
                created_at,
            ) in expenses
            if expense_category == category
        )

        remaining = limit - spent

        percent = (
            spent / limit * 100
            if limit > 0
            else 0
        )

        if percent < 60:
            indicator = "🟢"

        elif percent < 80:
            indicator = "🟡"

        elif percent <= 100:
            indicator = "🟠"

        else:
            indicator = "🔴"

        text += (
            "\n\n"
            f"{indicator} Лимит категории:\n"
            f"{spent:.2f} / {limit:.2f} ₽\n"
        )

        if remaining >= 0:
            text += (
                f"Осталось: {remaining:.2f} ₽\n"
                f"Использовано: {percent:.0f}%"
            )

            if percent >= 80:
                text += (
                    "\n⚠️ Ты близко к лимиту."
                )

        else:
            text += (
                "⚠️ Лимит превышен!\n"
                f"Превышение: "
                f"{abs(remaining):.2f} ₽\n"
                f"Использовано: {percent:.0f}%"
            )

    await message.answer(
        text,
        reply_markup=main_keyboard,
    )


# =========================================================
# ПЕРИОД
# =========================================================

@dp.message(
    lambda message:
    message.text == "📆 Период"
)
async def period_menu(message: Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Сегодня",
                    callback_data="period:today",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="Последние 7 дней",
                    callback_data="period:week",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="Этот месяц",
                    callback_data="period:month",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="Свой период",
                    callback_data="period:custom",
                ),
            ],
        ]
    )

    await message.answer(
        "📆 Выбери период:",
        reply_markup=keyboard,
    )


# =========================================================
# ВЫВОД ПЕРИОДА
# =========================================================

async def show_period_expenses(
    message: Message,
    user_id: int,
    start_date: str,
    end_date: str,
    title: str,
):
    expenses = get_expenses_by_period(
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
    )

    if not expenses:
        await message.answer(
            f"{title}\n\n"
            "Расходов за этот период нет.",
            reply_markup=main_keyboard,
        )
        return

    total = sum(
        expense[0]
        for expense in expenses
    )

    categories_total = {}

    for amount, category, created_at in expenses:
        if category in categories_total:
            categories_total[category] += amount

        else:
            categories_total[category] = amount

    text = f"{title}\n\n"

    for category, amount in categories_total.items():
        text += (
            f"{category}: "
            f"{amount:.2f} ₽\n"
        )

    text += (
        f"\n💰 Итого: {total:.2f} ₽"
    )

    await message.answer(
        text,
        reply_markup=main_keyboard,
    )


# =========================================================
# ОБРАБОТКА ПЕРИОДА
# =========================================================

@dp.callback_query(
    lambda callback:
    callback.data
    and callback.data.startswith("period:")
)
async def period_callback(
    callback: CallbackQuery,
):
    period = callback.data.split(":")[1]

    today = datetime.now().date()

    if period == "today":
        start_date = today
        end_date = today
        title = "📊 Расходы за сегодня"

    elif period == "week":
        start_date = (
            today - timedelta(days=6)
        )

        end_date = today

        title = (
            "📆 Расходы за последние 7 дней"
        )

    elif period == "month":
        start_date = today.replace(
            day=1
        )

        end_date = today

        title = (
            "📅 Расходы за текущий месяц"
        )

    elif period == "custom":
        await callback.answer()

        await callback.message.answer(
            "📆 Свой период добавим "
            "следующим шагом."
        )

        return

    else:
        await callback.answer(
            "Неизвестный период."
        )

        return

    await callback.answer()

    await show_period_expenses(
        message=callback.message,
        user_id=callback.from_user.id,
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
        title=title,
    )


# =========================================================
# 🎯 МЕНЮ ЛИМИТОВ
# =========================================================

@dp.message(
    lambda message:
    message.text == "🎯 Лимиты"
)
async def limits_menu(message: Message):
    keyboard = InlineKeyboardMarkup(
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

    await message.answer(
        "🎯 Лимиты по категориям\n\n"
        "Здесь можно установить месячный "
        "лимит расходов для каждой категории.",
        reply_markup=keyboard,
    )


# =========================================================
# УСТАНОВКА ЛИМИТА — КАТЕГОРИЯ
# =========================================================

@dp.callback_query(
    lambda callback:
    callback.data == "limit:set"
)
async def limit_set_callback(
    callback: CallbackQuery,
    state: FSMContext,
):
    await state.set_state(
        AddExpense.waiting_for_limit_category
    )

    await callback.answer()

    await callback.message.answer(
        "🏷 Выбери категорию "
        "или напиши свою:",
        reply_markup=category_keyboard,
    )


@dp.message(
    AddExpense.waiting_for_limit_category
)
async def process_limit_category(
    message: Message,
    state: FSMContext,
):
    category = message.text

    if not category:
        await message.answer(
            "❌ Отправь категорию."
        )
        return

    category = category.strip()

    button_categories = {
        "🍔 Еда": "Еда",
        "🚕 Транспорт": "Транспорт",
        "🚬 Табак": "Табак",
        "🎮 Развлечения": "Развлечения",
        "🛒 Покупки": "Покупки",
        "✍️ Другое": "Другое",
    }

    if category in button_categories:
        category = button_categories[category]

    else:
        category = normalize_category(
            category
        )

    await state.update_data(
        limit_category=category
    )

    await state.set_state(
        AddExpense.waiting_for_limit_amount
    )

    await message.answer(
        f"🎯 Категория: {category}\n\n"
        "Какой месячный лимит установить?\n\n"
        "Например: 15000",
        reply_markup=ReplyKeyboardRemove(),
    )


# =========================================================
# УСТАНОВКА ЛИМИТА — СУММА
# =========================================================

@dp.message(
    AddExpense.waiting_for_limit_amount
)
async def process_limit_amount(
    message: Message,
    state: FSMContext,
):
    amount_text = message.text

    if not amount_text:
        await message.answer(
            "❌ Отправь сумму текстом."
        )
        return

    try:
        amount = float(
            amount_text.replace(",", ".")
        )

    except ValueError:
        await message.answer(
            "❌ Некорректная сумма.\n"
            "Например: 15000"
        )
        return

    if amount <= 0:
        await message.answer(
            "❌ Лимит должен быть больше нуля."
        )
        return

    data = await state.get_data()

    category = data[
        "limit_category"
    ]

    set_category_limit(
        user_id=message.from_user.id,
        category=category,
        amount=amount,
    )

    await state.clear()

    await message.answer(
        "✅ Лимит установлен!\n\n"
        f"🏷 Категория: {category}\n"
        f"🎯 Лимит: {amount:.2f} ₽ / месяц",
        reply_markup=main_keyboard,
    )


# =========================================================
# МОИ ЛИМИТЫ
# =========================================================

@dp.callback_query(
    lambda callback:
    callback.data == "limit:list"
)
async def show_limits_callback(
    callback: CallbackQuery,
):
    user_id = callback.from_user.id

    limits = get_category_limits(
        user_id
    )

    await callback.answer()

    if not limits:
        await callback.message.answer(
            "🎯 Лимиты пока не установлены.",
            reply_markup=main_keyboard,
        )
        return

    today = datetime.now().date()

    start_date = today.replace(
        day=1
    )

    expenses = get_expenses_by_period(
        user_id=user_id,
        start_date=start_date.isoformat(),
        end_date=today.isoformat(),
    )

    text = "🎯 Лимиты на текущий месяц\n\n"

    for (
        limit_id,
        category,
        limit_amount,
    ) in limits:

        spent = sum(
            amount
            for (
                amount,
                expense_category,
                created_at,
            ) in expenses
            if expense_category == category
        )

        remaining = (
            limit_amount - spent
        )

        percent = (
            spent / limit_amount * 100
            if limit_amount > 0
            else 0
        )

        # =================================================
        # ИНДИКАТОР ЛИМИТА
        # =================================================

        if percent < 60:
            indicator = "🟢"

        elif percent < 80:
            indicator = "🟡"

        elif percent <= 100:
            indicator = "🟠"

        else:
            indicator = "🔴"

        # =================================================
        # СТАТУС
        # =================================================

        if remaining >= 0:
            status = (
                f"Осталось: {remaining:.2f} ₽"
            )

        else:
            status = (
                "⚠️ Превышение: "
                f"{abs(remaining):.2f} ₽"
            )

        # =================================================
        # ВЫВОД
        # =================================================

        text += (
            f"{indicator} {category}\n"
            f"{spent:.2f} / "
            f"{limit_amount:.2f} ₽\n"
            f"{status}\n"
            f"Использовано: "
            f"{percent:.0f}%\n\n"
        )

    await callback.message.answer(
        text,
        reply_markup=main_keyboard,
    )


# =========================================================
# МЕНЮ УДАЛЕНИЯ ЛИМИТА
# =========================================================

@dp.callback_query(
    lambda callback:
    callback.data == "limit:delete_menu"
)
async def delete_limit_menu(
    callback: CallbackQuery,
):
    limits = get_category_limits(
        callback.from_user.id
    )

    await callback.answer()

    if not limits:
        await callback.message.answer(
            "Удалять пока нечего."
        )
        return

    buttons = []

    for (
        limit_id,
        category,
        amount,
    ) in limits:

        buttons.append(
            [
                InlineKeyboardButton(
                    text=(
                        f"{category} — "
                        f"{amount:.2f} ₽"
                    ),
                    callback_data=(
                        f"limit_delete:{limit_id}"
                    ),
                )
            ]
        )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=buttons
    )

    await callback.message.answer(
        "🗑 Выбери лимит для удаления:",
        reply_markup=keyboard,
    )


# =========================================================
# УДАЛЕНИЕ ЛИМИТА
# =========================================================

@dp.callback_query(
    lambda callback:
    callback.data
    and callback.data.startswith(
        "limit_delete:"
    )
)
async def delete_limit_callback(
    callback: CallbackQuery,
):
    limit_id = int(
        callback.data.split(":")[1]
    )

    delete_category_limit(
        user_id=callback.from_user.id,
        limit_id=limit_id,
    )

    await callback.answer(
        "Лимит удалён ✅"
    )

    await callback.message.edit_text(
        "✅ Лимит удалён."
    )


# =========================================================
# УДАЛЕНИЕ РАСХОДА
# =========================================================

@dp.message(
    lambda message:
    message.text == "🗑 Удалить расход"
)
async def delete_expense_menu(
    message: Message,
):
    expenses = get_recent_expenses(
        user_id=message.from_user.id,
        limit=10,
    )

    if not expenses:
        await message.answer(
            "Удалять пока нечего.",
            reply_markup=main_keyboard,
        )
        return

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
                    text=(
                        f"{category} — "
                        f"{amount:.2f} ₽"
                    ),
                    callback_data=(
                        f"delete:{expense_id}"
                    ),
                )
            ]
        )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=buttons
    )

    await message.answer(
        "🗑 Выбери расход, который "
        "хочешь удалить:",
        reply_markup=keyboard,
    )


@dp.callback_query(
    lambda callback:
    callback.data
    and callback.data.startswith(
        "delete:"
    )
)
async def delete_expense_callback(
    callback: CallbackQuery,
):
    expense_id = int(
        callback.data.split(":")[1]
    )

    delete_expense(
        expense_id=expense_id,
        user_id=callback.from_user.id,
    )

    await callback.answer(
        "Расход удалён ✅"
    )

    await callback.message.edit_text(
        "✅ Расход удалён."
    )


# =========================================================
# РЕДАКТИРОВАНИЕ РАСХОДА
# =========================================================

@dp.message(
    lambda message:
    message.text == "✏️ Редактировать расход"
)
async def edit_expense_menu(
    message: Message,
):
    expenses = get_recent_expenses(
        user_id=message.from_user.id,
        limit=10,
    )

    if not expenses:
        await message.answer(
            "Редактировать пока нечего.",
            reply_markup=main_keyboard,
        )
        return

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
                    text=(
                        f"{category} — "
                        f"{amount:.2f} ₽"
                    ),
                    callback_data=(
                        f"edit:{expense_id}"
                    ),
                )
            ]
        )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=buttons
    )

    await message.answer(
        "✏️ Выбери расход, который "
        "хочешь изменить:",
        reply_markup=keyboard,
    )


# =========================================================
# ЧТО РЕДАКТИРОВАТЬ
# =========================================================

@dp.callback_query(
    lambda callback:
    callback.data
    and callback.data.startswith(
        "edit:"
    )
)
async def edit_expense_callback(
    callback: CallbackQuery,
):
    expense_id = int(
        callback.data.split(":")[1]
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💰 Изменить сумму",
                    callback_data=(
                        f"edit_amount:{expense_id}"
                    ),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🏷 Изменить категорию",
                    callback_data=(
                        f"edit_category:{expense_id}"
                    ),
                ),
            ],
        ]
    )

    await callback.message.edit_text(
        "Что хочешь изменить?",
        reply_markup=keyboard,
    )

    await callback.answer()


# =========================================================
# РЕДАКТИРОВАНИЕ СУММЫ
# =========================================================

@dp.callback_query(
    lambda callback:
    callback.data
    and callback.data.startswith(
        "edit_amount:"
    )
)
async def edit_amount_callback(
    callback: CallbackQuery,
    state: FSMContext,
):
    expense_id = int(
        callback.data.split(":")[1]
    )

    await state.update_data(
        edit_expense_id=expense_id
    )

    await state.set_state(
        AddExpense.waiting_for_edit_amount
    )

    await callback.message.edit_text(
        "💰 Введи новую сумму:"
    )

    await callback.answer()


@dp.message(
    AddExpense.waiting_for_edit_amount
)
async def process_edit_amount(
    message: Message,
    state: FSMContext,
):
    amount_text = message.text

    if not amount_text:
        await message.answer(
            "❌ Отправь сумму текстом."
        )
        return

    try:
        new_amount = float(
            amount_text.replace(",", ".")
        )

    except ValueError:
        await message.answer(
            "❌ Некорректная сумма."
        )
        return

    if new_amount <= 0:
        await message.answer(
            "❌ Сумма должна быть больше нуля."
        )
        return

    data = await state.get_data()

    expense_id = data[
        "edit_expense_id"
    ]

    update_expense_amount(
        expense_id=expense_id,
        user_id=message.from_user.id,
        new_amount=new_amount,
    )

    await state.clear()

    await message.answer(
        "✅ Сумма изменена!\n\n"
        f"💰 Новая сумма: "
        f"{new_amount:.2f} ₽",
        reply_markup=main_keyboard,
    )


# =========================================================
# РЕДАКТИРОВАНИЕ КАТЕГОРИИ
# =========================================================

@dp.callback_query(
    lambda callback:
    callback.data
    and callback.data.startswith(
        "edit_category:"
    )
)
async def edit_category_callback(
    callback: CallbackQuery,
    state: FSMContext,
):
    expense_id = int(
        callback.data.split(":")[1]
    )

    await state.update_data(
        edit_expense_id=expense_id
    )

    await state.set_state(
        AddExpense.waiting_for_edit_category
    )

    await callback.message.edit_text(
        "🏷 Введи новую категорию:"
    )

    await callback.answer()


@dp.message(
    AddExpense.waiting_for_edit_category
)
async def process_edit_category(
    message: Message,
    state: FSMContext,
):
    category = message.text

    if not category:
        await message.answer(
            "❌ Отправь категорию текстом."
        )
        return

    new_category = normalize_category(
        category
    )

    data = await state.get_data()

    expense_id = data[
        "edit_expense_id"
    ]

    update_expense_category(
        expense_id=expense_id,
        user_id=message.from_user.id,
        new_category=new_category,
    )

    await state.clear()

    await message.answer(
        "✅ Категория изменена!\n\n"
        f"🏷 Новая категория: "
        f"{new_category}",
        reply_markup=main_keyboard,
    )


# =========================================================
# ЗАПУСК
# =========================================================

async def main():
    if not TOKEN:
        raise RuntimeError(
            "BOT_TOKEN не найден в .env"
        )

    init_db()

    session = TrustedEnvSession()

    bot = Bot(
        token=TOKEN,
        session=session,
    )

    print("KashBot запущен ✅")

    try:
        await dp.start_polling(bot)

    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())