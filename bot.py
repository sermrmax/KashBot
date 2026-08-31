import asyncio
import os
import aiohttp

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from dotenv import load_dotenv

from database import init_db, add_expense, get_today_expenses


load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")

dp = Dispatcher()


class AddExpense(StatesGroup):
    waiting_for_amount = State()
    waiting_for_category = State()


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
        "Я KashBot — бот для учёта расходов.\n\n"
        "Команды:\n"
        "/add — добавить расход\n"
        "/today — расходы за сегодня"
    )


@dp.message(Command("add"))
async def add_handler(message: Message, state: FSMContext):
    await state.set_state(AddExpense.waiting_for_amount)

    await message.answer(
        "💰 Сколько потратил?\n\n"
        "Например: 500"
    )


@dp.message(AddExpense.waiting_for_amount)
async def process_amount(message: Message, state: FSMContext):
    amount_text = message.text

    if not amount_text:
        await message.answer(
            "❌ Отправь сумму текстом.\n"
            "Например: 500"
        )
        return

    try:
        amount = float(amount_text.replace(",", "."))
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

    await state.update_data(amount=amount)

    await state.set_state(
        AddExpense.waiting_for_category
    )

    await message.answer(
        "🏷️ Введите категорию расхода\n\n"
        "Например: Еда, Транспорт, Развлечения"
    )


@dp.message(AddExpense.waiting_for_category)
async def process_category(message: Message, state: FSMContext):
    category = message.text

    if not category:
        await message.answer(
            "❌ Отправь категорию текстом.\n"
            "Например: Еда"
        )
        return

    category = category.strip()

    data = await state.get_data()
    amount = data["amount"]

    add_expense(
        user_id=message.from_user.id,
        amount=amount,
        category=category
    )

    await message.answer(
        "✅ Расход добавлен!\n\n"
        f"💰 Сумма: {amount:.2f} ₽\n"
        f"🏷️ Категория: {category}"
    )

    await state.clear()


@dp.message(Command("today"))
async def today_handler(message: Message):
    expenses = get_today_expenses(message.from_user.id)

    if not expenses:
        await message.answer(
            "Сегодня расходов пока нет."
        )
        return

    total = sum(expense[0] for expense in expenses)

    text = "Расходы за сегодня:\n\n"

    for amount, category, created_at in expenses:
        text += f"{category}: {amount:.2f} ₽\n"

    text += f"\nИтого: {total:.2f} ₽"

    await message.answer(text)


async def main():
    if not TOKEN:
        raise RuntimeError(
            "BOT_TOKEN не найден в .env"
        )

    init_db()

    session = TrustedEnvSession()

    bot = Bot(
        token=TOKEN,
        session=session
    )

    print("KashBot запущен ✅")

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())