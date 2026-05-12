# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic


import asyncio

from pyrogram import enums, errors, filters, types
from pyrogram.raw.types import UpdateGroupCallParticipants

from anony import anon, app, config, db, lang, queue, tasks, userbot
from anony.helpers import buttons


@app.on_message(filters.video_chat_started, group=19)
@app.on_message(filters.video_chat_ended, group=20)
async def _watcher_vc(_, m: types.Message):
    await anon.stop(m.chat.id)


async def auto_leave():
    while True:
        await asyncio.sleep(3600)
        for ub in userbot.clients:
            try:
                chats = [dialog.chat.id async for dialog in ub.get_dialogs()
                            if dialog.chat.type in [
                                enums.ChatType.GROUP, enums.ChatType.SUPERGROUP,
                            ]][-20:]
                for chat in chats:
                    if chat in [app.logger, -1001686672798, -1001549206010]:
                        continue
                    if chat in db.active_calls:
                        continue
                    await ub.leave_chat(chat)
                    await asyncio.sleep(12)
            except asyncio.CancelledError:
                raise
            except Exception:
                continue


async def track_time():
    while True:
        try:
            await asyncio.sleep(1)
            for chat_id in list(db.active_calls):
                try:
                    if not await db.playing(chat_id):
                        continue
                    media = queue.get_current(chat_id)
                    if not media:
                        continue
                    media.time += 1
                except Exception:
                    continue
        except asyncio.CancelledError:
            break
        except Exception:
            pass





@userbot.one.on_raw_update(group=10)
@userbot.two.on_raw_update(group=10)
@userbot.three.on_raw_update(group=10)
async def _vc_watcher_event(client, update, users, chats):
    if not config.AUTO_END:
        return
    if isinstance(update, UpdateGroupCallParticipants):
        for chat_id, chat in chats.items():
            if not await db.playing(chat_id):
                continue

            media = queue.get_current(chat_id)
            if not media or getattr(media, "time", 0) < 30:
                continue

            # Triggered when participants change. Check if empty.
            is_empty = await anon.is_vc_empty(chat_id)
            if is_empty:
                _lang = await lang.get_lang(chat_id)
                try:
                    await app.edit_message_reply_markup(
                        chat_id=chat_id,
                        message_id=media.message_id,
                        reply_markup=buttons.controls(
                            chat_id=chat_id, status=_lang["stopped"], remove=True
                        ),
                    )
                except errors.MessageIdInvalid:
                    pass
                except Exception:
                    pass

                await anon.stop(chat_id)
                try:
                    await app.send_message(chat_id=chat_id, text=_lang["auto_left"])
                except Exception:
                    pass


if config.AUTO_LEAVE:
    tasks.append(asyncio.create_task(auto_leave()))
tasks.append(asyncio.create_task(track_time()))

