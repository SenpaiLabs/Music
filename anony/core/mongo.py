# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic


from datetime import datetime, timezone
from random import randint
from time import time

from pymongo import AsyncMongoClient, UpdateOne
from cachetools import TTLCache

from anony import config, logger, userbot


class MongoDB:
    def __init__(self):
        """
        Initialize the MongoDB connection.
        """
        self.mongo = AsyncMongoClient(config.MONGO_URL, serverSelectionTimeoutMS=12500)
        self.db = self.mongo.Anon

        self.admin_list = TTLCache(maxsize=100000, ttl=43200)  # 12h TTL
        self.active_calls = {}
        self.admin_play = []
        self.autoplay = []
        self.blacklisted = []
        self.cmd_delete = []
        self.loop = {}
        self.notified = []
        self.cache = self.db.cache
        self.song_cache = self.db.song_cache

        self.assistant = {}
        self.assistantdb = self.db.assistant

        self.auth = TTLCache(maxsize=100000, ttl=43200)  # 12h TTL
        self.authdb = self.db.auth

        self.chats = []
        self.chatsdb = self.db.chats

        self.lang = {}
        self.langdb = self.db.lang

        self.userstatsdb = self.db.user_stats
        self.chatstatsdb = self.db.chat_stats

        self.users = []
        self.usersdb = self.db.users

        self.afkdb = self.db.afk

        self._stats_buffer = {"users": {}, "chats": {}}
        self._flusher_task = None
        self._admin_flusher_task = None

    async def _admin_cache_flusher(self) -> None:
        import asyncio
        while True:
            try:
                await asyncio.sleep(900)  # 15 minutes
                for chat_id in list(self.admin_list.keys()):
                    try:
                        await self.get_admins(chat_id, reload=True)
                    except Exception:
                        pass
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in admin cache flusher: {e}")

    async def _stats_flusher(self) -> None:
        import asyncio
        while True:
            try:
                await asyncio.sleep(60)
                await self.flush_stats()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in DB stats flusher: {e}")

    async def flush_stats(self) -> None:
        buffer = self._stats_buffer
        self._stats_buffer = {"users": {}, "chats": {}}

        if not buffer["users"] and not buffer["chats"]:
            return

        user_updates = [
            UpdateOne(
                {"_id": _id},
                {"$inc": {"count": data["count"]}, "$set": data["set"]},
                upsert=True
            ) for _id, data in buffer["users"].items()
        ]

        chat_updates = [
            UpdateOne(
                {"_id": _id},
                {"$inc": {"count": data["count"]}, "$set": data["set"]},
                upsert=True
            ) for _id, data in buffer["chats"].items()
        ]

        if user_updates:
            try:
                await self.userstatsdb.bulk_write(user_updates)
            except Exception as e:
                logger.error(f"Error in userstatsdb bulk_write: {e}")

        if chat_updates:
            try:
                await self.chatstatsdb.bulk_write(chat_updates)
            except Exception as e:
                logger.error(f"Error in chatstatsdb bulk_write: {e}")

    async def connect(self) -> None:
        """Check if we can connect to the database.

        Raises:
            SystemExit: If the connection to the database fails.
        """
        try:
            start = time()
            await self.mongo.admin.command("ping")
            logger.info(f"Database connection successful. ({time() - start:.2f}s)")
            await self.load_cache()

            import asyncio
            from anony import tasks
            self._flusher_task = asyncio.create_task(self._stats_flusher())
            self._admin_flusher_task = asyncio.create_task(self._admin_cache_flusher())
            tasks.append(self._flusher_task)
            tasks.append(self._admin_flusher_task)
        except Exception as e:
            raise SystemExit(f"Database connection failed: {type(e).__name__}") from e

    async def close(self) -> None:
        """Close the connection to the database."""
        await self.flush_stats()
        if self._flusher_task and not self._flusher_task.done():
            self._flusher_task.cancel()
        if self._admin_flusher_task and not self._admin_flusher_task.done():
            self._admin_flusher_task.cancel()

        await self.mongo.close()
        logger.info("Database connection closed.")

    # SONG CACHE METHODS
    async def get_song_cache(self, video_id: str, video: bool) -> dict | None:
        doc = await self.song_cache.find_one({"_id": video_id})
        if doc:
            key = "video" if video else "audio"
            return doc.get(key)
        return None

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

    async def get_top_songs(self, limit: int = 10) -> list:
        pipeline = [
            {
                "$addFields": {
                    "total_plays": {
                        "$add": [
                            {"$ifNull": ["$audio.play_count", 0]},
                            {"$ifNull": ["$video.play_count", 0]}
                        ]
                    }
                }
            },
            {"$sort": {"total_plays": -1}},
            {"$limit": limit}
        ]
        cursor = await self.song_cache.aggregate(pipeline)
        return [doc async for doc in cursor]

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
        from anony.core.admins import reload_admins

        if chat_id not in self.admin_list or reload:
            self.admin_list[chat_id] = await reload_admins(chat_id)
        return self.admin_list[chat_id]

    async def get_loop(self, chat_id: int) -> int:
        return self.loop.get(chat_id, 0)

    async def set_loop(self, chat_id: int, count: int) -> None:
        self.loop[chat_id] = count

    # AUTH METHODS
    async def _get_auth(self, chat_id: int) -> set[int]:
        if chat_id not in self.auth:
            doc = await self.authdb.find_one({"_id": chat_id}) or {}
            self.auth[chat_id] = set(doc.get("user_ids", []))
        return self.auth[chat_id]

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
        if chat_id not in self.assistant:
            await self.get_assistant(chat_id)

        num = self.assistant[chat_id]
        if num > len(userbot.clients):
            num = await self.set_assistant(chat_id)
            self.assistant[chat_id] = num

        return {1: userbot.one, 2: userbot.two, 3: userbot.three}.get(num)

    # BLACKLIST METHODS
    async def add_blacklist(self, chat_id: int) -> None:
        if str(chat_id).startswith("-"):
            self.blacklisted.append(chat_id)
            return await self.cache.update_one(
                {"_id": "bl_chats"},
                {"$addToSet": {"chat_ids": chat_id}},
                upsert=True,
            )
        await self.cache.update_one(
            {"_id": "bl_users"},
            {"$addToSet": {"user_ids": chat_id}},
            upsert=True,
        )

    async def del_blacklist(self, chat_id: int) -> None:
        if str(chat_id).startswith("-"):
            self.blacklisted.remove(chat_id)
            return await self.cache.update_one(
                {"_id": "bl_chats"},
                {"$pull": {"chat_ids": chat_id}},
            )
        await self.cache.update_one(
            {"_id": "bl_users"},
            {"$pull": {"user_ids": chat_id}},
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
        if not await self.is_chat(chat_id):
            self.chats.append(chat_id)
            await self.chatsdb.insert_one({"_id": chat_id})

    async def rm_chat(self, chat_id: int) -> None:
        if await self.is_chat(chat_id):
            self.chats.remove(chat_id)
            await self.chatsdb.delete_one({"_id": chat_id})

    async def get_chats(self) -> list:
        if not self.chats:
            self.chats.extend([chat["_id"] async for chat in self.chatsdb.find()])
        return self.chats

    # COMMAND DELETE
    async def get_cmd_delete(self, chat_id: int) -> bool:
        if chat_id not in self.cmd_delete:
            doc = await self.chatsdb.find_one({"_id": chat_id})
            if doc and doc.get("cmd_delete"):
                self.cmd_delete.append(chat_id)
        return chat_id in self.cmd_delete

    async def set_cmd_delete(self, chat_id: int, delete: bool = False) -> None:
        if delete:
            self.cmd_delete.append(chat_id)
        else:
            self.cmd_delete.remove(chat_id)
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
        if doc:
            self.logger = doc["status"]
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
                self.admin_play.append(chat_id)
        return chat_id in self.admin_play

    async def set_play_mode(self, chat_id: int, remove: bool = False) -> None:
        if remove and chat_id in self.admin_play:
            self.admin_play.remove(chat_id)
        else:
            self.admin_play.append(chat_id)
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
                self.autoplay.append(chat_id)
        return chat_id in self.autoplay

    async def set_autoplay(self, chat_id: int, status: bool) -> None:
        if status and chat_id not in self.autoplay:
            self.autoplay.append(chat_id)
        elif not status and chat_id in self.autoplay:
            self.autoplay.remove(chat_id)
        await self.chatsdb.update_one(
            {"_id": chat_id},
            {"$set": {"autoplay": status}},
            upsert=True,
        )

    # LEADERBOARD METHODS
    async def add_play(
        self, chat_id: int, user_id: int, name: str = None, chat_title: str = None
    ) -> None:
        now = datetime.now(timezone.utc)
        day = now.strftime("%Y-%m-%d")
        week = now.strftime("%G-W%V")

        user_id_str = f"{chat_id}:{user_id}:{day}"
        if user_id_str not in self._stats_buffer["users"]:
            self._stats_buffer["users"][user_id_str] = {
                "count": 0,
                "set": {
                    "chat_id": chat_id,
                    "user_id": user_id,
                    "day": day,
                    "week": week,
                }
            }

        self._stats_buffer["users"][user_id_str]["count"] += 1
        if name:
            self._stats_buffer["users"][user_id_str]["set"]["name"] = name

        chat_id_str = f"{chat_id}:{day}"
        if chat_id_str not in self._stats_buffer["chats"]:
            self._stats_buffer["chats"][chat_id_str] = {
                "count": 0,
                "set": {
                    "chat_id": chat_id,
                    "day": day,
                    "week": week,
                }
            }

        self._stats_buffer["chats"][chat_id_str]["count"] += 1
        if chat_title:
            self._stats_buffer["chats"][chat_id_str]["set"]["title"] = chat_title

    async def get_top_users(self, chat_id: int, period: str) -> list[dict]:
        match = {"chat_id": chat_id}
        if period == "daily":
            match["day"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        elif period == "weekly":
            match["week"] = datetime.now(timezone.utc).strftime("%G-W%V")

        pipeline = [
            {"$match": match},
            {"$sort": {"day": 1}},
            {
                "$group": {
                    "_id": "$user_id",
                    "count": {"$sum": "$count"},
                    "name": {"$last": "$name"},
                }
            },
            {"$sort": {"count": -1}},
            {"$limit": 10},
        ]
        cursor = await self.userstatsdb.aggregate(pipeline)
        return [doc async for doc in cursor]

    async def get_top_chats(self) -> list[dict]:
        pipeline = [
            {"$sort": {"day": 1}},
            {
                "$group": {
                    "_id": "$chat_id",
                    "count": {"$sum": "$count"},
                    "title": {"$last": "$title"},
                }
            },
            {"$sort": {"count": -1}},
            {"$limit": 10},
        ]
        cursor = await self.chatstatsdb.aggregate(pipeline)
        return [doc async for doc in cursor]

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
        if not await self.is_user(user_id):
            self.users.append(user_id)
            await self.usersdb.insert_one({"_id": user_id})

    async def rm_user(self, user_id: int) -> None:
        if await self.is_user(user_id):
            self.users.remove(user_id)
            await self.usersdb.delete_one({"_id": user_id})

    async def get_users(self) -> list:
        if not self.users:
            self.users.extend([user["_id"] async for user in self.usersdb.find()])
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



    async def migrate_coll(self) -> None:
        logger.info("Migrating users and chats from old collections...")

        users, musers, mchats = [], [], []
        seen_chats, seen_users = set(), set()
        users.extend([user async for user in self.usersdb.find()])
        users.extend([user async for user in self.db.tgusersdb.find()])

        for user in users:
            _id = user.get("_id")
            if isinstance(_id, int):
                user_id = _id
            else:
                user_id = int(user.get("user_id"))

            if user_id in seen_users:
                continue
            seen_users.add(user_id)
            musers.append({"_id": user_id})

        await self.usersdb.drop()
        await self.db.tgusersdb.drop()
        if musers:
            await self.usersdb.insert_many(musers)

        async for chat in self.chatsdb.find():
            _id = chat.get("_id")
            if isinstance(_id, int):
                chat_id = _id
            else:
                chat_id = int(chat.get("chat_id"))

            if chat_id in seen_chats:
                continue
            seen_chats.add(chat_id)
            mchats.append({"_id": chat_id})

        await self.chatsdb.drop()
        if mchats:
            await self.chatsdb.insert_many(mchats)

        await self.cache.insert_one({"_id": "migrated"})
        logger.info("Migration completed successfully.")

    async def load_cache(self) -> None:
        doc = await self.cache.find_one({"_id": "migrated"})
        if not doc:
            await self.migrate_coll()

        await self.get_chats()
        await self.get_users()
        await self.get_blacklisted(True)
        await self.get_logger()
        logger.info("Database cache loaded.")

