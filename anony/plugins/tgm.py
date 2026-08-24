import os
import aiohttp
from pyrogram import filters, types
from anony import app, config, lang


@app.on_message(filters.command(["tgm", "imgbb"]) & ~app.bl_users)
@lang.language()
async def tgm_upload(_, message: types.Message):
    reply = message.reply_to_message
    if not reply or not reply.photo:
        return await message.reply_text(message.lang["tgm_reply_media"])

    msg = await message.reply_text(message.lang["tgm_downloading"])

    local_path = await reply.download()
    if not local_path:
        return await msg.edit_text(message.lang["tgm_download_fail"])

    await msg.edit_text(message.lang["tgm_uploading"].format("TGM"))
    try:
        api_key = config.IMGBB_API_KEY
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        }
        async with aiohttp.ClientSession(headers=headers) as session:
            with open(local_path, "rb") as f:
                async with session.post(f"https://api.imgbb.com/1/upload?key={api_key}", data={"image": f}) as response:
                    res = await response.json()
                    if res.get("success"):
                        url = res["data"]["url"]
                        markup = types.InlineKeyboardMarkup([[types.InlineKeyboardButton("🔗 Open Link", url=url)]])
                        await msg.edit_text(message.lang["tgm_success"].format(url), reply_markup=markup, disable_web_page_preview=True)
                    else:
                        error_msg = res.get("error", {}).get("message", "Unknown error")
                        await msg.edit_text(message.lang["tgm_imgbb_err"].format(error_msg))
    except Exception as e:
        await msg.edit_text(message.lang["tgm_err"].format(str(e)))
    finally:
        if os.path.exists(local_path):
            os.remove(local_path)
