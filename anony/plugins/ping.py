# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic


import time
import psutil

from pyrogram import filters, types
from anony import app, anon, boot, config, lang
from anony.helpers import buttons


@app.on_message(filters.command(["alive", "ping"]) & ~app.bl_users)
@lang.language()
async def _ping(_, m: types.Message):
    start = time.time()
    _s = int(time.time() - boot)
    _d, _s = divmod(_s, 86400)
    _h, _s = divmod(_s, 3600)
    _m, _s = divmod(_s, 60)
    _hms = f"{_h}h:{_m}m:{_s}s"
    uptime = f"{_d}days, {_hms}" if _d else _hms
    latency = round((time.time() - start) * 1000, 2)
    await m.reply_photo(
        photo=config.PING_IMG,
        caption=m.lang["ping_pong"].format(
            latency,
            uptime,
            psutil.cpu_percent(interval=0),
            psutil.virtual_memory().percent,
            psutil.disk_usage("/").percent,
            await anon.ping(),
        ),
        reply_markup=buttons.ping_markup(m.lang["support"]),
        ephemeral_message_parameters=types.EphemeralMessageParameters(
            receiver_user_id=m.from_user.id
        )
    )
