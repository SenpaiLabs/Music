# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic

import asyncio
import io
from pyrogram import filters, types
from pyrogram.errors import FloodWait, ChannelInvalid, ChannelPrivate, PeerIdInvalid

from anony import app, db, lang

botchats_lock = asyncio.Lock()

@app.on_message(filters.command(["botchats", "grouplist"]) & filters.private & app.sudoers)
@lang.language()
async def extract_bot_chats(_, message: types.Message):
    if botchats_lock.locked():
        return await message.reply_text(message.lang["botchats_locked"])

    mystic = await message.reply_text(message.lang["botchats_processing"])
    
    chats = await db.get_chats()
    if not chats:
        return await mystic.edit_text(message.lang["botchats_empty"])
    
    async with botchats_lock:
        memory_file = io.BytesIO()
        memory_file.write(message.lang["botchats_header"].format(app.name.title()).encode("utf-8"))

        successful = 0
        failed = 0
        
        for chat_id in chats:
            try:
                chat = await app.get_chat(chat_id)
                
                # Fetch or generate invite link
                invite_link = chat.invite_link
                if not invite_link:
                    try:
                        invite_link = await app.export_chat_invite_link(chat_id)
                    except Exception:
                        invite_link = message.lang["botchats_no_link"]
                
                chat_title = chat.title or "Unknown Title"
                members = chat.members_count or 0
                
                chunk = message.lang["botchats_chunk"].format(chat_title, chat_id, members, invite_link)
                memory_file.write(chunk.encode("utf-8"))
                    
                successful += 1
                
            except FloodWait as e:
                await asyncio.sleep(e.value + 1)
            except (ChannelInvalid, ChannelPrivate, PeerIdInvalid):
                # Bot is no longer in this group, clean DB
                await db.rm_chat(chat_id)
                failed += 1
            except Exception:
                failed += 1
            
            await asyncio.sleep(2)
                
        await mystic.delete()
        
        caption = message.lang["botchats_done"].format(len(chats), successful, failed)
        
        memory_file.name = f"bot_groups_{message.from_user.id}.txt"
        
        await message.reply_document(
            document=memory_file,
            caption=caption
        )
        
        memory_file.close()
