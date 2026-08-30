# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic


import itertools

from pyrogram import filters, types

from anony import app, db, lang, queue
from anony.helpers import buttons


@app.on_message(filters.command(["queue", "playing"]) & filters.group & ~app.bl_users)
@lang.language()
async def _queue_func(_, m: types.Message):
    if not await db.get_call(m.chat.id):
        return await m.reply_text(m.lang["not_playing"])

    _reply = await m.reply_text(m.lang["queue_fetching"])
    _queue = queue.get_queue(m.chat.id)
    _media = _queue[0]

    _text = m.lang["queue_curr"].format(
        _media.url,
        _media.title[:50],
        _media.duration,
        _media.user,
    )
    _queue.pop(0)

    if _queue:
        _text += "<blockquote expandable>"
        for i, media in enumerate(itertools.islice(_queue, 0, 14), start=1):
            _text += m.lang["queue_item"].format(
                i + 1, media.title, media.duration
            )
        _text += "</blockquote>"

    _playing = await db.playing(m.chat.id)
    _buttons = buttons.queue_markup(
            m.chat.id,
            m.lang["playing"] if _playing else m.lang["paused"],
            _playing,
        )
    try:
        await _reply.edit_text(
            text=_text,
            reply_markup=_buttons,
        )
    except Exception:
        await _reply.delete()
        await m.reply_text(
            text=_text,
            reply_markup=_buttons,
        )
