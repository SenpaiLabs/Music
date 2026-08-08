# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic


import time
from pyrogram import filters, types
from pyrogram.enums import MessageEntityType

from anony import app, db, lang


def get_readable_time(seconds: int) -> str:
    count = 0
    ping_time = ""
    time_list = []
    time_suffix_list = ["s", "m", "h", "days"]

    if seconds == 0:
        return "0s"
        
    while count < 4:
        count += 1
        remainder, result = divmod(seconds, 60) if count < 3 else divmod(seconds, 24)
        if seconds == 0 and remainder == 0:
            break
        time_list.append(int(result))
        seconds = int(remainder)

    for x in range(len(time_list)):
        time_list[x] = str(time_list[x]) + time_suffix_list[x]
    if len(time_list) == 4:
        ping_time += time_list.pop() + ", "

    time_list.reverse()
    ping_time += ":".join(time_list)
    return ping_time


@app.on_message(filters.command(["afk"]) & filters.group & ~app.bl_users)
@lang.language()
async def _afk_cmd(_, m: types.Message):
    if len(m.command) == 1:
        reason = ""
    else:
        reason = m.text.split(None, 1)[1]
        
    afk_user = await db.is_afk(m.from_user.id)
    if afk_user:
        since = int(time.time() - afk_user["time"])
        time_str = get_readable_time(since)
        await db.remove_afk(m.from_user.id)
        await m.reply_text(m.lang["afk_removed"].format(m.from_user.first_name, time_str))
    
    details = {
        "time": time.time(),
        "reason": reason,
    }
    
    await db.add_afk(m.from_user.id, details)
    await m.reply_text(m.lang["afk_set"].format(m.from_user.first_name, f"\nReason: {reason}" if reason else ""))


@app.on_message(filters.group & ~app.bl_users & ~filters.bot & ~filters.via_bot, group=20)
@lang.language()
async def _afk_watcher(_, m: types.Message):
    # Check if sender was AFK (ignore the /afk command itself)
    if m.from_user and not (m.text and m.text.split()[0].lower().endswith("afk") and m.text.startswith(("/", "!", "?"))):
        afk_user = await db.is_afk(m.from_user.id)
        if afk_user:
            since = int(time.time() - afk_user["time"])
            time_str = get_readable_time(since)
            await db.remove_afk(m.from_user.id)
            await m.reply_text(m.lang["afk_removed"].format(m.from_user.first_name, time_str))
            
    # Check if a mentioned user is AFK
    if m.entities:
        for entity in m.entities:
            if entity.type == MessageEntityType.MENTION:
                try:
                    username = m.text[entity.offset:entity.offset + entity.length].strip("@")
                    user = await app.get_users(username)
                    afk_user = await db.is_afk(user.id)
                    if afk_user:
                        since = int(time.time() - afk_user["time"])
                        time_str = get_readable_time(since)
                        reason = afk_user.get("reason", "")
                        await m.reply_text(
                            m.lang["afk_reply"].format(user.first_name, time_str, f"\nReason: {reason}" if reason else "")
                        )
                except Exception:
                    pass
            elif entity.type == MessageEntityType.TEXT_MENTION:
                try:
                    user_id = entity.user.id
                    afk_user = await db.is_afk(user_id)
                    if afk_user:
                        since = int(time.time() - afk_user["time"])
                        time_str = get_readable_time(since)
                        reason = afk_user.get("reason", "")
                        await m.reply_text(
                            m.lang["afk_reply"].format(entity.user.first_name, time_str, f"\nReason: {reason}" if reason else "")
                        )
                except Exception:
                    pass

    # Check if replied to an AFK user
    if m.reply_to_message and m.reply_to_message.from_user:
        user_id = m.reply_to_message.from_user.id
        if user_id != m.from_user.id:
            afk_user = await db.is_afk(user_id)
            if afk_user:
                since = int(time.time() - afk_user["time"])
                time_str = get_readable_time(since)
                reason = afk_user.get("reason", "")
                await m.reply_text(
                    m.lang["afk_reply"].format(m.reply_to_message.from_user.first_name, time_str, f"\nReason: {reason}" if reason else "")
                )
