# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic

import asyncio
import random
import time
from pyrogram.errors import MessageNotModified, MessageIdInvalid, FloodWait
from anony.helpers import buttons

class TokenBucket:
    def __init__(self, capacity: int, fill_rate: float):
        self.capacity = float(capacity)
        self._tokens = float(capacity)
        self.fill_rate = float(fill_rate)
        self.last_sync = time.monotonic()
        self._lock = asyncio.Lock()

    async def consume(self, tokens: int = 1):
        async with self._lock:
            while True:
                now = time.monotonic()
                elapsed = now - self.last_sync
                self._tokens = min(self.capacity, self._tokens + elapsed * self.fill_rate)
                self.last_sync = now

                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return

                # Wait until enough tokens are available
                wait_time = (tokens - self._tokens) / self.fill_rate
                await asyncio.sleep(wait_time)


class ProgressManager:
    def __init__(self):
        # 30 edits per second maximum
        self.rate_limiter = TokenBucket(capacity=30, fill_rate=30.0)
        self.queue = asyncio.Queue()
        self.active_chats = {} # chat_id -> asyncio.Task (loop task)
        self.pending_edits = {} # chat_id -> remaining_time (deduplication)
        self.workers = []
        self.is_running = False

    def start_workers(self, num_workers=5):
        if not self.is_running:
            self.is_running = True
            for _ in range(num_workers):
                self.workers.append(asyncio.create_task(self._worker_loop()))

    async def _worker_loop(self):
        while self.is_running:
            try:
                chat_id, remaining_time, timer, needs_autoplay, played = await self.queue.get()

                # Backpressure: If this isn't the latest queued update for this chat, drop it.
                if self.pending_edits.get(chat_id) != remaining_time:
                    self.queue.task_done()
                    continue

                # Clear pending status since we are processing it
                if chat_id in self.pending_edits:
                    del self.pending_edits[chat_id]

                from anony import app, db, lang, queue

                # Check if chat is still active and playing
                if not await db.playing(chat_id):
                    self.queue.task_done()
                    continue

                media = queue.get_current(chat_id)
                if not media or not media.message_id:
                    self.queue.task_done()
                    continue

                # Token bucket consume (Rate Limiting)
                await self.rate_limiter.consume(1)

                autoplay = None
                if needs_autoplay:
                    _lang = await lang.get_lang(chat_id)
                    status = await db.get_autoplay(chat_id)
                    autoplay = _lang.get("autoplay_btn", "Autoplay: {}").format(
                        _lang.get("on", "On") if status else _lang.get("off", "Off")
                    )

                try:
                    from anony import config
                    if config.THUMB_GEN:
                        await app.edit_message_reply_markup(
                            chat_id=chat_id,
                            message_id=media.message_id,
                            reply_markup=buttons.controls(
                                chat_id=chat_id, timer=timer, autoplay=autoplay, remove=False
                            )
                        )
                    else:
                        text = _lang["play_media"].format(
                            media.url,
                            media.title,
                            f"{time.strftime('%M:%S', time.gmtime(played))} / {media.duration}",
                            media.user,
                        )
                        markup = buttons.controls(
                            chat_id=chat_id, timer=None, autoplay=autoplay, remove=False
                        )
                        try:
                            await app.edit_message_text(
                                chat_id=chat_id,
                                message_id=media.message_id,
                                text=text,
                                reply_markup=markup,
                                disable_web_page_preview=True
                            )
                        except Exception:
                            await app.edit_message_caption(
                                chat_id=chat_id,
                                message_id=media.message_id,
                                caption=text,
                                reply_markup=markup,
                            )
                except MessageNotModified:
                    pass
                except MessageIdInvalid:
                    # Message deleted, stop tracking
                    self.deregister(chat_id)
                except FloodWait as e:
                    # Circuit breaker
                    await asyncio.sleep(e.value)

                self.queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception:
                pass

    def register(self, chat_id: int):
        self.start_workers()
        self.deregister(chat_id)
        # Start the generator loop for this chat
        self.active_chats[chat_id] = asyncio.create_task(self._chat_loop(chat_id))

    def deregister(self, chat_id: int):
        if chat_id in self.active_chats:
            self.active_chats[chat_id].cancel()
            del self.active_chats[chat_id]
        if chat_id in self.pending_edits:
            del self.pending_edits[chat_id]

    async def close_message(self, chat_id: int, media):
        if not media or not getattr(media, "message_id", 0):
            return

        from anony import app
        from anony.helpers import buttons

        played = getattr(media, "time", 0)
        duration = getattr(media, "duration_sec", 0)

        pos = min(int((played / duration) * 10), 9) if duration > 0 else 0
        bar = "—" * pos + "◉" + "—" * (9 - pos)
        timer = bar

        try:
            await app.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=media.message_id,
                reply_markup=buttons.controls(
                    chat_id=chat_id, timer=timer, autoplay=None, remove=True
                )
            )
        except Exception:
            pass

    async def _chat_loop(self, chat_id: int):
        try:
            while True:
                # Jittered interval 4-7 seconds
                await asyncio.sleep(random.uniform(4.0, 7.0))

                from anony import db, queue

                if not await db.playing(chat_id):
                    continue

                media = queue.get_current(chat_id)
                if not media or not media.duration_sec or not media.time:
                    continue

                played = media.time
                duration = media.duration_sec
                remaining = max(duration - played, 0)

                if remaining <= 30:
                    next_track = queue.get_next(chat_id, check=True)
                    if next_track and not next_track.file_path:
                        from anony import yt
                        if not getattr(next_track, "download_task", None) or next_track.download_task.done():
                            next_track.download_task = asyncio.create_task(yt.download(next_track.id, video=next_track.video))
                        next_track.file_path = "downloading"

                if remaining < 10:
                    continue # handled by remove=True in main update loop or stop

                from anony import config
                if config.THUMB_GEN:
                    pos = min(int((played / duration) * 10), 9)
                    bar = "—" * pos + "◉" + "—" * (9 - pos)
                    timer = f"{time.strftime('%M:%S', time.gmtime(played))} | {bar} | -{time.strftime('%M:%S', time.gmtime(remaining))}"
                    needs_autoplay = False
                else:
                    timer = None
                    needs_autoplay = True

                self.pending_edits[chat_id] = remaining
                await self.queue.put((chat_id, remaining, timer, needs_autoplay, played))

        except asyncio.CancelledError:
            pass
        except Exception:
            pass

    async def stop_workers(self):
        """Gracefully stop all workers and flush pending edits"""
        self.is_running = False

        # Cancel all active chat loops
        for chat_id in list(self.active_chats):
            self.deregister(chat_id)

        # Cancel all workers
        for worker in self.workers:
            worker.cancel()

        if self.workers:
            await asyncio.gather(*self.workers, return_exceptions=True)
        self.workers.clear()

progress_manager = ProgressManager()
