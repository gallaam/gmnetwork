import asyncio
import ctypes
import os

from core.autoreger import AutoReger
from art import tprint


def bot_info(name: str = ""):
    tprint(name)

    if os.name == 'nt':
        ctypes.windll.kernel32.SetConsoleTitleW(f"{name}")
    


async def main():
    bot_info("GmNetwork_Daily")
    await AutoReger().start()


if __name__ == '__main__':
    asyncio.run(main())
