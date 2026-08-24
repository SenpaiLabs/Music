# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic

import asyncio
from pyrogram import filters, types
from pyrogram.errors import FloodWait, ChannelInvalid, ChannelPrivate, PeerIdInvalid

from anony import app, db, lang

@app.on_message(filters.command(["botchats"]) & filters.private & app.sudoers)
@lang.language()
async def extract_bot_chats(_, message: types.Message):
    if len(message.command) < 2:
        return await message.reply_text(message.lang["bc_usage"])
    
    try:
        chat_id = int(message.command[1])
    except ValueError:
        return await message.reply_text(message.lang["bc_id"])

    mystic = await message.reply_text(message.lang["bc_load"])
    
    try:
        chat = await app.get_chat(chat_id)
        
        invite_link = chat.invite_link
        if not invite_link:
            if chat.username:
                invite_link = f"https://t.me/{chat.username}"
            else:
                try:
                    invite_link = await app.export_chat_invite_link(chat_id)
                except Exception:
                    invite_link = message.lang["bc_nolink"]
        
        chat_title = chat.title or "Unknown Title"
        members = chat.members_count or 0
        
        text = message.lang["bc_res"].format(chat_title, chat_id, members, invite_link)
        await mystic.edit_text(text)
        
    except FloodWait as e:
        await mystic.edit_text(message.lang["bc_fw"].format(e.value))
    except (ChannelInvalid, ChannelPrivate, PeerIdInvalid):
        await mystic.edit_text(message.lang["bc_nf"])
        await db.rm_chat(chat_id)
    except Exception as e:
        await mystic.edit_text(message.lang["bc_err"].format(e))
