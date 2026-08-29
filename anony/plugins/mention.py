from pyrogram import filters
from pyrogram.enums import ChatMemberStatus
from anony import app, lang
import asyncio

stop_tag = {}

async def is_admin(m):
    member = await m.chat.get_member(m.from_user.id)
    return member.status in (ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR)

@app.on_message(filters.command(["mention", "tag", "tagall"]) & filters.group)
@lang.language()
async def tagall(_, m):
    if not await is_admin(m):
        return await m.reply(m.lang["user_not_admin"])
    stop_tag[m.chat.id] = False
    users = [u.user.mention async for u in m.chat.get_members() if not u.user.is_bot]
    text = f"{m.text.split(None, 1)[1]}\n" if len(m.command) > 1 else ""
    reply_id = m.reply_to_message.id if m.reply_to_message else m.id
    for i in range(0, len(users), 5):
        if stop_tag.get(m.chat.id):
            break
        await m.reply(f"{text}{' '.join(users[i:i+5])}", reply_to_message_id=reply_id)
        await asyncio.sleep(2)

@app.on_message(filters.command(["cancel", "stoptag", "canceltag"]) & filters.group)
@lang.language()
async def cancel(_, m):
    if not await is_admin(m):
        return await m.reply(m.lang["user_not_admin"])
    stop_tag[m.chat.id] = True
    await m.reply(m.lang["t_stp"])
