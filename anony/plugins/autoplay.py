# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic


from pyrogram import filters, types

from anony import app, db, lang


@app.on_message(filters.command("autoplay") & filters.group & ~app.bl_users)
@lang.language()
async def autoplay_hndlr(_, m: types.Message) -> None:
    chat_id = m.chat.id

    if len(m.command) < 2:
        status = await db.get_autoplay(chat_id)
        return await m.reply_text(
            m.lang["autoplay_status"].format(
                m.lang["enabled"] if status else m.lang["disabled"]
            )
        )

    adminlist = await db.get_admins(chat_id)
    if (
        m.from_user.id not in adminlist
        and not await db.is_auth(chat_id, m.from_user.id)
        and m.from_user.id not in app.sudoers
    ):
        return await m.reply_text(m.lang["play_admin"])

    arg = m.command[1].lower()
    if arg in ("on", "enable"):
        await db.set_autoplay(chat_id, True)
        return await m.reply_text(m.lang["autoplay_on"])
    elif arg in ("off", "disable"):
        await db.set_autoplay(chat_id, False)
        return await m.reply_text(m.lang["autoplay_off"])

    return await m.reply_text(m.lang["autoplay_usage"])

