# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic


import io
import asyncio

from pyrogram import errors, filters, types

from anony import app, db, lang


broadcasting = asyncio.Lock()

@app.on_message(filters.command(["broadcast"]) & app.sudoers)
@lang.language()
async def _broadcast(_, message: types.Message):
    if not message.reply_to_message:
        return await message.reply_text(message.lang["gcast_usage"])

    if broadcasting.locked():
        return await message.reply_text(message.lang["gcast_active"])

    msg = message.reply_to_message
    copy = "-copy" in message.command
    groups, users = set(), set()
    sent = await message.reply_text(message.lang["gcast_start"])

    if "-nochat" not in message.command:
        groups = set(await db.get_chats())
    if "-user" in message.command:
        users = set(await db.get_users())

    chats = list(groups | users)
    failed = None

    async with broadcasting:
        stats = {"count": 0, "ucount": 0}
        failed_list = []

        circuit_breaker = asyncio.Event()
        circuit_breaker.set()
        semaphore = asyncio.Semaphore(20)

        async def _send(chat):
            while True:
                async with semaphore:
                    await circuit_breaker.wait()
                    try:
                        (
                            await msg.copy(chat, reply_markup=msg.reply_markup)
                            if copy
                            else await msg.forward(chat)
                        )
                        if chat in groups:
                            stats["count"] += 1
                        else:
                            stats["ucount"] += 1
                        await asyncio.sleep(0.5)
                        break
                    except errors.FloodWait as fw:
                        circuit_breaker.clear()
                        await asyncio.sleep(fw.value + 1)
                        circuit_breaker.set()
                    except (
                        errors.UserIsBlocked,
                        errors.PeerIdInvalid,
                        errors.InputUserDeactivated,
                        errors.ChannelInvalid,
                        errors.ChannelPrivate,
                    ) as ex:
                        if chat in groups:
                            await db.rm_chat(chat)
                        else:
                            await db.rm_user(chat)
                        failed_list.append(f"{chat} - Cleaned from DB: {ex.__class__.__name__}\n")
                        break
                    except Exception as ex:
                        failed_list.append(f"{chat} - {ex.__class__.__name__}: {str(ex)}\n")
                        break

        await asyncio.gather(*[_send(chat) for chat in chats])

        count = stats["count"]
        ucount = stats["ucount"]

        failed_bio = None
        if failed_list:
            failed_bio = io.BytesIO("".join(failed_list).encode())
            failed_bio.name = "errors.txt"

    text = message.lang["gcast_end"].format(count, ucount)
    if failed_bio:
        await message.reply_document(
            document=failed_bio,
            caption=text,
        )

    await sent.edit_text(text)
