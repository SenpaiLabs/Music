# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic


from pyrogram import filters, types

from anony import app, lang
from anony.helpers import buttons


@app.on_message(
    filters.command(["leaderboard", "top", "tops", "ranking"]) & filters.group & ~app.bl_users
)
@lang.language()
async def _leaderboard(_, m: types.Message):
    await m.reply_text(
        m.lang["leaderboard_menu"],
        reply_markup=buttons.leaderboard_markup(m.lang, m.chat.id),
    )

