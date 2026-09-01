from pyrogram import filters, types
from anony import app

@app.on_message(filters.command("pin") & filters.group)
async def pin_msg(_, message: types.Message):
    if message.reply_to_message:
        try: await message.reply_to_message.pin()
        except: pass

@app.on_message(filters.command("unpin") & filters.group)
async def unpin_msg(_, message: types.Message):
    if message.reply_to_message:
        try: await message.reply_to_message.unpin()
        except: pass
