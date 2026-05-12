# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic


import asyncio
import time

from pyrogram import filters, enums
from pyrogram.enums import ChatMemberStatus
from pyrogram.errors import FloodWait, ChatAdminRequired
from pyrogram.types import Message

from anony import app, lang, config
from anony.helpers import format_exception
from anony.core.admins import reload_admins

active_ops: dict[int, str] = {}


async def _clean_msg(message: Message, delay: int = 60):
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception:
        pass


async def _worker(
    worker_id: int,
    queue: asyncio.Queue,
    chat_id: int,
    op: str,
    circuit_breaker: asyncio.Event,
    stats: dict
):
    while True:
        try:
            user_id = queue.get_nowait()
        except asyncio.QueueEmpty:
            break

        await circuit_breaker.wait()

        if chat_id not in active_ops:
            queue.task_done()
            continue

        stats["total"] += 1
        try:
            if op in ("ban", "kick"):
                await app.ban_chat_member(chat_id, user_id)
                if op == "kick":
                    await asyncio.sleep(0.1)
                    await app.unban_chat_member(chat_id, user_id)
            else:
                await app.unban_chat_member(chat_id, user_id)
            stats["done"] += 1
        except FloodWait as e:
            circuit_breaker.clear()
            await asyncio.sleep(e.value + 1)
            circuit_breaker.set()
        except Exception:
            stats["failed"] += 1

        queue.task_done()


async def purge_chat(message: Message, target_chat_id: int, op: str, is_test: bool, filter_type: str) -> None:
    if target_chat_id in active_ops:
        return await message.reply_text(message.lang["purge_active"])

    try:
        me = await app.get_chat_member(target_chat_id, app.id)
        if me.status != ChatMemberStatus.OWNER and not (
            me.privileges and getattr(me.privileges, "can_restrict_members", False)
        ):
            return await message.reply_text(message.lang["purge_rights"])
    except Exception:
        return await message.reply_text(message.lang["purge_rights"])

    active_ops[target_chat_id] = op
    if message.chat.id == target_chat_id:
        try:
            await app.send_reaction(target_chat_id, message.id, "🍓")
        except Exception:
            pass

    labels = {"ban": "purge_op_ban", "kick": "purge_op_kick", "unban": "purge_op_unban"}
    label = message.lang[labels[op]]

    progress = await message.reply_text(
        message.lang["purge_start"].format(label)
    )

    start_time = time.time()
    stats = {"total": 0, "done": 0, "failed": 0}
    target_ids = []

    try:
        if op in ("ban", "kick"):
            admins = await reload_admins(target_chat_id)
            async for member in app.get_chat_members(target_chat_id):
                user = member.user
                if not user or user.id in admins or user.id == app.id:
                    continue

                # Apply Targeted Purge Filters
                if filter_type == "bots" and not user.is_bot:
                    continue
                if filter_type == "deleted" and not user.is_deleted:
                    continue

                target_ids.append(user.id)
        else:
            async for member in app.get_chat_members(target_chat_id, filter=enums.ChatMembersFilter.BANNED):
                if member.user:
                    target_ids.append(member.user.id)

        total_targets = len(target_ids)

        # Dry-Run Mode
        if is_test:
            active_ops.pop(target_chat_id, None)
            eta_sec = total_targets * 0.15
            eta_str = f"{int(eta_sec)}s" if eta_sec < 60 else f"{int(eta_sec // 60)}m {int(eta_sec % 60)}s"
            filter_str = filter_type.capitalize() if filter_type else message.lang["purge_all_users"]

            res_msg = await progress.edit_text(
                message.lang["purge_test_result"].format(
                    label, filter_str, total_targets, eta_str
                )
            )
            asyncio.create_task(_clean_msg(res_msg, 60))
            return

        if not target_ids:
            active_ops.pop(target_chat_id, None)
            res_msg = await progress.edit_text(
                message.lang["purge_complete"].format(label, 0, 0, 0)
            )
            asyncio.create_task(_clean_msg(res_msg, 60))
            return

        queue = asyncio.Queue()
        for uid in target_ids:
            queue.put_nowait(uid)

        circuit_breaker = asyncio.Event()
        circuit_breaker.set()

        workers = [
            asyncio.create_task(_worker(i, queue, target_chat_id, op, circuit_breaker, stats))
            for i in range(20)
        ]

        last_update = time.time()
        while not queue.empty():
            await asyncio.sleep(2)
            if target_chat_id not in active_ops:
                break

            now = time.time()
            if now - last_update >= 3.0:
                elapsed = now - start_time
                done_total = stats["total"]
                if done_total > 0:
                    eta_sec = (elapsed / done_total) * (total_targets - done_total)
                    eta_str = f"{int(eta_sec)}s" if eta_sec < 60 else f"{int(eta_sec // 60)}m {int(eta_sec % 60)}s"
                else:
                    eta_str = message.lang["purge_calc"]

                pct = (done_total / total_targets) * 100 if total_targets else 0

                try:
                    await progress.edit_text(
                        message.lang["purge_progress"].format(
                            done_total, total_targets, pct, eta_str, stats["done"]
                        )
                    )
                except Exception:
                    pass
                last_update = now

        await queue.join()
        for w in workers:
            w.cancel()

        if target_chat_id in active_ops:
            final_time = time.time() - start_time
            time_str = f"{int(final_time)}s" if final_time < 60 else f"{int(final_time // 60)}m {int(final_time % 60)}s"

            res_msg = await progress.edit_text(
                message.lang["purge_complete"].format(
                    label, stats["total"], stats["done"], stats["failed"]
                )
            )
            from anony import tasks
            task = asyncio.create_task(_clean_msg(res_msg, 60))
            tasks.append(task)
            task.add_done_callback(lambda t: tasks.remove(t) if t in tasks else None)

            # Audit Logging
            try:
                target_chat_obj = await app.get_chat(target_chat_id)
                chat_title = target_chat_obj.title or "Unknown Chat"

                filter_str = filter_type.capitalize() if filter_type else message.lang["purge_all_users"]
                log_text = message.lang["purge_log_report"].format(
                    chat_title, target_chat_id,
                    message.from_user.mention, message.from_user.id,
                    label, filter_str, stats["done"], time_str
                )
                await app.send_message(config.LOGGER_ID, log_text)
            except Exception as e:
                from anony import logger
                logger.warning(f"Failed to send purge audit log to LOGGER_ID ({config.LOGGER_ID}). Reason: {format_exception(e)}")

    except ChatAdminRequired:
        await progress.edit_text(message.lang["purge_admin_req"])
    except Exception as e:
        await progress.edit_text(message.lang["purge_error"].format(format_exception(e)))
    finally:
        active_ops.pop(target_chat_id, None)


@app.on_message(filters.command(["banall", "kickall", "unbanall"]) & (filters.group | filters.private) & app.sudoers & ~app.bl_users)
@lang.language()
async def handle_purge_cmds(_, m: Message):
    cmd = m.command[0].lower()

    op = "unban" if "unbanall" == cmd else "kick" if "kickall" == cmd else "ban"

    args = [arg.lower() for arg in m.command[1:]]
    is_test = "-test" in args

    filter_type = None
    if "bots" in args:
        filter_type = "bots"
    elif "deleted" in args:
        filter_type = "deleted"

    target_chat_id = m.chat.id
    target_arg = None

    for arg in args:
        if arg not in ("-test", "bots", "deleted"):
            target_arg = arg
            break

    if target_arg:
        try:
            if target_arg.startswith("-") or target_arg.isdigit():
                target_chat_id = int(target_arg)
            else:
                target_chat_id = target_arg

            chat = await app.get_chat(target_chat_id)
            target_chat_id = chat.id
        except Exception:
            return await m.reply_text("Invalid Chat ID or Username.")

    if m.chat.type == enums.ChatType.PRIVATE and target_chat_id == m.chat.id:
        return await m.reply_text("Please provide a group Chat ID or Username. Example: `/banall -1001234567890`")

    await purge_chat(m, target_chat_id, op, is_test, filter_type)


@app.on_message(filters.command("bhelp") & filters.private & app.sudoers & ~app.bl_users)
@lang.language()
async def bhelp_cmd(_, message: Message):
    await message.reply_text(message.lang["bhelp_text"])
