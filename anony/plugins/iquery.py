# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic

import asyncio
import time
import yt_dlp
from pyrogram import types

from anony import app, yt
from anony.helpers import buttons


@app.on_inline_query(~app.bl_users)
async def inline_query_handler(_, query: types.InlineQuery):
    text = query.query.strip().lower()
    if not text:
        return

    try:
        def _search():
            cookie = yt.get_cookies()
            opts = {"extract_flat": True, "quiet": True}
            if cookie:
                opts["cookiefile"] = cookie
            with yt_dlp.YoutubeDL(opts) as ydl:
                return ydl.extract_info(f"ytsearch15:{text}", download=False)

        info = await asyncio.to_thread(_search)
        results = info.get("entries", []) if info else []

        answers = []
        for video in results:
            if not video:
                continue
            title = video.get("title", "Unknown Title").title()
            dur_sec = int(video.get("duration") or 0)
            duration = time.strftime("%M:%S", time.gmtime(dur_sec)) if dur_sec else "N/A"
            views = str(video.get("view_count", "N/A"))
            thumbnail = video.get("thumbnail", "").split("?")[0] if video.get("thumbnail") else ""
            channel = video.get("uploader", "Unknown Channel")
            vid_id = video.get("id", "")
            link = f"https://www.youtube.com/watch?v={vid_id}" if vid_id else "https://youtube.com"

            description = f"{views} views | {duration} | {channel}"
            caption = (
                f"<b>Title:</b> <a href='{link}'>{title[:250]}</a>\n\n"
                f"<b>Duration:</b> {duration}\n"
                f"<b>Views:</b> <code>{views}</code>\n"
                f"<b>Channel:</b> {channel}\n\n"
                f"<u><i>Fetched by {app.name}</i></u>"
            )

            if thumbnail:
                answers.append(
                    types.InlineQueryResultPhoto(
                        photo_url=thumbnail,
                        title=title,
                        description=description,
                        caption=caption,
                        reply_markup=buttons.yt_key(link),
                    )
                )

        if answers:
            await app.answer_inline_query(query.id, results=answers, cache_time=5)
    except Exception:
        pass
