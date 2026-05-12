# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic


import os
from pathlib import Path

from pyrogram import errors, filters, types

from anony import anon, app, config, db, lang, queue, tg, yt
from anony.helpers import buttons, utils
from anony.helpers._play import checkUB


def playlist_to_queue(chat_id: int, tracks: list) -> str:
    text = "<blockquote expandable>"
    for track in tracks:
        pos = queue.add(chat_id, track)
        text += f"<b>{pos}.</b> {track.title}\n"
    text = text[:1948] + "</blockquote>"
    return text

async def safe_edit(msg: types.Message, *args, **kwargs):
    try:
        return await msg.edit_text(*args, **kwargs)
    except (errors.MessageDeleted, errors.MessageIdInvalid):
        pass


@app.on_message(
    filters.command(["play", "playforce", "vplay", "vplayforce"])
    & filters.group
    & ~app.bl_users
)
@lang.language()
@checkUB
async def play_hndlr(
    _,
    m: types.Message,
    force: bool = False,
    m3u8: bool = False,
    video: bool = False,
    url: str = None,
) -> None:
    sent = await m.reply_text(m.lang["play_searching"])
    file = None
    mention = m.from_user.mention
    media = tg.get_media(m.reply_to_message) if m.reply_to_message else None
    tracks = []

    if media:
        setattr(sent, "lang", m.lang)
        file = await tg.download(m.reply_to_message, sent)

    elif m3u8:
        file = await tg.process_m3u8(url, sent.id, video)

    elif url:
        if "playlist" in url:
            await safe_edit(sent, m.lang["playlist_fetch"])
            tracks = await yt.playlist(
                config.PLAYLIST_LIMIT, mention, url, video
            )

            if not tracks:
                await safe_edit(sent, m.lang["playlist_error"])
                return

            file = tracks[0]
            tracks.remove(file)
            file.message_id = sent.id
        else:
            file = await yt.search(url, sent.id, video=video)

        if not file:
            await safe_edit(sent, m.lang["play_not_found"].format(config.SUPPORT_CHAT))
            return

    elif len(m.command) >= 2:
        query = " ".join(m.command[1:])
        file = await yt.search(query, sent.id, video=video)
        if not file:
            await safe_edit(sent, m.lang["play_not_found"].format(config.SUPPORT_CHAT))
            return

    if not file:
        await safe_edit(sent, m.lang["play_usage"])
        return

    if file.duration_sec > config.DURATION_LIMIT:
        await safe_edit(sent, m.lang["play_duration_limit"].format(config.DURATION_LIMIT // 60))
        return

    if await db.is_logger():
        await utils.play_log(m, sent.link, file.title, file.duration)

    leaderboard_name = f'<a href="tg://openmessage?user_id={m.from_user.id}">{m.from_user.first_name}</a>'
    await db.add_play(m.chat.id, m.from_user.id, leaderboard_name, m.chat.title)

    file.user = mention
    if force:
        queue.force_add(m.chat.id, file)
    else:
        position = queue.add(m.chat.id, file)

        if position != 0 or await db.get_call(m.chat.id):
            await safe_edit(
                sent,
                m.lang["play_queued"].format(
                    position,
                    file.url,
                    file.title,
                    file.duration,
                    m.from_user.mention,
                ),
                reply_markup=buttons.play_queued(
                    m.chat.id, file.id, m.lang["play_now"]
                ),
            )
            if tracks:
                added = playlist_to_queue(m.chat.id, tracks)
                await app.send_message(
                    chat_id=m.chat.id,
                    text=m.lang["playlist_queued"].format(len(tracks)) + added,
                )
            return

    if not file.file_path:
        fname = os.path.abspath(f"downloads/{file.id}.{'mp4' if video else 'webm'}")
        if Path(fname).exists() and os.path.getsize(fname) > 0:
            file.file_path = fname
        else:
            await safe_edit(sent, m.lang["play_downloading"])
            file.file_path = await yt.download(
                file.id,
                video=video,
                title=getattr(file, "title", ""),
                duration=getattr(file, "duration", ""),
                duration_sec=getattr(file, "duration_sec", 0)
            )

    await anon.play_media(chat_id=m.chat.id, message=sent, media=file)
    if not tracks:
        return
    added = playlist_to_queue(m.chat.id, tracks)
    await app.send_message(
        chat_id=m.chat.id,
        text=m.lang["playlist_queued"].format(len(tracks)) + added,
    )

