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
from anony.helpers import reload_admins

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


async def purge_chat(message: Message, op: str, is_test: bool, filter_type: str) -> None:
    chat_id = message.chat.id
    
    if not message.from_user or message.from_user.id not in app.sudoers:
        return await message.reply_text(message.lang["user_no_perms"])

    if chat_id in active_ops:
        return await message.reply_text(message.lang["purge_active"])

    try:
        me = await app.get_chat_member(chat_id, app.id)
        if me.status != ChatMemberStatus.OWNER and not (
            me.privileges and getattr(me.privileges, "can_restrict_members", False)
        ):
            return await message.reply_text(message.lang["purge_rights"])
    except Exception:
        return await message.reply_text(message.lang["purge_rights"])

    active_ops[chat_id] = op
    try:
        await app.send_reaction(chat_id, message.id, "🍓")
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
            admins = await reload_admins(chat_id)
            async for member in app.get_chat_members(chat_id):
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
            async for member in app.get_chat_members(chat_id, filter=enums.ChatMembersFilter.BANNED):
                if member.user:
                    target_ids.append(member.user.id)
                    
        total_targets = len(target_ids)
        
        # Dry-Run Mode
        if is_test:
            active_ops.pop(chat_id, None)
            eta_sec = total_targets * 0.15 # Rough estimate based on concurrency throughput
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
            active_ops.pop(chat_id, None)
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
            asyncio.create_task(_worker(i, queue, chat_id, op, circuit_breaker, stats))
            for i in range(20)
        ]

        last_update = time.time()
        while not queue.empty():
            await asyncio.sleep(2)
            if chat_id not in active_ops:
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

        if chat_id in active_ops:
            final_time = time.time() - start_time
            time_str = f"{int(final_time)}s" if final_time < 60 else f"{int(final_time // 60)}m {int(final_time % 60)}s"
            
            res_msg = await progress.edit_text(
                message.lang["purge_complete"].format(
                    label, stats["total"], stats["done"], stats["failed"]
                )
            )
            asyncio.create_task(_clean_msg(res_msg, 60))

            # Audit Logging
            try:
                filter_str = filter_type.capitalize() if filter_type else message.lang["purge_all_users"]
                log_text = message.lang["purge_log_report"].format(
                    message.chat.title, chat_id,
                    message.from_user.mention, message.from_user.id,
                    label, filter_str, stats["done"], time_str
                )
                await app.send_message(config.LOGGER_ID, log_text)
            except Exception:
                pass

    except ChatAdminRequired:
        await progress.edit_text(message.lang["purge_admin_req"])
    except Exception as e:
        await progress.edit_text(message.lang["purge_error"].format(e))
    finally:
        active_ops.pop(chat_id, None)


@app.on_message(filters.command(["banall", "kickall", "unbanall"]) & filters.group & app.sudoers & ~app.bl_users)
@lang.language()
async def handle_purge_cmds(_, m: Message):
    cmd_text = m.text.lower().split()
    cmd = cmd_text[0]
    
    op = "ban" if "banall" in cmd else "kick" if "kickall" in cmd else "unban"
    
    is_test = "-test" in cmd_text
    filter_type = None
    if "bots" in cmd_text:
        filter_type = "bots"
    elif "deleted" in cmd_text:
        filter_type = "deleted"
        
    await purge_chat(m, op, is_test, filter_type)
