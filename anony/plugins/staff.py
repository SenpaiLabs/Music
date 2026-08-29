from pyrogram import filters, types, enums
from anony import app, lang

@app.on_message(filters.command(["staff", "admins"]) & filters.group)
@lang.language()
async def staff_list(_, message: types.Message):
    text = message.lang["m_staff_title"]
    async for m in app.get_chat_members(message.chat.id, filter=enums.ChatMembersFilter.ADMINISTRATORS):
        text += f"- {m.user.first_name}\n"
    await message.reply_text(text)
