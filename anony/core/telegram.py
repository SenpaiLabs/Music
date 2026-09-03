# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic


import asyncio
import os
import time

from pyrogram import types

from anony import config
from anony.helpers import Track, buttons, utils


class Telegram:
    def __init__(self):
        self.active = set()
        self.active_tasks = {}
        self.sleep = 5

    def get_media(self, msg: types.Message) -> bool:
        return bool(msg.video or msg.audio or msg.document or msg.voice)

    async def cancel(self, query: types.CallbackQuery):
        if (task := self.active_tasks.pop(query.message.id, None)) and not task.done():
            task.cancel()
            await query.edit_message_text(
                query.lang["dl_cancel"].format(query.from_user.mention)
            )
        else:
            await query.answer(query.lang["dl_not_found"], show_alert=True)

    async def download(self, msg: types.Message, sent: types.Message) -> Track | None:
        msg_id = sent.id
        start_time = time.time()
        last_edit = 0

        media = msg.audio or msg.voice or msg.video or msg.document
        file_id = getattr(media, "file_unique_id", None)
        file_ext = getattr(media, "file_name", "").split(".")[-1]
        file_size = getattr(media, "file_size", 0)
        file_title = getattr(media, "title", None) or "Telegram File"
        duration = getattr(media, "duration", 0)
        video = bool(getattr(media, "mime_type", "").startswith("video/"))

        if duration > config.DURATION_LIMIT:
            await sent.edit_text(sent.lang["play_duration_limit"].format(config.DURATION_LIMIT // 60))
            return await sent.stop_propagation()

        if file_size > 200 * 1024 * 1024:
            await sent.edit_text(sent.lang["dl_limit"])
            return await sent.stop_propagation()

        async def progress(current, total):
            nonlocal last_edit
            now = time.time()
            if now - last_edit < self.sleep:
                return

            last_edit = now
            percent = current * 100 / total
            speed = current / (now - start_time or 1e-6)
            eta = time.strftime("%H:%M:%S", time.gmtime(int((total - current) / (speed or 1e-6))))
            text = sent.lang["dl_progress"].format(
                utils.format_size(current),
                utils.format_size(total),
                percent,
                utils.format_size(speed),
                eta,
            )

            await sent.edit_text(
                text, reply_markup=buttons.cancel_dl(sent.lang["cancel"])
            )

        try:
            file_path = os.path.abspath(f"downloads/{file_id}.{file_ext}")
            if not os.path.exists(file_path):
                if file_id in self.active:
                    await sent.edit_text(sent.lang["dl_active"])
                    return await sent.stop_propagation()

                self.active.add(file_id)
                task = asyncio.create_task(
                    msg.download(file_name=file_path, progress=progress)
                )
                self.active_tasks[msg_id] = task
                await task
                await sent.edit_text(
                    sent.lang["dl_complete"].format(round(time.time() - start_time, 2))
                )

            return Track(
                id=file_id,
                duration=time.strftime("%M:%S", time.gmtime(duration)),
                duration_sec=duration,
                file_path=file_path,
                message_id=sent.id,
                url=msg.link,
                title=file_title[:25],
                video=video,
            )
        except asyncio.CancelledError:
            return await sent.stop_propagation()
        finally:
            self.active.discard(file_id)
            self.active_tasks.pop(msg_id, None)

    async def process_m3u8(self, url: str, msg_id: int, video: bool) -> Track:
        return Track(
            id=str(msg_id),
            file_path=url,
            message_id=msg_id,
            url=url,
            title="M3U8 Stream",
            video=video,
        )
