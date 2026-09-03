# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic


import asyncio
from random import randint
from time import time

from pymongo import AsyncMongoClient

from anony import config, logger, userbot


class MongoDB:
    def __init__(self):
        """
        Initialize the MongoDB connection.
        """
        self.mongo = AsyncMongoClient(config.MONGO_URL, serverSelectionTimeoutMS=12500)
        self.db = self.mongo.Anon

        self.song_cache_mongo = AsyncMongoClient(config.SONG_CACHE_MONGO_URI, serverSelectionTimeoutMS=12500)
        self.song_cache_db = self.song_cache_mongo.AnonSongCache

        self.admin_list = {}  # {chat_id: (admins, expire_time)}
        self.active_calls = {}
        self.admin_play = set()
        self.autoplay = set()
        self.blacklisted = []
        self.cmd_delete = set()
        self.loop = {}
        self.notified = []
        self.cache = self.db.cache
        self.song_cache = self.song_cache_db.song_cache

        self.assistant = {}
        self.assistantdb = self.db.assistant

        self.auth = {}  # {chat_id: (user_ids_set, expire_time)}
        self.authdb = self.db.auth

        self.chats = []
        self.chatsdb = self.db.chats

        self.lang = {}
        self.langdb = self.db.lang

        self.users = []
        self.usersdb = self.db.users

        self.afkdb = self.db.afk

        self._admin_flusher_task = None

    async def _admin_cache_flusher(self) -> None:
        while True:
            try:
                await asyncio.sleep(900)  # 15 minutes
                for chat_id in list(self.admin_list):
                    try:
                        await self.get_admins(chat_id, reload=True)
                    except Exception:
                        pass
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in admin cache flusher: {e}")

    async def connect(self) -> None:
        """Check if we can connect to the database.

        Raises:
            SystemExit: If the connection to the database fails.
        """
        for client, name in ((self.mongo, "Primary MongoDB"), (self.song_cache_mongo, "Song Cache MongoDB")):
            start = time()
            try:
                await client.admin.command("ping")
                logger.info(f"{name} connected. ({time() - start:.2f}s)")
            except Exception as e:
                logger.error(f"Failed to connect to {name}.")
                raise SystemExit(f"{name} connection failed: {type(e).__name__}") from e

        try:
            await self.load_cache()

            from anony import tasks
            self._admin_flusher_task = asyncio.create_task(self._admin_cache_flusher())
            tasks.append(self._admin_flusher_task)
        except Exception as e:
            raise SystemExit(f"Failed to load cache or start flusher tasks: {type(e).__name__}") from e

    async def close(self) -> None:
        """Close the connection to the database."""
        if self._admin_flusher_task and not self._admin_flusher_task.done():
            self._admin_flusher_task.cancel()

        await self.mongo.close()
        logger.info("Primary MongoDB connection closed.")

        await self.song_cache_mongo.close()
        logger.info("Song Cache MongoDB connection closed.")

    # SONG CACHE METHODS
    async def get_song_cache(self, video_id: str, video: bool) -> dict | None:
        return (
            doc.get("video" if video else "audio")
            if (doc := await self.song_cache.find_one({"_id": video_id}))
            else None
        )

    async def save_song_cache(
        self, video_id: str, video: bool, msg_id: int, file_id: str, title: str, duration: str, duration_sec: int
    ) -> None:
        key = "video" if video else "audio"
        await self.song_cache.update_one(
            {"_id": video_id},
            {
                "$set": {
                    f"{key}.msg_id": msg_id,
                    f"{key}.file_id": file_id,
                    f"{key}.title": title,
                    f"{key}.duration": duration,
                    f"{key}.duration_sec": duration_sec,
                },
                "$setOnInsert": {f"{key}.play_count": 0}
            },
            upsert=True,
        )

    async def increment_play_count(self, video_id: str, video: bool) -> None:
        key = "video" if video else "audio"
        await self.song_cache.update_one(
            {"_id": video_id},
            {"$inc": {f"{key}.play_count": 1}}
        )

    # CACHE
    async def get_call(self, chat_id: int) -> bool:
        return chat_id in self.active_calls

    async def add_call(self, chat_id: int) -> None:
        self.active_calls[chat_id] = 1

    async def remove_call(self, chat_id: int) -> None:
        self.active_calls.pop(chat_id, None)

    async def playing(self, chat_id: int, paused: bool = None) -> bool | None:
        if paused is not None:
            self.active_calls[chat_id] = int(not paused)
        return bool(self.active_calls.get(chat_id, 0))

    async def get_admins(self, chat_id: int, reload: bool = False) -> list[int]:
        from anony.helpers import reload_admins

        cached = self.admin_list.get(chat_id)
        if not cached or reload or time() > cached[1]:
            admins = await reload_admins(chat_id)
            self.admin_list[chat_id] = (admins, time() + 43200)
            return admins
        return cached[0]

    async def get_loop(self, chat_id: int) -> int:
        return self.loop.get(chat_id, 0)

    async def set_loop(self, chat_id: int, count: int) -> None:
        self.loop[chat_id] = count

    # AUTH METHODS
    async def _get_auth(self, chat_id: int) -> set[int]:
        cached = self.auth.get(chat_id)
        if not cached or time() > cached[1]:
            doc = await self.authdb.find_one({"_id": chat_id}) or {}
            users = set(doc.get("user_ids", []))
            self.auth[chat_id] = (users, time() + 43200)
            return users
        return cached[0]

    async def is_auth(self, chat_id: int, user_id: int) -> bool:
        return user_id in await self._get_auth(chat_id)

    async def add_auth(self, chat_id: int, user_id: int) -> None:
        users = await self._get_auth(chat_id)
        if user_id not in users:
            users.add(user_id)
            await self.authdb.update_one(
                {"_id": chat_id}, {"$addToSet": {"user_ids": user_id}}, upsert=True
            )

    async def rm_auth(self, chat_id: int, user_id: int) -> None:
        users = await self._get_auth(chat_id)
        if user_id in users:
            users.discard(user_id)
            await self.authdb.update_one(
                {"_id": chat_id}, {"$pull": {"user_ids": user_id}}
            )

    # ASSISTANT METHODS
    async def set_assistant(self, chat_id: int) -> int:
        num = randint(1, len(userbot.clients))
        await self.assistantdb.update_one(
            {"_id": chat_id},
            {"$set": {"num": num}},
            upsert=True,
        )
        self.assistant[chat_id] = num
        return num

    async def get_assistant(self, chat_id: int):
        from anony import anon

        if chat_id not in self.assistant:
            doc = await self.assistantdb.find_one({"_id": chat_id})
            num = doc["num"] if doc else None

            if not num or num > len(anon.clients):
                num = await self.set_assistant(chat_id)
            self.assistant[chat_id] = num

        return anon.clients[self.assistant[chat_id] - 1]

    async def get_client(self, chat_id: int):
        await self.get_assistant(chat_id)
        return userbot.clients[self.assistant[chat_id] - 1]

    # BLACKLIST METHODS
    async def add_blacklist(self, chat_id: int) -> None:
        is_chat = chat_id < 0
        if is_chat:
            self.blacklisted.append(chat_id)
        doc_id, field = ("bl_chats", "chat_ids") if is_chat else ("bl_users", "user_ids")
        await self.cache.update_one(
            {"_id": doc_id},
            {"$addToSet": {field: chat_id}},
            upsert=True,
        )

    async def del_blacklist(self, chat_id: int) -> None:
        is_chat = chat_id < 0
        if is_chat and chat_id in self.blacklisted:
            self.blacklisted.remove(chat_id)
        doc_id, field = ("bl_chats", "chat_ids") if is_chat else ("bl_users", "user_ids")
        await self.cache.update_one(
            {"_id": doc_id},
            {"$pull": {field: chat_id}},
        )

    async def get_blacklisted(self, chat: bool = False) -> list[int]:
        if chat:
            if not self.blacklisted:
                doc = await self.cache.find_one({"_id": "bl_chats"})
                self.blacklisted.extend(doc.get("chat_ids", []) if doc else [])
            return self.blacklisted
        doc = await self.cache.find_one({"_id": "bl_users"})
        return doc.get("user_ids", []) if doc else []

    # CHAT METHODS
    async def is_chat(self, chat_id: int) -> bool:
        return chat_id in self.chats

    async def add_chat(self, chat_id: int) -> None:
        if chat_id not in self.chats:
            self.chats.append(chat_id)
            await self.chatsdb.insert_one({"_id": chat_id})

    async def rm_chat(self, chat_id: int) -> None:
        if chat_id in self.chats:
            self.chats.remove(chat_id)
            await self.chatsdb.delete_one({"_id": chat_id})

    async def get_chats(self) -> list:
        if not self.chats:
            self.chats = [c["_id"] async for c in self.chatsdb.find()]
        return self.chats

    # COMMAND DELETE
    async def get_cmd_delete(self, chat_id: int) -> bool:
        if chat_id not in self.cmd_delete:
            doc = await self.chatsdb.find_one({"_id": chat_id})
            if doc and doc.get("cmd_delete"):
                self.cmd_delete.add(chat_id)
        return chat_id in self.cmd_delete

    async def set_cmd_delete(self, chat_id: int, delete: bool = False) -> None:
        if delete:
            self.cmd_delete.add(chat_id)
        else:
            self.cmd_delete.discard(chat_id)
        await self.chatsdb.update_one(
            {"_id": chat_id},
            {"$set": {"cmd_delete": delete}},
            upsert=True,
        )

    # LANGUAGE METHODS
    async def set_lang(self, chat_id: int, lang_code: str):
        await self.langdb.update_one(
            {"_id": chat_id},
            {"$set": {"lang": lang_code}},
            upsert=True,
        )
        self.lang[chat_id] = lang_code

    async def get_lang(self, chat_id: int) -> str:
        if chat_id not in self.lang:
            doc = await self.langdb.find_one({"_id": chat_id})
            self.lang[chat_id] = doc["lang"] if doc else config.LANG_CODE
        return self.lang[chat_id]

    # LOGGER METHODS
    async def is_logger(self) -> bool:
        return self.logger

    async def get_logger(self) -> bool:
        doc = await self.cache.find_one({"_id": "logger"})
        self.logger = doc["status"] if doc else True
        return self.logger

    async def set_logger(self, status: bool) -> None:
        self.logger = status
        await self.cache.update_one(
            {"_id": "logger"},
            {"$set": {"status": status}},
            upsert=True,
        )

    # PLAY MODE METHODS
    async def get_play_mode(self, chat_id: int) -> bool:
        if chat_id not in self.admin_play:
            doc = await self.chatsdb.find_one({"_id": chat_id})
            if doc and doc.get("admin_play"):
                self.admin_play.add(chat_id)
        return chat_id in self.admin_play

    async def set_play_mode(self, chat_id: int, remove: bool = False) -> None:
        if remove:
            self.admin_play.discard(chat_id)
        else:
            self.admin_play.add(chat_id)
        await self.chatsdb.update_one(
            {"_id": chat_id},
            {"$set": {"admin_play": not remove}},
            upsert=True,
        )

    # AUTOPLAY METHODS
    async def get_autoplay(self, chat_id: int) -> bool:
        if chat_id not in self.autoplay:
            doc = await self.chatsdb.find_one({"_id": chat_id})
            if doc and doc.get("autoplay"):
                self.autoplay.add(chat_id)
        return chat_id in self.autoplay

    async def set_autoplay(self, chat_id: int, status: bool) -> None:
        if status:
            self.autoplay.add(chat_id)
        else:
            self.autoplay.discard(chat_id)
        await self.chatsdb.update_one(
            {"_id": chat_id},
            {"$set": {"autoplay": status}},
            upsert=True,
        )

    # SUDO METHODS
    async def add_sudo(self, user_id: int) -> None:
        await self.cache.update_one(
            {"_id": "sudoers"}, {"$addToSet": {"user_ids": user_id}}, upsert=True
        )

    async def del_sudo(self, user_id: int) -> None:
        await self.cache.update_one(
            {"_id": "sudoers"}, {"$pull": {"user_ids": user_id}}
        )

    async def get_sudoers(self) -> list[int]:
        doc = await self.cache.find_one({"_id": "sudoers"})
        return doc.get("user_ids", []) if doc else []

    # USER METHODS
    async def is_user(self, user_id: int) -> bool:
        return user_id in self.users

    async def add_user(self, user_id: int) -> None:
        if user_id not in self.users:
            self.users.append(user_id)
            await self.usersdb.insert_one({"_id": user_id})

    async def rm_user(self, user_id: int) -> None:
        if user_id in self.users:
            self.users.remove(user_id)
            await self.usersdb.delete_one({"_id": user_id})

    async def get_users(self) -> list:
        if not self.users:
            self.users = [u["_id"] async for u in self.usersdb.find()]
        return self.users

    # AFK METHODS
    async def add_afk(self, user_id: int, mode: dict) -> None:
        await self.afkdb.update_one(
            {"_id": user_id},
            {"$set": mode},
            upsert=True,
        )

    async def remove_afk(self, user_id: int) -> None:
        await self.afkdb.delete_one({"_id": user_id})

    async def is_afk(self, user_id: int) -> dict | None:
        return await self.afkdb.find_one({"_id": user_id})

    async def load_cache(self) -> None:
        await self.get_chats()
        await self.get_users()
        await self.get_blacklisted(True)
        await self.get_logger()
        logger.info("Database cache loaded.")
