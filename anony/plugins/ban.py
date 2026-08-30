from pyrogram import filters, types
from pyrogram.errors import ChatAdminRequired, UserAdminInvalid
from anony import app, lang

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

@app.on_message(filters.command("ban") & filters.group)
@lang.language()
async def ban_usr(_, message: types.Message):
    user = await extract_target(message)
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
    user = await extract_target(message)
    if not user:
        return await message.reply_text(message.lang["m_invalid_target"])
    try:
        await message.chat.unban_member(user.id)
        await message.reply_text(message.lang["m_unbanned"].format(user.mention))
    except ChatAdminRequired:
        await message.reply_text(message.lang["m_bot_not_admin"].format(message.chat.title))
    except Exception as e:
        await message.reply_text(message.lang["m_fail_unban"].format(e))
