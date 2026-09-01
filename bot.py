import asyncio
import os
import aiohttp

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
    get_today_expenses,
    get_month_expenses,
    get_recent_expenses,
    delete_expense,
)

from categories import normalize_category

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")

dp = Dispatcher()

class AddExpense(StatesGroup):
    waiting_for_amount = State()
    waiting_for_category = State()

main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="➕ Добавить расход"),
            KeyboardButton(text="📊 Сегодня"),
        ],
        [
            KeyboardButton(text="📅 Месяц"),
            KeyboardButton(text="🗑 Удалить расход"),
        ],
    ],
    resize_keyboard=True,
)

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

class TrustedEnvSession(AiohttpSession):
    async def create_session(self):
        if self._should_reset_connector:
            await self.close()

        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                connector=self._connector_type(**self._connector_init),
                trust_env=True,
            )

            self._should_reset_connector = False

        return self._session

@dp.message(CommandStart())
async def start_handler(message: Message):
    await message.answer(
        "Привет 👋\n\n"
        "Я KashBot — бот для учёта расходов.",
        reply_markup=main_keyboard,
    )

@dp.message(Command("add"))
async def add_handler(message: Message, state: FSMContext):
    await state.set_state(AddExpense.waiting_for_amount)

    await message.answer(
        "💰 Сколько потратил?\n\n"
        "Например: 500"
    )

@dp.message(lambda message: message.text == "🗑 Удалить расход")
async def delete_expense_menu(message: Message):
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

    for expense_id, amount, category, created_at in expenses:
        button = InlineKeyboardButton(
            text=f"{category} — {amount:.2f} ₽",
            callback_data=f"delete:{expense_id}",
        )

        buttons.append([button])

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=buttons
    )

    await message.answer(
        "🗑 Выбери расход, который хочешь удалить:",
        reply_markup=keyboard,
    )

@dp.callback_query(
    lambda callback: callback.data
    and callback.data.startswith("delete:")
)
async def delete_expense_callback(callback: CallbackQuery):
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

@dp.message(lambda message: message.text == "➕ Добавить расход")
async def add_button_handler(
    message: Message,
    state: FSMContext
):
    await state.set_state(
        AddExpense.waiting_for_amount
    )

    await message.answer(
        "💰 Сколько потратил?\n\n"
        "Например: 500",
        reply_markup=ReplyKeyboardRemove(),
    )

@dp.message(AddExpense.waiting_for_amount)
async def process_amount(
    message: Message,
    state: FSMContext
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
            "❌ Некорректная сумма."
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

@dp.message(AddExpense.waiting_for_category)
async def process_category(
    message: Message,
    state: FSMContext
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

    add_expense(
        user_id=message.from_user.id,
        amount=amount,
        category=category,
    )

    await state.clear()

    await message.answer(
        "✅ Расход добавлен!\n\n"
        f"💰 Сумма: {amount:.2f} ₽\n"
        f"🏷️ Категория: {category}",
        reply_markup=main_keyboard,
    )

async def show_today_expenses(
    message: Message
):
    expenses = get_today_expenses(
        message.from_user.id
    )

    if not expenses:
        await message.answer(
            "Сегодня расходов пока нет.",
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

    text = "📊 Расходы за сегодня:\n\n"

    for category, amount in categories_total.items():
        text += (
            f"{category}: "
            f"{amount:.2f} ₽\n"
        )

    text += (
        f"\n💰 Итого: "
        f"{total:.2f} ₽"
    )

    await message.answer(
        text,
        reply_markup=main_keyboard,
    )

async def show_month_expenses(message: Message):
    expenses = get_month_expenses(message.from_user.id)

    if not expenses:
        await message.answer(
            "В этом месяце расходов пока нет.",
            reply_markup=main_keyboard,
        )
        return

    total = sum(expense[0] for expense in expenses)

    categories_total = {}

    for amount, category, created_at in expenses:
        if category in categories_total:
            categories_total[category] += amount
        else:
            categories_total[category] = amount

    text = "📅 Расходы за текущий месяц:\n\n"

    for category, amount in categories_total.items():
        text += f"{category}: {amount:.2f} ₽\n"

    text += f"\n💰 Итого: {total:.2f} ₽"

    await message.answer(
        text,
        reply_markup=main_keyboard,
    )

@dp.message(Command("today"))
async def today_handler(
    message: Message
):
    await show_today_expenses(
        message
    )

@dp.message(Command("month"))
async def month_handler(message: Message):
    await show_month_expenses(message)

@dp.message(lambda message: message.text == "📅 Месяц")
async def month_button_handler(message: Message):
    await show_month_expenses(message)

@dp.message(lambda message: message.text == "📊 Сегодня")
async def today_button_handler(
    message: Message
):
    await show_today_expenses(
        message
    )

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