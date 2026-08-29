from pyrogram import filters, types
from anony import app

@app.on_message(filters.command("purge") & filters.group)
async def purge_msgs(_, message: types.Message):
    if not message.reply_to_message:
        return
    msg_ids = list(range(message.reply_to_message.id, message.id + 1))
    await app.delete_messages(message.chat.id, msg_ids)
