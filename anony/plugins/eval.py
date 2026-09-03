# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic


import io
import os
import re
import sys
import traceback
from html import escape

from pyrogram import filters, types

from anony import anon, app, config, db, lang, userbot
from anony.helpers import meval


@app.on_message(filters.command(["eval", "exec"]) & filters.user(app.owner))
@app.on_edited_message(filters.command(["eval", "exec"]) & filters.user(app.owner))
@lang.language()
async def eval_handler(_, message: types.Message):
    if len(message.command) < 2:
        return await message.reply_text(message.lang["eval_inp"])

    code = message.text.split(None, 1)[1]
    out_buf = io.StringIO()

    async def _eval_code():
        async def send(*args, **kwargs) -> types.Message:
            return await message.reply_text(*args, **kwargs)

        def _print(*args, **kwargs) -> None:
            kwargs.setdefault("file", out_buf)
            print(*args, **kwargs)

        eval_vars = {
            "m": message,
            "r": message.reply_to_message,
            "chat": message.chat,
            "user": message.from_user,
            "app": app,
            "anon": anon,
            "db": db,
            "client": app,
            "ub": userbot,
            "ikb": types.InlineKeyboardButton,
            "ikm": types.InlineKeyboardMarkup,
            "send": send,
            "config": config,
            "print": _print,
            "os": os,
            "re": re,
            "sys": sys,
            "tb": traceback,
        }

        try:
            result = await meval(code, globals(), **eval_vars)
            return "", result
        except Exception:
            return message.lang["eval_error"], traceback.format_exc()

    _, result = await _eval_code()

    if result is not None or not out_buf.getvalue():
        print(result, file=out_buf)

    output = out_buf.getvalue().strip()
    response = message.lang["eval_out"].format(escape(output))

    if len(response) > 4096:
        with io.BytesIO(output.encode()) as out_file:
            out_file.name = f"{os.urandom(4).hex()}.txt"
            return await message.reply_document(
                document=out_file, disable_notification=True
            )

    await message.reply_text(response)
