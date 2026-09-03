from pyrogram import filters, types
from pyrogram.errors import ChatAdminRequired, UserAdminInvalid
from anony import app, lang
from anony.helpers import extract_user

@app.on_message(filters.command("ban") & filters.group)
@lang.language()
async def ban_usr(_, message: types.Message):
    user = await extract_user(message)
    if not user:
        return await message.reply_text(message.lang["m_invalid_target"])
    try:
        await message.chat.ban_member(user.id)
        await message.reply_text(message.lang["m_banned"].format(user.mention))
    except ChatAdminRequired:
        await message.reply_text(message.lang["m_bot_not_admin"].format(message.chat.title))
    except UserAdminInvalid:
        await message.reply_text(message.lang["m_cant_ban_admin"])
    except Exception as e:
        await message.reply_text(message.lang["m_fail_ban"].format(e))

@app.on_message(filters.command("unban") & filters.group)
@lang.language()
async def unban_usr(_, message: types.Message):
    user = await extract_user(message)
    if not user:
        return await message.reply_text(message.lang["m_invalid_target"])
    try:
        await message.chat.unban_member(user.id)
        await message.reply_text(message.lang["m_unbanned"].format(user.mention))
    except ChatAdminRequired:
        await message.reply_text(message.lang["m_bot_not_admin"].format(message.chat.title))
    except Exception as e:
        await message.reply_text(message.lang["m_fail_unban"].format(e))
