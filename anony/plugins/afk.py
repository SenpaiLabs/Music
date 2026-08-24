# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic


import time
from pyrogram import filters, types
from pyrogram.enums import MessageEntityType

from anony import app, db, lang


def get_readable_time(seconds: int) -> str:
    if not seconds:
        return "0s"
    suffixes = ["s", "m", "h", "days"]
    parts = []
    for i in range(4):
        if not seconds:
            break
        seconds, val = divmod(seconds, 60 if i < 2 else 24)
        parts.append(f"{val}{suffixes[i]}")
    parts.reverse()
    if len(parts) == 4:
        return parts[0] + ", " + ":".join(parts[1:])
    return ":".join(parts)


@app.on_message(filters.command(["afk"]) & filters.group & ~app.bl_users)
@lang.language()
async def _afk_cmd(_, m: types.Message):
    reason = m.text.split(None, 1)[1] if len(m.command) > 1 else ""

    if afk_user := await db.is_afk(m.from_user.id):
        await db.remove_afk(m.from_user.id)
        await m.reply_text(m.lang["afk_removed"].format(m.from_user.first_name, get_readable_time(int(time.time() - afk_user["time"]))))

    await db.add_afk(m.from_user.id, {"time": time.time(), "reason": reason})
    await m.reply_text(m.lang["afk_set"].format(m.from_user.first_name, f"\nReason: {reason}" if reason else ""))


@app.on_message(filters.group & ~app.bl_users & ~filters.bot & ~filters.via_bot, group=20)
@lang.language()
async def _afk_watcher(_, m: types.Message):
    if not m.from_user:
        return

    if not (m.text and m.text.split()[0].lower().endswith("afk") and m.text.startswith(("/", "!", "?"))):
        if afk_user := await db.is_afk(m.from_user.id):
            await db.remove_afk(m.from_user.id)
            await m.reply_text(m.lang["afk_removed"].format(m.from_user.first_name, get_readable_time(int(time.time() - afk_user["time"]))))

    targets = {}
    if m.reply_to_message and m.reply_to_message.from_user:
        targets[m.reply_to_message.from_user.id] = m.reply_to_message.from_user.first_name

    for e in (m.entities or []):
        try:
            if e.type == MessageEntityType.TEXT_MENTION:
                targets[e.user.id] = e.user.first_name
            elif e.type == MessageEntityType.MENTION and m.text:
                u = await app.get_users(m.text[e.offset:e.offset + e.length].strip("@"))
                targets[u.id] = u.first_name
        except Exception:
            pass

    for uid, name in targets.items():
        if uid == m.from_user.id:
            continue
        if afk_user := await db.is_afk(uid):
            r = afk_user.get("reason", "")
            await m.reply_text(m.lang["afk_reply"].format(name, get_readable_time(int(time.time() - afk_user["time"])), f"\nReason: {r}" if r else ""))
