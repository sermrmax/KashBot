import asyncio
import os
import aiohttp

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.client.session.aiohttp import AiohttpSession
from dotenv import load_dotenv

from database import init_db, add_expense, get_today_expenses

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")

dp = Dispatcher()


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
async def add_handler(message: Message):
    await message.answer(
        "Отправь расход в формате:\n\n"
        "500 Еда"
    )


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


@dp.message()
async def expense_handler(message: Message):
    text = message.text

    if not text:
        return

    parts = text.split(maxsplit=1)

    if len(parts) != 2:
        return

    amount_text, category = parts

    try:
        amount = float(
            amount_text.replace(",", ".")
        )
    except ValueError:
        return

    add_expense(
        user_id=message.from_user.id,
        amount=amount,
        category=category
    )

    await message.answer(
        f"✅ Расход сохранён\n\n"
        f"Сумма: {amount:.2f} ₽\n"
        f"Категория: {category}"
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
        session=session
    )

    print("KashBot запущен ✅")

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())