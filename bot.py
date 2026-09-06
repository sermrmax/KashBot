import asyncio
import os
from datetime import datetime, timedelta

import aiohttp

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    Message,
    ReplyKeyboardRemove,
)

from dotenv import load_dotenv

from categories import normalize_category

from database import (
    # База данных
    init_db,

    # Обычные расходы
    add_expense,
    get_recent_expenses,
    delete_expense,
    update_expense_amount,
    update_expense_category,
    get_expenses_by_period,

    # Лимиты
    set_category_limit,
    get_category_limits,
    get_category_limit,
    delete_category_limit,

    # Регулярные расходы
    add_recurring_expense,
    get_recurring_expenses,
    get_recurring_expense,
    delete_recurring_expense,
    update_recurring_name,
    update_recurring_amount,
    update_recurring_category,
    update_recurring_day,

    # Бюджет
    set_monthly_budget,
    get_monthly_budget,
    delete_monthly_budget,
)

from keyboards import (
    main_keyboard,
    category_keyboard,
    get_undo_keyboard,
    get_period_keyboard,
    get_budget_keyboard,
    get_limits_keyboard,
    get_delete_limits_keyboard,
    get_recurring_menu_keyboard,
    get_recurring_pay_keyboard,
    get_recurring_edit_keyboard,
    get_recurring_edit_fields_keyboard,
    get_recurring_delete_keyboard,
    get_delete_expenses_keyboard,
    get_edit_expenses_keyboard,
    get_edit_expense_fields_keyboard,
)


# =========================================================
# 1. НАСТРОЙКИ
# =========================================================

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")

dp = Dispatcher()


# =========================================================
# 2. КОНСТАНТЫ
# =========================================================

MONTHS_RU = {
    1: "Январь",
    2: "Февраль",
    3: "Март",
    4: "Апрель",
    5: "Май",
    6: "Июнь",
    7: "Июль",
    8: "Август",
    9: "Сентябрь",
    10: "Октябрь",
    11: "Ноябрь",
    12: "Декабрь",
}


CATEGORY_EMOJIS = {
    "Еда": "🍔",
    "Транспорт": "🚕",
    "Табак": "🚬",
    "Развлечения": "🎮",
    "Покупки": "🛒",
    "Другое": "✍️",
}


CATEGORY_BUTTONS = {
    "🍔 Еда": "Еда",
    "🚕 Транспорт": "Транспорт",
    "🚬 Табак": "Табак",
    "🎮 Развлечения": "Развлечения",
    "🛒 Покупки": "Покупки",
    "✍️ Другое": "Другое",
}


# =========================================================
# 3. FSM-СОСТОЯНИЯ
# =========================================================

class ExpenseStates(StatesGroup):
    """Состояния обычных расходов."""

    waiting_for_amount = State()
    waiting_for_category = State()

    waiting_for_edit_amount = State()
    waiting_for_edit_category = State()


class LimitStates(StatesGroup):
    """Состояния лимитов."""

    waiting_for_category = State()
    waiting_for_amount = State()


class BudgetStates(StatesGroup):
    """Состояния общего бюджета."""

    waiting_for_amount = State()


class RecurringStates(StatesGroup):
    """Состояния регулярных расходов."""

    waiting_for_name = State()
    waiting_for_amount = State()
    waiting_for_category = State()
    waiting_for_day = State()

    waiting_for_edit_name = State()
    waiting_for_edit_amount = State()
    waiting_for_edit_category = State()
    waiting_for_edit_day = State()


# =========================================================
# 4. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =========================================================

def prepare_category(category: str) -> str:
    """
    Приводит категорию к стандартному виду.

    Например:
    🍔 Еда -> Еда
    хавчик -> Еда
    такси -> Транспорт
    """

    category = category.strip()

    if category in CATEGORY_BUTTONS:
        return CATEGORY_BUTTONS[category]

    return normalize_category(category)


def get_category_emoji(category: str) -> str:
    """Возвращает emoji категории."""

    return CATEGORY_EMOJIS.get(
        category,
        "•",
    )


def get_usage_indicator(percent: float) -> str:
    """
    Возвращает индикатор использования
    бюджета или лимита.
    """

    if percent < 60:
        return "🟢"

    if percent < 80:
        return "🟡"

    if percent <= 100:
        return "🟠"

    return "🔴"


def parse_positive_amount(
    text: str,
) -> float | None:
    """
    Преобразует текст в положительное число.

    Поддерживает:
    500
    500.50
    500,50
    """

    try:
        amount = float(
            text.replace(",", ".")
        )

    except ValueError:
        return None

    if amount <= 0:
        return None

    return amount


def get_current_month_expenses(
    user_id: int,
):
    """Возвращает расходы текущего месяца."""

    today = datetime.now().date()
    start_date = today.replace(day=1)

    return get_expenses_by_period(
        user_id=user_id,
        start_date=start_date.isoformat(),
        end_date=today.isoformat(),
    )


# =========================================================
# 5. TELEGRAM SESSION
# =========================================================

class TrustedEnvSession(AiohttpSession):
    """
    aiohttp-сессия с trust_env=True.

    Нужна в текущей локальной среде,
    чтобы учитывать системный proxy/VPN.
    """

    async def create_session(self):

        if self._should_reset_connector:
            await self.close()

        if (
            self._session is None
            or self._session.closed
        ):
            self._session = aiohttp.ClientSession(
                connector=self._connector_type(
                    **self._connector_init
                ),
                trust_env=True,
            )

            self._should_reset_connector = False

        return self._session


# =========================================================
# 6. /START
# =========================================================

@dp.message(CommandStart())
async def start_handler(
    message: Message,
):
    """Приветствие и главное меню."""

    await message.answer(
        "Привет 👋\n\n"
        "Я KashBot — бот для учёта расходов.\n\n"
        "Выбирай действие ниже 👇",
        reply_markup=main_keyboard,
    )


# =========================================================
# 7. ДОБАВЛЕНИЕ РАСХОДА
# =========================================================

async def start_add_expense(
    message: Message,
    state: FSMContext,
):
    """Запускает процесс добавления расхода."""

    await state.set_state(
        ExpenseStates.waiting_for_amount
    )

    await message.answer(
        "💰 Сколько потратил?\n\n"
        "Например: 500",
        reply_markup=ReplyKeyboardRemove(),
    )


@dp.message(Command("add"))
async def add_command_handler(
    message: Message,
    state: FSMContext,
):
    await start_add_expense(
        message,
        state,
    )


@dp.message(
    lambda message:
    message.text == "➕ Добавить расход"
)
async def add_button_handler(
    message: Message,
    state: FSMContext,
):
    await start_add_expense(
        message,
        state,
    )


@dp.message(
    ExpenseStates.waiting_for_amount
)
async def process_expense_amount(
    message: Message,
    state: FSMContext,
):
    """Получаем сумму расхода."""

    if not message.text:
        await message.answer(
            "❌ Отправь сумму текстом."
        )
        return

    amount = parse_positive_amount(
        message.text
    )

    if amount is None:
        await message.answer(
            "❌ Некорректная сумма.\n\n"
            "Например: 500"
        )
        return

    await state.update_data(
        amount=amount
    )

    await state.set_state(
        ExpenseStates.waiting_for_category
    )

    await message.answer(
        "🏷 Выбери категорию "
        "или напиши свою:",
        reply_markup=category_keyboard,
    )


@dp.message(
    ExpenseStates.waiting_for_category
)
async def process_expense_category(
    message: Message,
    state: FSMContext,
):
    """Получаем категорию и сохраняем расход."""

    if not message.text:
        await message.answer(
            "❌ Отправь категорию."
        )
        return

    category = prepare_category(
        message.text
    )

    data = await state.get_data()

    amount = data["amount"]
    user_id = message.from_user.id

    expense_id = add_expense(
        user_id=user_id,
        amount=amount,
        category=category,
    )

    await state.clear()

    text = (
        "✅ Расход добавлен!\n\n"
        f"💰 Сумма: {amount:.2f} ₽\n"
        f"🏷 Категория: {category}"
    )

    month_expenses = (
        get_current_month_expenses(
            user_id
        )
    )

    # -----------------------------------------------------
    # Лимит категории
    # -----------------------------------------------------

    category_limit = get_category_limit(
        user_id=user_id,
        category=category,
    )

    if category_limit is not None:

        category_spent = sum(
            expense_amount
            for (
                expense_amount,
                expense_category,
                created_at,
            ) in month_expenses
            if expense_category == category
        )

        remaining = (
            category_limit - category_spent
        )

        percent = (
            category_spent
            / category_limit
            * 100
        )

        indicator = get_usage_indicator(
            percent
        )

        text += (
            "\n\n"
            f"{indicator} Лимит категории:\n"
            f"{category_spent:.2f} / "
            f"{category_limit:.2f} ₽\n"
        )

        if remaining >= 0:

            text += (
                f"Осталось: "
                f"{remaining:.2f} ₽\n"
                f"Использовано: "
                f"{percent:.0f}%"
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
                f"Использовано: "
                f"{percent:.0f}%"
            )

    # -----------------------------------------------------
    # Общий месячный бюджет
    # -----------------------------------------------------

    monthly_budget = get_monthly_budget(
        user_id
    )

    if monthly_budget is not None:

        total_spent = sum(
            expense_amount
            for (
                expense_amount,
                expense_category,
                created_at,
            ) in month_expenses
        )

        remaining_budget = (
            monthly_budget - total_spent
        )

        percent = (
            total_spent
            / monthly_budget
            * 100
        )

        indicator = get_usage_indicator(
            percent
        )

        text += (
            "\n\n"
            f"{indicator} Общий бюджет:\n"
            f"{total_spent:.2f} / "
            f"{monthly_budget:.2f} ₽\n"
        )

        if remaining_budget >= 0:

            text += (
                f"Осталось: "
                f"{remaining_budget:.2f} ₽\n"
                f"Использовано: "
                f"{percent:.0f}%"
            )

        else:

            text += (
                "⚠️ Бюджет превышен!\n"
                f"Превышение: "
                f"{abs(remaining_budget):.2f} ₽\n"
                f"Использовано: "
                f"{percent:.0f}%"
            )

    await message.answer(
        text,
        reply_markup=get_undo_keyboard(
            expense_id
        ),
    )

    await message.answer(
        "Выбери следующее действие 👇",
        reply_markup=main_keyboard,
    )


# =========================================================
# 8. ОТМЕНА РАСХОДА
# =========================================================

@dp.callback_query(
    lambda callback:
    callback.data
    and callback.data.startswith(
        "undo_expense:"
    )
)
async def undo_expense_callback(
    callback: CallbackQuery,
):
    """Отменяет конкретный добавленный расход."""

    expense_id = int(
        callback.data.split(":")[1]
    )

    delete_expense(
        expense_id=expense_id,
        user_id=callback.from_user.id,
    )

    await callback.answer(
        "Расход отменён ↩️"
    )

    await callback.message.edit_text(
        "↩️ Расход отменён.\n\n"
        "Запись удалена из расходов."
    )


# =========================================================
# 9. ПЕРИОД
# =========================================================

@dp.message(
    lambda message:
    message.text == "📆 Период"
)
async def period_menu(
    message: Message,
):
    """Показывает выбор периода."""

    await message.answer(
        "📆 Выбери период:",
        reply_markup=get_period_keyboard(),
    )


async def show_period_expenses(
    message: Message,
    user_id: int,
    start_date: str,
    end_date: str,
    title: str,
):
    """Формирует отчёт расходов за период."""

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
        amount
        for amount, category, created_at
        in expenses
    )

    categories_total = {}

    for amount, category, created_at in expenses:

        categories_total[category] = (
            categories_total.get(
                category,
                0,
            )
            + amount
        )

    text = f"{title}\n\n"

    for category, amount in categories_total.items():

        emoji = get_category_emoji(
            category
        )

        text += (
            f"{emoji} {category}: "
            f"{amount:.2f} ₽\n"
        )

    text += (
        f"\n💰 Итого: {total:.2f} ₽"
    )

    await message.answer(
        text,
        reply_markup=main_keyboard,
    )


@dp.callback_query(
    lambda callback:
    callback.data
    and callback.data.startswith(
        "period:"
    )
)
async def period_callback(
    callback: CallbackQuery,
):
    """Обрабатывает выбранный период."""

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

        start_date = today.replace(day=1)
        end_date = today

        title = (
            "📅 Расходы за текущий месяц"
        )

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
# 10. СТАТИСТИКА
# =========================================================

@dp.message(
    lambda message:
    message.text == "📊 Статистика"
)
async def statistics_handler(
    message: Message,
):
    """Статистика текущего месяца."""

    user_id = message.from_user.id
    today = datetime.now().date()

    expenses = get_current_month_expenses(
        user_id
    )

    if not expenses:

        await message.answer(
            "📊 Статистика\n\n"
            "В этом месяце расходов пока нет.",
            reply_markup=main_keyboard,
        )

        return

    total = sum(
        amount
        for amount, category, created_at
        in expenses
    )

    operations_count = len(expenses)

    average_expense = (
        total / operations_count
    )

    average_per_day = (
        total / today.day
    )

    categories_total = {}

    for amount, category, created_at in expenses:

        categories_total[category] = (
            categories_total.get(
                category,
                0,
            )
            + amount
        )

    sorted_categories = sorted(
        categories_total.items(),
        key=lambda item: item[1],
        reverse=True,
    )

    (
        top_category_name,
        top_category_amount,
    ) = sorted_categories[0]

    month_name = MONTHS_RU[
        today.month
    ]

    text = (
        f"📊 Статистика — {month_name}\n\n"
        f"💰 Потрачено: {total:.2f} ₽\n"
        f"🧾 Операций: {operations_count}\n"
        f"💳 Средний расход: "
        f"{average_expense:.2f} ₽\n"
        f"📅 Средние траты в день: "
        f"{average_per_day:.2f} ₽\n\n"
        "Категории:\n"
    )

    for category, amount in sorted_categories:

        percent = (
            amount / total * 100
        )

        emoji = get_category_emoji(
            category
        )

        text += (
            f"{emoji} {category} — "
            f"{amount:.2f} ₽ "
            f"({percent:.0f}%)\n"
        )

    top_emoji = get_category_emoji(
        top_category_name
    )

    text += (
        "\n🏆 Больше всего расходов:\n"
        f"{top_emoji} "
        f"{top_category_name} — "
        f"{top_category_amount:.2f} ₽"
    )

    await message.answer(
        text,
        reply_markup=main_keyboard,
    )


# =========================================================
# 11. БЮДЖЕТ
# =========================================================

@dp.message(
    lambda message:
    message.text == "💼 Бюджет"
)
async def budget_menu(
    message: Message,
):
    """Главное меню бюджета."""

    await message.answer(
        "💼 Общий месячный бюджет\n\n"
        "Здесь можно установить общий "
        "лимит расходов на месяц.",
        reply_markup=get_budget_keyboard(),
    )


@dp.callback_query(
    lambda callback:
    callback.data == "budget:set"
)
async def budget_set_callback(
    callback: CallbackQuery,
    state: FSMContext,
):
    """Начинает установку бюджета."""

    await state.set_state(
        BudgetStates.waiting_for_amount
    )

    await callback.answer()

    await callback.message.answer(
        "💼 Какой бюджет установить "
        "на месяц?\n\n"
        "Например: 100000"
    )


@dp.message(
    BudgetStates.waiting_for_amount
)
async def process_budget_amount(
    message: Message,
    state: FSMContext,
):
    """Получает сумму бюджета."""

    if not message.text:
        await message.answer(
            "❌ Отправь сумму."
        )
        return

    amount = parse_positive_amount(
        message.text
    )

    if amount is None:
        await message.answer(
            "❌ Некорректная сумма.\n\n"
            "Например: 100000"
        )
        return

    set_monthly_budget(
        user_id=message.from_user.id,
        amount=amount,
    )

    await state.clear()

    await message.answer(
        "✅ Месячный бюджет установлен!\n\n"
        f"💼 Бюджет: {amount:.2f} ₽",
        reply_markup=main_keyboard,
    )


@dp.callback_query(
    lambda callback:
    callback.data == "budget:show"
)
async def budget_show_callback(
    callback: CallbackQuery,
):
    """Показывает состояние бюджета."""

    user_id = callback.from_user.id

    budget = get_monthly_budget(
        user_id
    )

    await callback.answer()

    if budget is None:

        await callback.message.answer(
            "💼 Месячный бюджет "
            "пока не установлен.",
            reply_markup=main_keyboard,
        )

        return

    today = datetime.now().date()

    expenses = get_current_month_expenses(
        user_id
    )

    spent = sum(
        amount
        for amount, category, created_at
        in expenses
    )

    remaining = budget - spent

    percent = (
        spent / budget * 100
    )

    indicator = get_usage_indicator(
        percent
    )

    month_name = MONTHS_RU[
        today.month
    ]

    text = (
        f"💼 Бюджет — {month_name}\n\n"
        f"Бюджет: {budget:.2f} ₽\n"
        f"Потрачено: {spent:.2f} ₽\n"
    )

    if remaining >= 0:

        text += (
            f"Осталось: {remaining:.2f} ₽\n"
            f"Использовано: "
            f"{percent:.0f}%\n\n"
            f"{indicator} "
            "Бюджет пока не превышен."
        )

    else:

        text += (
            f"Превышение: "
            f"{abs(remaining):.2f} ₽\n"
            f"Использовано: "
            f"{percent:.0f}%\n\n"
            "🔴 Бюджет превышен!"
        )

    await callback.message.answer(
        text,
        reply_markup=main_keyboard,
    )


@dp.callback_query(
    lambda callback:
    callback.data == "budget:delete"
)
async def budget_delete_callback(
    callback: CallbackQuery,
):
    """Удаляет месячный бюджет."""

    user_id = callback.from_user.id

    budget = get_monthly_budget(
        user_id
    )

    await callback.answer()

    if budget is None:

        await callback.message.answer(
            "💼 Бюджет пока не установлен.",
            reply_markup=main_keyboard,
        )

        return

    delete_monthly_budget(
        user_id
    )

    await callback.message.edit_text(
        "✅ Месячный бюджет удалён."
    )


# =========================================================
# 12. ЛИМИТЫ
# =========================================================

@dp.message(
    lambda message:
    message.text == "🎯 Лимиты"
)
async def limits_menu(
    message: Message,
):
    """Главное меню лимитов."""

    await message.answer(
        "🎯 Лимиты по категориям\n\n"
        "Можно установить месячный "
        "лимит для каждой категории.",
        reply_markup=get_limits_keyboard(),
    )


@dp.callback_query(
    lambda callback:
    callback.data == "limit:set"
)
async def limit_set_callback(
    callback: CallbackQuery,
    state: FSMContext,
):
    """Начинает установку лимита."""

    await state.set_state(
        LimitStates.waiting_for_category
    )

    await callback.answer()

    await callback.message.answer(
        "🏷 Выбери категорию "
        "или напиши свою:",
        reply_markup=category_keyboard,
    )


@dp.message(
    LimitStates.waiting_for_category
)
async def process_limit_category(
    message: Message,
    state: FSMContext,
):
    """Получает категорию лимита."""

    if not message.text:
        await message.answer(
            "❌ Отправь категорию."
        )
        return

    category = prepare_category(
        message.text
    )

    await state.update_data(
        limit_category=category
    )

    await state.set_state(
        LimitStates.waiting_for_amount
    )

    await message.answer(
        f"🎯 Категория: {category}\n\n"
        "Какой месячный лимит установить?\n\n"
        "Например: 15000",
        reply_markup=ReplyKeyboardRemove(),
    )


@dp.message(
    LimitStates.waiting_for_amount
)
async def process_limit_amount(
    message: Message,
    state: FSMContext,
):
    """Получает сумму лимита."""

    if not message.text:
        await message.answer(
            "❌ Отправь сумму."
        )
        return

    amount = parse_positive_amount(
        message.text
    )

    if amount is None:
        await message.answer(
            "❌ Некорректная сумма."
        )
        return

    data = await state.get_data()

    category = data["limit_category"]

    set_category_limit(
        user_id=message.from_user.id,
        category=category,
        amount=amount,
    )

    await state.clear()

    await message.answer(
        "✅ Лимит установлен!\n\n"
        f"🏷 Категория: {category}\n"
        f"🎯 Лимит: "
        f"{amount:.2f} ₽ / месяц",
        reply_markup=main_keyboard,
    )


@dp.callback_query(
    lambda callback:
    callback.data == "limit:list"
)
async def show_limits_callback(
    callback: CallbackQuery,
):
    """Показывает лимиты пользователя."""

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

    expenses = get_current_month_expenses(
        user_id
    )

    text = (
        "🎯 Лимиты на текущий месяц\n\n"
    )

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
        )

        indicator = get_usage_indicator(
            percent
        )

        if remaining >= 0:

            status = (
                f"Осталось: "
                f"{remaining:.2f} ₽"
            )

        else:

            status = (
                "⚠️ Превышение: "
                f"{abs(remaining):.2f} ₽"
            )

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


@dp.callback_query(
    lambda callback:
    callback.data == "limit:delete_menu"
)
async def delete_limit_menu(
    callback: CallbackQuery,
):
    """Выбор лимита для удаления."""

    limits = get_category_limits(
        callback.from_user.id
    )

    await callback.answer()

    if not limits:

        await callback.message.answer(
            "Удалять пока нечего."
        )

        return

    await callback.message.answer(
        "🗑 Выбери лимит для удаления:",
        reply_markup=(
            get_delete_limits_keyboard(
                limits
            )
        ),
    )


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
    """Удаляет выбранный лимит."""

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
# 13. РЕГУЛЯРНЫЕ РАСХОДЫ — МЕНЮ
# =========================================================

@dp.message(
    lambda message:
    message.text == "🔁 Регулярные"
)
async def recurring_menu(
    message: Message,
):
    """Главное меню регулярных расходов."""

    await message.answer(
        "🔁 Регулярные расходы\n\n"
        "Здесь можно хранить ежемесячные "
        "обязательные расходы.",
        reply_markup=(
            get_recurring_menu_keyboard()
        ),
    )


# =========================================================
# 14. РЕГУЛЯРНЫЕ — ДОБАВЛЕНИЕ
# =========================================================

@dp.callback_query(
    lambda callback:
    callback.data == "recurring:add"
)
async def recurring_add_callback(
    callback: CallbackQuery,
    state: FSMContext,
):
    """Начинает добавление регулярного расхода."""

    await state.set_state(
        RecurringStates.waiting_for_name
    )

    await callback.answer()

    await callback.message.answer(
        "🔁 Введи название расхода.\n\n"
        "Например: Интернет"
    )


@dp.message(
    RecurringStates.waiting_for_name
)
async def process_recurring_name(
    message: Message,
    state: FSMContext,
):
    """Получает название."""

    if not message.text:
        await message.answer(
            "❌ Введи название."
        )
        return

    name = message.text.strip()

    if not name:
        await message.answer(
            "❌ Название не может быть пустым."
        )
        return

    await state.update_data(
        recurring_name=name
    )

    await state.set_state(
        RecurringStates.waiting_for_amount
    )

    await message.answer(
        "💰 Какая сумма?\n\n"
        "Например: 900"
    )


@dp.message(
    RecurringStates.waiting_for_amount
)
async def process_recurring_amount(
    message: Message,
    state: FSMContext,
):
    """Получает сумму."""

    if not message.text:
        await message.answer(
            "❌ Отправь сумму."
        )
        return

    amount = parse_positive_amount(
        message.text
    )

    if amount is None:
        await message.answer(
            "❌ Некорректная сумма.\n\n"
            "Например: 900"
        )
        return

    await state.update_data(
        recurring_amount=amount
    )

    await state.set_state(
        RecurringStates.waiting_for_category
    )

    await message.answer(
        "🏷 Выбери категорию "
        "или напиши свою:",
        reply_markup=category_keyboard,
    )


@dp.message(
    RecurringStates.waiting_for_category
)
async def process_recurring_category(
    message: Message,
    state: FSMContext,
):
    """Получает категорию."""

    if not message.text:
        await message.answer(
            "❌ Отправь категорию."
        )
        return

    category = prepare_category(
        message.text
    )

    await state.update_data(
        recurring_category=category
    )

    await state.set_state(
        RecurringStates.waiting_for_day
    )

    await message.answer(
        "📅 Какого числа каждого месяца "
        "этот расход нужно оплатить?\n\n"
        "Введи число от 1 до 31.\n"
        "Например: 10",
        reply_markup=ReplyKeyboardRemove(),
    )


@dp.message(
    RecurringStates.waiting_for_day
)
async def process_recurring_day(
    message: Message,
    state: FSMContext,
):
    """Получает день и сохраняет расход."""

    if not message.text:
        await message.answer(
            "❌ Введи число от 1 до 31."
        )
        return

    try:
        day = int(
            message.text.strip()
        )

    except ValueError:
        await message.answer(
            "❌ Нужно ввести число.\n\n"
            "Например: 10"
        )
        return

    if not 1 <= day <= 31:
        await message.answer(
            "❌ День должен быть от 1 до 31."
        )
        return

    data = await state.get_data()

    name = data["recurring_name"]
    amount = data["recurring_amount"]
    category = data["recurring_category"]

    add_recurring_expense(
        user_id=message.from_user.id,
        name=name,
        amount=amount,
        category=category,
        day_of_month=day,
    )

    await state.clear()

    await message.answer(
        "✅ Регулярный расход добавлен!\n\n"
        f"🔁 {name}\n"
        f"💰 {amount:.2f} ₽\n"
        f"🏷 {category}\n"
        f"📅 Каждый месяц: "
        f"{day} числа",
        reply_markup=main_keyboard,
    )


# =========================================================
# 15. РЕГУЛЯРНЫЕ — ПРОСМОТР
# =========================================================

@dp.callback_query(
    lambda callback:
    callback.data == "recurring:list"
)
async def recurring_list_callback(
    callback: CallbackQuery,
):
    """Показывает регулярные расходы."""

    expenses = get_recurring_expenses(
        callback.from_user.id
    )

    await callback.answer()

    if not expenses:

        await callback.message.answer(
            "🔁 Регулярных расходов пока нет.",
            reply_markup=main_keyboard,
        )

        return

    total = sum(
        amount
        for (
            recurring_id,
            name,
            amount,
            category,
            day,
        ) in expenses
    )

    text = (
        "🔁 Регулярные расходы\n\n"
    )

    for (
        recurring_id,
        name,
        amount,
        category,
        day,
    ) in expenses:

        text += (
            f"• {name}\n"
            f"  💰 {amount:.2f} ₽\n"
            f"  🏷 {category}\n"
            f"  📅 {day} числа\n\n"
        )

    text += (
        "💰 Всего обязательных расходов "
        f"в месяц: {total:.2f} ₽"
    )

    await callback.message.answer(
        text,
        reply_markup=main_keyboard,
    )


# =========================================================
# 16. РЕГУЛЯРНЫЕ — ОПЛАТА
# =========================================================

@dp.callback_query(
    lambda callback:
    callback.data == "recurring:pay_menu"
)
async def recurring_pay_menu(
    callback: CallbackQuery,
):
    """Выбор оплаченного регулярного расхода."""

    expenses = get_recurring_expenses(
        callback.from_user.id
    )

    await callback.answer()

    if not expenses:
        await callback.message.answer(
            "🔁 Регулярных расходов пока нет."
        )
        return

    await callback.message.answer(
        "✅ Что ты оплатил?",
        reply_markup=(
            get_recurring_pay_keyboard(
                expenses
            )
        ),
    )


@dp.callback_query(
    lambda callback:
    callback.data
    and callback.data.startswith(
        "recurring_pay:"
    )
)
async def recurring_pay_callback(
    callback: CallbackQuery,
):
    """Добавляет оплаченный регулярный расход в обычные."""

    recurring_id = int(
        callback.data.split(":")[1]
    )

    recurring = get_recurring_expense(
        recurring_id=recurring_id,
        user_id=callback.from_user.id,
    )

    if not recurring:
        await callback.answer(
            "Расход не найден."
        )
        return

    (
        recurring_id,
        name,
        amount,
        category,
        day,
    ) = recurring

    expense_id = add_expense(
        user_id=callback.from_user.id,
        amount=amount,
        category=category,
    )

    await callback.answer(
        "Оплачено ✅"
    )

    await callback.message.edit_text(
        "✅ Регулярный расход оплачен!\n\n"
        f"🔁 {name}\n"
        f"💰 {amount:.2f} ₽\n"
        f"🏷 {category}\n\n"
        "Расход добавлен в общую статистику.",
        reply_markup=get_undo_keyboard(
            expense_id
        ),
    )


# =========================================================
# 17. РЕГУЛЯРНЫЕ — РЕДАКТИРОВАНИЕ
# =========================================================

@dp.callback_query(
    lambda callback:
    callback.data == "recurring:edit_menu"
)
async def recurring_edit_menu(
    callback: CallbackQuery,
):
    """Выбор регулярного расхода."""

    expenses = get_recurring_expenses(
        callback.from_user.id
    )

    await callback.answer()

    if not expenses:
        await callback.message.answer(
            "Редактировать пока нечего."
        )
        return

    await callback.message.answer(
        "✏️ Выбери регулярный расход:",
        reply_markup=(
            get_recurring_edit_keyboard(
                expenses
            )
        ),
    )


@dp.callback_query(
    lambda callback:
    callback.data
    and callback.data.startswith(
        "recurring_edit:"
    )
)
async def recurring_edit_select(
    callback: CallbackQuery,
):
    """Выбор поля регулярного расхода."""

    recurring_id = int(
        callback.data.split(":")[1]
    )

    recurring = get_recurring_expense(
        recurring_id=recurring_id,
        user_id=callback.from_user.id,
    )

    if not recurring:
        await callback.answer(
            "Расход не найден."
        )
        return

    (
        recurring_id,
        name,
        amount,
        category,
        day,
    ) = recurring

    await callback.message.edit_text(
        "✏️ Редактирование\n\n"
        f"🔁 {name}\n"
        f"💰 {amount:.2f} ₽\n"
        f"🏷 {category}\n"
        f"📅 {day} числа\n\n"
        "Что изменить?",
        reply_markup=(
            get_recurring_edit_fields_keyboard(
                recurring_id
            )
        ),
    )

    await callback.answer()


@dp.callback_query(
    lambda callback:
    callback.data
    and callback.data.startswith(
        "rec_edit_name:"
    )
)
async def recurring_edit_name_callback(
    callback: CallbackQuery,
    state: FSMContext,
):
    recurring_id = int(
        callback.data.split(":")[1]
    )

    await state.update_data(
        recurring_edit_id=recurring_id
    )

    await state.set_state(
        RecurringStates.waiting_for_edit_name
    )

    await callback.answer()

    await callback.message.answer(
        "📝 Введи новое название:"
    )


@dp.message(
    RecurringStates.waiting_for_edit_name
)
async def process_recurring_edit_name(
    message: Message,
    state: FSMContext,
):
    if not message.text:
        await message.answer(
            "❌ Введи название."
        )
        return

    new_name = message.text.strip()

    if not new_name:
        await message.answer(
            "❌ Название не может быть пустым."
        )
        return

    data = await state.get_data()

    update_recurring_name(
        recurring_id=(
            data["recurring_edit_id"]
        ),
        user_id=message.from_user.id,
        new_name=new_name,
    )

    await state.clear()

    await message.answer(
        "✅ Название изменено!\n\n"
        f"📝 Новое название: {new_name}",
        reply_markup=main_keyboard,
    )


@dp.callback_query(
    lambda callback:
    callback.data
    and callback.data.startswith(
        "rec_edit_amount:"
    )
)
async def recurring_edit_amount_callback(
    callback: CallbackQuery,
    state: FSMContext,
):
    recurring_id = int(
        callback.data.split(":")[1]
    )

    await state.update_data(
        recurring_edit_id=recurring_id
    )

    await state.set_state(
        RecurringStates.waiting_for_edit_amount
    )

    await callback.answer()

    await callback.message.answer(
        "💰 Введи новую сумму:"
    )


@dp.message(
    RecurringStates.waiting_for_edit_amount
)
async def process_recurring_edit_amount(
    message: Message,
    state: FSMContext,
):
    if not message.text:
        await message.answer(
            "❌ Отправь сумму."
        )
        return

    new_amount = parse_positive_amount(
        message.text
    )

    if new_amount is None:
        await message.answer(
            "❌ Некорректная сумма."
        )
        return

    data = await state.get_data()

    update_recurring_amount(
        recurring_id=(
            data["recurring_edit_id"]
        ),
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


@dp.callback_query(
    lambda callback:
    callback.data
    and callback.data.startswith(
        "rec_edit_category:"
    )
)
async def recurring_edit_category_callback(
    callback: CallbackQuery,
    state: FSMContext,
):
    recurring_id = int(
        callback.data.split(":")[1]
    )

    await state.update_data(
        recurring_edit_id=recurring_id
    )

    await state.set_state(
        RecurringStates.waiting_for_edit_category
    )

    await callback.answer()

    await callback.message.answer(
        "🏷 Выбери новую категорию "
        "или напиши свою:",
        reply_markup=category_keyboard,
    )


@dp.message(
    RecurringStates.waiting_for_edit_category
)
async def process_recurring_edit_category(
    message: Message,
    state: FSMContext,
):
    if not message.text:
        await message.answer(
            "❌ Отправь категорию."
        )
        return

    new_category = prepare_category(
        message.text
    )

    data = await state.get_data()

    update_recurring_category(
        recurring_id=(
            data["recurring_edit_id"]
        ),
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


@dp.callback_query(
    lambda callback:
    callback.data
    and callback.data.startswith(
        "rec_edit_day:"
    )
)
async def recurring_edit_day_callback(
    callback: CallbackQuery,
    state: FSMContext,
):
    recurring_id = int(
        callback.data.split(":")[1]
    )

    await state.update_data(
        recurring_edit_id=recurring_id
    )

    await state.set_state(
        RecurringStates.waiting_for_edit_day
    )

    await callback.answer()

    await callback.message.answer(
        "📅 Введи новый день оплаты "
        "от 1 до 31:"
    )


@dp.message(
    RecurringStates.waiting_for_edit_day
)
async def process_recurring_edit_day(
    message: Message,
    state: FSMContext,
):
    if not message.text:
        await message.answer(
            "❌ Введи число от 1 до 31."
        )
        return

    try:
        new_day = int(
            message.text.strip()
        )

    except ValueError:
        await message.answer(
            "❌ Нужно ввести число."
        )
        return

    if not 1 <= new_day <= 31:
        await message.answer(
            "❌ День должен быть от 1 до 31."
        )
        return

    data = await state.get_data()

    update_recurring_day(
        recurring_id=(
            data["recurring_edit_id"]
        ),
        user_id=message.from_user.id,
        new_day=new_day,
    )

    await state.clear()

    await message.answer(
        "✅ День оплаты изменён!\n\n"
        f"📅 Новый день: "
        f"{new_day} числа",
        reply_markup=main_keyboard,
    )


# =========================================================
# 18. РЕГУЛЯРНЫЕ — УДАЛЕНИЕ
# =========================================================

@dp.callback_query(
    lambda callback:
    callback.data == "recurring:delete_menu"
)
async def recurring_delete_menu(
    callback: CallbackQuery,
):
    """Выбор регулярного расхода для удаления."""

    expenses = get_recurring_expenses(
        callback.from_user.id
    )

    await callback.answer()

    if not expenses:
        await callback.message.answer(
            "Удалять пока нечего."
        )
        return

    await callback.message.answer(
        "🗑 Выбери регулярный расход "
        "для удаления:",
        reply_markup=(
            get_recurring_delete_keyboard(
                expenses
            )
        ),
    )


@dp.callback_query(
    lambda callback:
    callback.data
    and callback.data.startswith(
        "recurring_delete:"
    )
)
async def recurring_delete_callback(
    callback: CallbackQuery,
):
    """Удаляет регулярный расход."""

    recurring_id = int(
        callback.data.split(":")[1]
    )

    delete_recurring_expense(
        recurring_id=recurring_id,
        user_id=callback.from_user.id,
    )

    await callback.answer(
        "Удалено ✅"
    )

    await callback.message.edit_text(
        "✅ Регулярный расход удалён."
    )


# =========================================================
# 19. УДАЛЕНИЕ ОБЫЧНОГО РАСХОДА
# =========================================================

@dp.message(
    lambda message:
    message.text == "🗑 Удалить расход"
)
async def delete_expense_menu(
    message: Message,
):
    """Показывает последние 10 расходов."""

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

    await message.answer(
        "🗑 Выбери расход, который "
        "хочешь удалить:",
        reply_markup=(
            get_delete_expenses_keyboard(
                expenses
            )
        ),
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
    """Удаляет выбранный расход."""

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
# 20. РЕДАКТИРОВАНИЕ ОБЫЧНОГО РАСХОДА
# =========================================================

@dp.message(
    lambda message:
    message.text == "✏️ Редактировать расход"
)
async def edit_expense_menu(
    message: Message,
):
    """Выбор расхода для редактирования."""

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

    await message.answer(
        "✏️ Выбери расход, который "
        "хочешь изменить:",
        reply_markup=(
            get_edit_expenses_keyboard(
                expenses
            )
        ),
    )


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
    """Выбор поля расхода."""

    expense_id = int(
        callback.data.split(":")[1]
    )

    await callback.message.edit_text(
        "Что хочешь изменить?",
        reply_markup=(
            get_edit_expense_fields_keyboard(
                expense_id
            )
        ),
    )

    await callback.answer()


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
    """Начинает изменение суммы."""

    expense_id = int(
        callback.data.split(":")[1]
    )

    await state.update_data(
        edit_expense_id=expense_id
    )

    await state.set_state(
        ExpenseStates.waiting_for_edit_amount
    )

    await callback.message.edit_text(
        "💰 Введи новую сумму:"
    )

    await callback.answer()


@dp.message(
    ExpenseStates.waiting_for_edit_amount
)
async def process_edit_amount(
    message: Message,
    state: FSMContext,
):
    """Сохраняет новую сумму."""

    if not message.text:
        await message.answer(
            "❌ Отправь сумму."
        )
        return

    new_amount = parse_positive_amount(
        message.text
    )

    if new_amount is None:
        await message.answer(
            "❌ Некорректная сумма."
        )
        return

    data = await state.get_data()

    update_expense_amount(
        expense_id=data["edit_expense_id"],
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
    """Начинает изменение категории."""

    expense_id = int(
        callback.data.split(":")[1]
    )

    await state.update_data(
        edit_expense_id=expense_id
    )

    await state.set_state(
        ExpenseStates.waiting_for_edit_category
    )

    await callback.answer()

    await callback.message.answer(
        "🏷 Выбери новую категорию "
        "или напиши свою:",
        reply_markup=category_keyboard,
    )


@dp.message(
    ExpenseStates.waiting_for_edit_category
)
async def process_edit_category(
    message: Message,
    state: FSMContext,
):
    """Сохраняет новую категорию."""

    if not message.text:
        await message.answer(
            "❌ Отправь категорию."
        )
        return

    new_category = prepare_category(
        message.text
    )

    data = await state.get_data()

    update_expense_category(
        expense_id=data["edit_expense_id"],
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
# 21. ЗАПУСК
# =========================================================

async def main():
    """
    Точка входа KashBot.

    1. Проверяем BOT_TOKEN.
    2. Инициализируем SQLite.
    3. Создаём Telegram-сессию.
    4. Запускаем polling.
    """

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