# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic


from pyrogram import Client

from anony import config, logger


class Userbot:
    def __init__(self):
        self.clients: list[Client] = []
        dummy = type("Dummy", (), {"on_raw_update": lambda *a, **k: lambda f: f})()
        self.one = self.two = self.three = dummy

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

        client.id, client.name, client.username, client.mention = (
            client.me.id,
            client.me.first_name,
            client.me.username,
            client.me.mention,
        )
        self.clients.append(client)
        if 1 <= num <= 3:
            setattr(self, ("one", "two", "three")[num - 1], client)
        logger.info(f"Assistant {num} started as @{client.username}")

    async def boot(self):
        for i in (1, 2, 3):
            if s := getattr(config, f"SESSION{i}", None):
                await self.boot_client(i, s)

    async def exit(self):
        for client in self.clients:
            await client.stop()
        logger.info("Assistants stopped.")
