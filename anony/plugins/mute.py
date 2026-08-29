from datetime import datetime, timedelta
from pyrogram import filters, types
from anony import app, lang
from anony.helpers import admin_check

def parse_time(time_str: str):
    try:
        val = int(time_str[:-1])
        unit = time_str[-1].lower()
        if unit == "m": return datetime.now() + timedelta(minutes=val)
        if unit == "h": return datetime.now() + timedelta(hours=val)
        if unit == "d": return datetime.now() + timedelta(days=val)
    except:
        pass
    return None

async def extract_target(message: types.Message, arg_idx: int = 1):
    if message.reply_to_message:
        return message.reply_to_message.from_user
    if len(message.command) > arg_idx:
        arg = message.command[arg_idx]
        try:
            return await app.get_users(int(arg) if arg.isdigit() else arg)
        except:
            pass
    return None

@app.on_message(filters.command("mute") & filters.group)
@lang.language()
@admin_check
async def mute_usr(_, message: types.Message):
    user = await extract_target(message)
    if not user:
        return await message.reply_text(message.lang["m_invalid_target"])
        
    await message.chat.restrict_member(user.id, types.ChatPermissions())
    await message.reply_text(message.lang["m_muted_perm"].format(user.mention))

@app.on_message(filters.command("tmute") & filters.group)
@lang.language()
@admin_check
async def tmute_usr(_, message: types.Message):
    if len(message.command) < 2:
        return await message.reply_text(message.lang["m_provide_time"])
        
    until_date = parse_time(message.command[1])
    if not until_date:
        return await message.reply_text(message.lang["m_invalid_time"])
        
    user = await extract_target(message, arg_idx=2)
    if not user:
        return await message.reply_text(message.lang["m_invalid_target"])
        
    await message.chat.restrict_member(
        user.id, 
        types.ChatPermissions(),
        until_date=until_date
    )
    await message.reply_text(message.lang["m_muted_temp"].format(user.mention, message.command[1]))

@app.on_message(filters.command("unmute") & filters.group)
@lang.language()
@admin_check
async def unmute_usr(_, message: types.Message):
    user = await extract_target(message)
    if not user:
        return await message.reply_text(message.lang["m_invalid_target"])
        
    await message.chat.unban_member(user.id)
    await message.reply_text(message.lang["m_unmuted"].format(user.mention))
