import asyncio
import aiohttp


async def main():
    async with aiohttp.ClientSession(trust_env=True) as session:
        async with session.get("https://api.telegram.org") as response:
            print(response.status)


asyncio.run(main())