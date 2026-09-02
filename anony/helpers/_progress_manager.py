# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic

import asyncio
import logging
import random
import time
from pyrogram.errors import MessageNotModified, MessageIdInvalid, FloodWait
from anony.helpers import buttons

class RateLimiter:
    def __init__(self, max_edits_per_sec=20):
        self.max_edits_per_sec = max_edits_per_sec
        self.edits = 0
        self.last_reset = time.time()
        self.lock = asyncio.Lock()

    async def acquire(self):
        while True:
            async with self.lock:
                now = time.time()
                if now - self.last_reset >= 1.0:
                    self.edits = 0
                    self.last_reset = now
                
                if self.edits < self.max_edits_per_sec:
                    self.edits += 1
                    return
            await asyncio.sleep(0.1)

rate_limiter = RateLimiter()


class ProgressManager:
    def __init__(self):
        self.active_chats = {} # chat_id -> asyncio.Task

    def register(self, chat_id: int):
        self.deregister(chat_id)
        self.active_chats[chat_id] = asyncio.create_task(self._chat_loop(chat_id))

    def deregister(self, chat_id: int):
        if chat_id in self.active_chats:
            self.active_chats[chat_id].cancel()
            del self.active_chats[chat_id]

    async def close_message(self, chat_id: int, media):
        if not media or not getattr(media, "message_id", 0):
            return

        from anony import app

        played = getattr(media, "time", 0)
        duration = getattr(media, "duration_sec", 0)

        pos = min(int((played / duration) * 10), 9) if duration > 0 else 0
        bar = "—" * pos + "◉" + "—" * (9 - pos)
        timer = bar

        try:
            await rate_limiter.acquire()
            await app.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=media.message_id,
                reply_markup=buttons.controls(
                    chat_id=chat_id, timer=timer, autoplay=None, remove=True
                )
            )
        except MessageNotModified:
            pass
        except FloodWait as e:
            await asyncio.sleep(e.value)
        except Exception:
            pass

    async def _chat_loop(self, chat_id: int):
        from anony import app, db, lang, queue, yt
        
        last_text = ""
        
        try:
            while True:
                await asyncio.sleep(random.uniform(4.0, 7.0))

                if not await db.playing(chat_id):
                    continue

                media = queue.get_current(chat_id)
                if not media or not media.message_id or not media.duration_sec or not media.time:
                    continue

                played = media.time
                duration = media.duration_sec
                remaining = max(duration - played, 0)

                if remaining <= 30:
                    next_track = queue.get_next(chat_id, check=True)
                    if next_track and not next_track.file_path:
                        if not getattr(next_track, "download_task", None) or next_track.download_task.done():
                            next_track.download_task = asyncio.create_task(yt.download(next_track.id, video=next_track.video))
                        next_track.file_path = "downloading"

                if remaining < 10:
                    continue

                _lang = await lang.get_lang(chat_id)
                status = await db.get_autoplay(chat_id)
                autoplay = _lang.get("autoplay_btn", "Autoplay: {}").format(
                    _lang.get("on", "On") if status else _lang.get("off", "Off")
                )

                text = _lang["play_media"].format(
                    media.url,
                    media.title,
                    f"{time.strftime('%M:%S', time.gmtime(played))} / {media.duration}",
                    media.user,
                )
                
                if text == last_text:
                    continue
                
                markup = buttons.controls(
                    chat_id=chat_id, timer=None, autoplay=autoplay, remove=False
                )

                await rate_limiter.acquire()

                try:
                    await app.edit_message_text(
                        chat_id=chat_id,
                        message_id=media.message_id,
                        text=text,
                        reply_markup=markup,
                        disable_web_page_preview=True
                    )
                    last_text = text
                except MessageNotModified:
                    last_text = text
                except MessageIdInvalid:
                    self.deregister(chat_id)
                    return
                except FloodWait as e:
                    await asyncio.sleep(e.value)
                except Exception:
                    await rate_limiter.acquire()
                    try:
                        await app.edit_message_caption(
                            chat_id=chat_id,
                            message_id=media.message_id,
                            caption=text,
                            reply_markup=markup,
                        )
                        last_text = text
                    except MessageNotModified:
                        last_text = text
                    except MessageIdInvalid:
                        self.deregister(chat_id)
                        return
                    except FloodWait as e:
                        await asyncio.sleep(e.value)
                    except Exception:
                        pass

        except asyncio.CancelledError:
            pass
        except Exception:
            logging.exception("Unexpected error in progress loop")

    async def stop_workers(self):
        """Gracefully stop all chat loops."""
        for chat_id in list(self.active_chats):
            self.deregister(chat_id)

progress_manager = ProgressManager()
