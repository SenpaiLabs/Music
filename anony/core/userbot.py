# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic


import types
from pyrogram import Client

from anony import config, logger


class Userbot:
    def __init__(self):
        self.clients: list[Client] = []
        self._dummy = types.SimpleNamespace(on_raw_update=lambda *a, **k: lambda f: f)

    @property
    def one(self):
        return self.clients[0] if len(self.clients) > 0 else self._dummy

    @property
    def two(self):
        return self.clients[1] if len(self.clients) > 1 else self._dummy

    @property
    def three(self):
        return self.clients[2] if len(self.clients) > 2 else self._dummy

    async def boot_client(self, num: int, session: str):
        """Boot an assistant client and perform initial setup."""
        client = Client(
            name=f"AnonyUB{num}",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            session_string=session,
        )
        await client.start()
        try:
            await client.send_message(config.LOGGER_ID, "Assistant Started")
        except Exception:
            raise SystemExit(f"Assistant {num} failed to send message in log group.")

        client.id = client.me.id
        client.name = client.me.first_name
        client.username = client.me.username
        client.mention = client.me.mention
        self.clients.append(client)
        logger.info(f"Assistant {num} started as @{client.username}")

    async def boot(self):
        for i in (1, 2, 3):
            session = getattr(config, f"SESSION{i}")
            if session:
                await self.boot_client(i, session)

    async def exit(self):
        for client in self.clients:
            await client.stop()
        logger.info("Assistants stopped.")
