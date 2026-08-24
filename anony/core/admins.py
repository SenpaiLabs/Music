# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic

from pyrogram import enums
from anony import app

async def reload_admins(chat_id: int) -> list[int]:
    try:
        return [
            admin.user.id
            async for admin in app.get_chat_members(
                chat_id, filter=enums.ChatMembersFilter.ADMINISTRATORS
            )
            if not admin.user.is_bot
        ]
    except Exception:
        return []
