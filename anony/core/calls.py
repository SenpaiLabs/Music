# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic


import asyncio

from ntgcalls import (ConnectionNotFound, TelegramServerError,
                      RTMPStreamingUnsupported, ConnectionError)
from pyrogram import errors
from pyrogram.errors import (ChatSendMediaForbidden, ChatSendPhotosForbidden,
                             MessageIdInvalid)
from pyrogram.raw import functions
from pyrogram.raw import types as raw_types
from pyrogram.types import InputMediaPhoto, Message
from pytgcalls import PyTgCalls, exceptions, types
from pytgcalls.pytgcalls_session import PyTgCallsSession

from anony import (app, config, db, lang, logger,
                   queue, thumb, userbot, yt)
from anony.helpers import Media, Track, buttons


class TgCall(PyTgCalls):
    def __init__(self):
        self.clients = []

    async def pause(self, chat_id: int) -> bool:
        client = await db.get_assistant(chat_id)
        await db.playing(chat_id, paused=True)
        return await client.pause(chat_id)

    async def resume(self, chat_id: int) -> bool:
        client = await db.get_assistant(chat_id)
        await db.playing(chat_id, paused=False)
        return await client.resume(chat_id)

    async def stop(self, chat_id: int) -> None:
        client = await db.get_assistant(chat_id)
        current = queue.get_current(chat_id)
        if config.DB_CHANNEL and current and getattr(current, "file_path", None):
            import os
            if os.path.isfile(current.file_path):
                try: os.remove(current.file_path)
                except Exception: pass
        queue.clear(chat_id)
        await db.remove_call(chat_id)
        await db.set_loop(chat_id, 0)

        try:
            await client.leave_call(chat_id, close=False)
        except Exception:
            pass


    MAX_SKIP_ATTEMPTS = 5

    async def play_media(
        self,
        chat_id: int,
        message: Message,
        media: Media | Track,
        seek_time: int = 0,
        attempt: int = 0,
    ) -> None:
        client = await db.get_assistant(chat_id)
        _lang = await lang.get_lang(chat_id)
        _thumb = (
            await thumb.generate(media)
            if isinstance(media, Track)
            else config.DEFAULT_THUMB
        ) if config.THUMB_GEN else None

        if not media.file_path:
            await message.edit_text(_lang["error_no_file"].format(config.SUPPORT_CHAT))
            if attempt >= self.MAX_SKIP_ATTEMPTS:
                logger.warning(f"Too many consecutive failures in {chat_id}, stopping.")
                return await self.stop(chat_id)
            return await self.play_next(chat_id, attempt=attempt + 1)

        stream = types.MediaStream(
            media_path=media.file_path,
            audio_parameters=types.AudioQuality.HIGH,
            video_parameters=types.VideoQuality.HD_720p,
            audio_flags=types.MediaStream.Flags.REQUIRED,
            video_flags=(
                types.MediaStream.Flags.AUTO_DETECT
                if media.video
                else types.MediaStream.Flags.IGNORE
            ),
            ffmpeg_parameters=f"-ss {seek_time}" if seek_time > 1 else None,
        )
        try:
            try:
                await client.play(
                    chat_id=chat_id,
                    stream=stream,
                    config=types.GroupCallConfig(auto_start=False),
                )
            except errors.FloodWait as fw:
                logger.warning(f"FloodWait on JoinGroupCall: sleeping {fw.value}s (chat {chat_id})")
                await asyncio.sleep(fw.value)
                await client.play(
                    chat_id=chat_id,
                    stream=stream,
                    config=types.GroupCallConfig(auto_start=False),
                )
            if not seek_time:
                media.time = 1
                await db.add_call(chat_id)
                text = _lang["play_media"].format(
                    media.url,
                    media.title,
                    media.duration,
                    media.user,
                )
                keyboard = buttons.controls(chat_id)
                try:
                    if _thumb:
                        await message.edit_media(
                            media=InputMediaPhoto(
                                media=_thumb,
                                caption=text,
                            ),
                            reply_markup=keyboard,
                        )
                    else:
                        await message.edit_text(text, reply_markup=keyboard)
                except (ChatSendMediaForbidden, ChatSendPhotosForbidden, MessageIdInvalid):
                    if _thumb:
                        sent = await app.send_photo(
                            chat_id=chat_id,
                            photo=_thumb,
                            caption=text,
                            reply_markup=keyboard,
                        )
                    else:
                        sent = await app.send_message(
                            chat_id=chat_id,
                            text=text,
                            reply_markup=keyboard,
                        )
                    media.message_id = sent.id
        except FileNotFoundError:
            await message.edit_text(_lang["error_no_file"].format(config.SUPPORT_CHAT))
            if attempt >= self.MAX_SKIP_ATTEMPTS:
                logger.warning(f"Too many consecutive failures in {chat_id}, stopping.")
                return await self.stop(chat_id)
            await self.play_next(chat_id, attempt=attempt + 1)
        except ProcessLookupError as ex:
            logger.warning(f"Stream probe failed for {media.file_path}: {ex}")
            await message.edit_text(_lang["error_no_file"].format(config.SUPPORT_CHAT))
            if attempt >= self.MAX_SKIP_ATTEMPTS:
                logger.warning(f"Too many consecutive failures in {chat_id}, stopping.")
                return await self.stop(chat_id)
            await self.play_next(chat_id, attempt=attempt + 1)
        except exceptions.NoActiveGroupCall:
            await self.stop(chat_id)
            await message.edit_text(_lang["error_no_call"])
        except exceptions.NoAudioSourceFound:
            await message.edit_text(_lang["error_no_audio"])
            if attempt >= self.MAX_SKIP_ATTEMPTS:
                logger.warning(f"Too many consecutive failures in {chat_id}, stopping.")
                return await self.stop(chat_id)
            await self.play_next(chat_id, attempt=attempt + 1)
        except (ConnectionError, ConnectionNotFound, TelegramServerError):
            await self.stop(chat_id)
            await message.edit_text(_lang["error_tg_server"])
        except RTMPStreamingUnsupported:
            await self.stop(chat_id)
            await message.edit_text(_lang["error_rtmp"])


    async def is_vc_empty(self, chat_id: int) -> bool:
        client = await db.get_client(chat_id)
        assistant_id = client.me.id

        try:
            peer = await client.resolve_peer(chat_id)
            if isinstance(peer, raw_types.InputPeerChannel):
                full = await client.invoke(functions.channels.GetFullChannel(channel=peer))
            elif isinstance(peer, raw_types.InputPeerChat):
                full = await client.invoke(functions.messages.GetFullChat(chat_id=peer.chat_id))
            else:
                return False

            input_call = full.full_chat.call
            if not input_call:
                return True

            result = await client.invoke(
                functions.phone.GetGroupParticipants(
                    call=input_call, ids=[], sources=[], offset="", limit=100
                )
            )
            real_users = [
                p for p in result.participants
                if getattr(p.peer, "user_id", None) not in (assistant_id, None)
            ]
            return len(real_users) == 0
        except Exception:
            return False


    async def replay(self, chat_id: int) -> None:
        if not await db.get_call(chat_id):
            return

        media = queue.get_current(chat_id)
        _lang = await lang.get_lang(chat_id)
        msg = await app.send_message(chat_id=chat_id, text=_lang["play_again"])
        media.message_id = msg.id
        await self.play_media(chat_id, msg, media)


    async def play_next(self, chat_id: int, attempt: int = 0) -> None:
        if loop := await db.get_loop(chat_id):
            await db.set_loop(chat_id, loop - 1)
            return await self.replay(chat_id)

        last_track = queue.get_current(chat_id)
        if config.DB_CHANNEL and last_track and getattr(last_track, "file_path", None):
            import os
            if os.path.isfile(last_track.file_path):
                try: os.remove(last_track.file_path)
                except Exception: pass
        media = queue.get_next(chat_id)
        try:
            if media and media.message_id:
                await app.delete_messages(
                    chat_id=chat_id,
                    message_ids=media.message_id,
                    revoke=True,
                )
                media.message_id = 0
        except Exception as e:
            logger.warning(f"Failed to delete message in {chat_id}: {e}")

        if not media:
            if last_track and await db.get_autoplay(chat_id):
                if await self.is_vc_empty(chat_id):
                    _lang = await lang.get_lang(chat_id)
                    await self.stop(chat_id)
                    try:
                        await app.send_message(chat_id=chat_id, text=_lang["auto_left"])
                    except Exception:
                        pass
                    return
                else:
                    queue.add_history(chat_id, last_track.id)
                    media = await yt.autoplay(
                        last_track.id,
                        queue.get_history(chat_id),
                        video=getattr(last_track, "video", False),
                    )
                    if media:
                        media.user = "Autoplay"
                        queue.add(chat_id, media)

            if not media:
                return await self.stop(chat_id)

        _lang = await lang.get_lang(chat_id)
        msg = await app.send_message(chat_id=chat_id, text=_lang["play_next"])
        if not media.file_path:
            media.file_path = await yt.download(
                media.id,
                video=media.video,
                title=getattr(media, "title", ""),
                duration=getattr(media, "duration", ""),
                duration_sec=getattr(media, "duration_sec", 0)
            )
            if not media.file_path:
                await msg.edit_text(
                    _lang["error_no_file"].format(config.SUPPORT_CHAT)
                )
                if attempt >= self.MAX_SKIP_ATTEMPTS:
                    logger.warning(f"Too many consecutive failures in {chat_id}, stopping.")
                    return await self.stop(chat_id)
                return await self.play_next(chat_id, attempt=attempt + 1)

        media.message_id = msg.id
        await self.play_media(chat_id, msg, media, attempt=attempt)


    async def ping(self) -> float:
        pings = [client.ping for client in self.clients]
        return round(sum(pings) / len(pings), 2)


    async def decorators(self, client: PyTgCalls) -> None:
        @client.on_update()
        async def update_handler(_, update: types.Update) -> None:
            if isinstance(update, types.StreamEnded):
                if update.stream_type == types.StreamEnded.Type.AUDIO:
                    await self.play_next(update.chat_id)
            elif isinstance(update, types.ChatUpdate):
                if update.status in [
                    types.ChatUpdate.Status.KICKED,
                    types.ChatUpdate.Status.LEFT_GROUP,
                    types.ChatUpdate.Status.CLOSED_VOICE_CHAT,
                ]:
                    await self.stop(update.chat_id)


    async def boot(self) -> None:
        PyTgCallsSession.notice_displayed = True
        for ub in userbot.clients:
            client = PyTgCalls(ub, cache_duration=100)
            await client.start()
            self.clients.append(client)
            await self.decorators(client)
        logger.info("PyTgCalls client(s) started.")


