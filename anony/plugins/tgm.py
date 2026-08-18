import io
import os
import aiohttp
from pyrogram import filters, types
from anony import app, lang


@app.on_message(filters.command(["tgm", "telegraph", "catbox", "imgbb"]) & ~app.bl_users)
@lang.language()
async def multi_upload(_, message: types.Message):
    reply = message.reply_to_message
    if not reply or not (reply.photo or reply.video or reply.animation or reply.document):
        return await message.reply_text(message.lang["tgm_reply_media"])

    command = message.command[0].lower()

    if command in ["tgm", "telegraph"]:
        if not (reply.photo or reply.video or reply.animation):
            return await message.reply_text(message.lang["tgm_tele_unsupported"])
        if (reply.video and reply.video.file_size > 5 * 1024 * 1024) or (reply.animation and reply.animation.file_size > 5 * 1024 * 1024):
            return await message.reply_text(message.lang["tgm_tele_size"])
    elif command == "imgbb":
        if not reply.photo:
            return await message.reply_text(message.lang["tgm_imgbb_unsupported"])

    media = reply.photo or reply.video or reply.animation or reply.document
    if getattr(media, "file_size", 0) > 200 * 1024 * 1024:
        return await message.reply_text(message.lang["tgm_catbox_size"])

    filename = getattr(media, "file_name", "upload.jpg" if reply.photo else "upload.mp4")

    msg = await message.reply_text(message.lang["tgm_downloading"])
    
    # Download directly into memory (extremely fast)
    mem_file = await reply.download(in_memory=True)
    if not mem_file:
        return await msg.edit_text(message.lang["tgm_download_fail"])

    await msg.edit_text(message.lang["tgm_uploading"].format(command.capitalize()))
    try:
        mem_file.name = filename
        async with aiohttp.ClientSession() as session:
            if command in ["tgm", "telegraph"]:
                form = aiohttp.FormData()
                form.add_field("file", mem_file, filename=filename)
                async with session.post("https://telegra.ph/upload", data=form) as response:
                    res = await response.json()
                    if isinstance(res, list) and "src" in res[0]:
                        url = f"https://telegra.ph{res[0]['src']}"
                        markup = types.InlineKeyboardMarkup([[types.InlineKeyboardButton("🔗 Open Link", url=url)]])
                        await msg.edit_text(message.lang["tgm_success"].format(url), reply_markup=markup, disable_web_page_preview=True)
                    elif isinstance(res, dict) and "error" in res:
                        await msg.edit_text(message.lang["tgm_tele_err"].format(res['error']))
                    else:
                        await msg.edit_text(message.lang["tgm_tele_fail"])
            
            elif command == "catbox":
                form = aiohttp.FormData()
                form.add_field("reqtype", "fileupload")
                form.add_field("fileToUpload", mem_file, filename=filename)
                async with session.post("https://catbox.moe/user/api.php", data=form) as response:
                    res = await response.text()
                    if res.startswith("https://"):
                        markup = types.InlineKeyboardMarkup([[types.InlineKeyboardButton("🔗 Open Link", url=res)]])
                        await msg.edit_text(message.lang["tgm_success"].format(res), reply_markup=markup, disable_web_page_preview=True)
                    else:
                        await msg.edit_text(message.lang["tgm_catbox_err"].format(res))
            
            elif command == "imgbb":
                api_key = "c80e46893d6143f407e66fa944f0c46c"
                form = aiohttp.FormData()
                form.add_field("image", mem_file, filename=filename)
                async with session.post(f"https://api.imgbb.com/1/upload?key={api_key}", data=form) as response:
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
        mem_file.close()
