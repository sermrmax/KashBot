import asyncio
import aiohttp

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.client.session.aiohttp import AiohttpSession


TOKEN = "8880394696:AAHIWIfWOdT94MJ5taiiQ2K68Kq4E_s33Mo"

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
    await message.answer("KashBot работает ✅")


async def main():
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