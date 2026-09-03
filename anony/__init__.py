# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic


import time
import asyncio
import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler

logging.basicConfig(
    format="[%(asctime)s - %(levelname)s] - %(name)s: %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
    handlers=[
        RotatingFileHandler("log.txt", maxBytes=10485760, backupCount=5),
        logging.StreamHandler(),
    ],
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.ERROR)
logging.getLogger("ntgcalls").setLevel(logging.CRITICAL)
logging.getLogger("pymongo").setLevel(logging.ERROR)
logging.getLogger("pyrogram").setLevel(logging.ERROR)
logging.getLogger("pytgcalls").setLevel(logging.ERROR)
logger = logging.getLogger(__name__)


__version__ = "3.0.4"

from config import Config

config = Config()
config.check()
tasks = []
boot = time.time()

from anony.core.bot import Bot
app = Bot()

for d in ("cache", "downloads"):
    Path(d).mkdir(parents=True, exist_ok=True)
logger.info("Cache directories updated.")

from anony.core.userbot import Userbot
userbot = Userbot()

from anony.core.mongo import MongoDB
db = MongoDB()

from anony.core.lang import Language
lang = Language()

from anony.core.telegram import Telegram
from anony.core.youtube import YouTube
tg = Telegram()
yt = YouTube()

from anony.helpers import Queue
queue = Queue()

from anony.core.calls import TgCall
anon = TgCall()

from anony.helpers import progress_manager


async def _graceful(coro, timeout: float = 5) -> None:
    try:
        await asyncio.wait_for(coro, timeout=timeout)
    except Exception:
        pass


async def stop() -> None:
    logger.info("Stopping...")
    for task in tasks:
        try:
            await asyncio.wait([task], timeout=3)
        except Exception:
            continue

    await _graceful(progress_manager.stop_workers())
    await _graceful(app.exit())
    await _graceful(userbot.exit())
    await _graceful(db.close())

    logger.info("Stopped.\n")
