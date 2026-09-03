# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic


from functools import wraps

from pyrogram import StopPropagation, enums, types

from anony import app, db


def admin_check(func):
    @wraps(func)
    async def wrapper(_, update: types.Message | types.CallbackQuery, *args, **kwargs):
        async def reply(text):
            if isinstance(update, types.Message):
                return await update.reply_text(text)
            else:
                return await update.answer(text, show_alert=True)

        chat = (
            update.chat
            if isinstance(update, types.Message)
            else update.message.chat
        )
        if chat.type == enums.ChatType.PRIVATE:
            return await func(_, update, *args, **kwargs)

        sender_chat = getattr(update, "sender_chat", None)
        if sender_chat and sender_chat.id == chat.id:
            return await func(_, update, *args, **kwargs)

        from_user = getattr(update, "from_user", None)
        if not from_user:
            return await reply(update.lang["user_no_perms"])

        user_id = from_user.id
        if user_id == 1087968824 or user_id in app.sudoers:
            return await func(_, update, *args, **kwargs)

        admins = await db.get_admins(chat.id)
        if user_id not in admins:
            return await reply(update.lang["user_no_perms"])

        return await func(_, update, *args, **kwargs)

    return wrapper



def can_manage_vc(func):
    @wraps(func)
    async def wrapper(_, update: types.Message | types.CallbackQuery, *args, **kwargs):
        chat_id = (
            update.chat.id
            if isinstance(update, types.Message)
            else update.message.chat.id
        )
        sender_chat = getattr(update, "sender_chat", None)
        if sender_chat and sender_chat.id == chat_id:
            return await func(_, update, *args, **kwargs)

        from_user = getattr(update, "from_user", None)
        if not from_user:
            msg = update.lang["user_no_perms"]
            return await update.reply_text(msg) if isinstance(update, types.Message) else await update.answer(msg, show_alert=True)

        user_id = from_user.id
        if user_id == 1087968824 or user_id in app.sudoers:
            return await func(_, update, *args, **kwargs)

        if await db.is_auth(chat_id, user_id):
            return await func(_, update, *args, **kwargs)

        admins = await db.get_admins(chat_id)
        if user_id in admins:
            return await func(_, update, *args, **kwargs)

        if isinstance(update, types.Message):
            return await update.reply_text(update.lang["user_no_perms"])
        else:
            return await update.answer(update.lang["user_no_perms"], show_alert=True)

    return wrapper


async def is_admin(chat_id: int, user_id: int) -> bool:
    if user_id == 1087968824 or user_id in await db.get_admins(chat_id):
        return True
    try:
        member = await app.get_chat_member(chat_id, user_id)
        return member.status in [
            enums.ChatMemberStatus.ADMINISTRATOR,
            enums.ChatMemberStatus.OWNER,
        ]
    except Exception:
        raise StopPropagation


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

