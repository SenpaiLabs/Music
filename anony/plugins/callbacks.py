# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic


import re
from time import time

from pyrogram import errors, filters, types

from anony import anon, app, db, lang, queue, tg, yt
from anony.helpers import admin_check, buttons, can_manage_vc


_leaderboard_cooldown: dict[int, float] = {}
LEADERBOARD_COOLDOWN_SECONDS = 3


@app.on_callback_query(filters.regex("cancel_dl") & ~app.bl_users)
@lang.language()
async def cancel_dl(_, query: types.CallbackQuery):
    await query.answer()
    await tg.cancel(query)


@app.on_callback_query(filters.regex("controls") & ~app.bl_users)
@lang.language()
@can_manage_vc
async def _controls(_, query: types.CallbackQuery):
    args = query.data.split()
    action, chat_id = args[1], int(args[2])
    qaction = len(args) == 4
    user = query.from_user.mention

    if not await db.get_call(chat_id):
        try:
            return await query.answer(query.lang["not_playing"], show_alert=True)
        except errors.QueryIdInvalid:
            try:
                await query.message.delete()
            except Exception:
                pass
            return

    if action == "status":
        return await query.answer()

    if action == "autoplay":
        status = not await db.get_autoplay(chat_id)
        await db.set_autoplay(chat_id, status)
        autoplay_text = query.lang["autoplay_btn"].format(
            query.lang["on"] if status else query.lang["off"]
        )
        await query.answer(
            query.lang["autoplay_on"] if status else query.lang["autoplay_off"]
        )
        return await query.edit_message_reply_markup(
            reply_markup=buttons.controls(
                chat_id,
                autoplay=autoplay_text,
                add_playlist=query.lang["pl_btn"],
            )
        )

    if action == "addplaylist":
        user_id = query.from_user.id
        media = queue.get_current(chat_id)
        if not media:
            return await query.answer(query.lang["not_playing"], show_alert=True)
        active = await db.get_active_playlist(user_id)
        track_dict = {
            "id": media.id,
            "title": media.title or "",
            "url": media.url or "",
            "duration": media.duration or "00:00",
        }
        added = await db.add_song_to_playlist(user_id, active, track_dict)
        if added:
            return await query.answer(
                query.lang["pl_song_added"].format(active),
                show_alert=True,
            )
        return await query.answer(
            query.lang["pl_already_in"].format(active),
            show_alert=True,
        )

    await query.answer(query.lang["processing"], show_alert=True)

    if action == "pause":
        if not await db.playing(chat_id):
            return await query.answer(
                query.lang["play_already_paused"], show_alert=True
            )
        await anon.pause(chat_id)
        if qaction:
            return await query.edit_message_reply_markup(
                reply_markup=buttons.queue_markup(chat_id, query.lang["paused"], False)
            )
        status = query.lang["paused"]
        reply = query.lang["play_paused"].format(user)

    elif action == "resume":
        if await db.playing(chat_id):
            return await query.answer(query.lang["play_not_paused"], show_alert=True)
        await anon.resume(chat_id)
        if qaction:
            return await query.edit_message_reply_markup(
                reply_markup=buttons.queue_markup(chat_id, query.lang["playing"], True)
            )
        status = None
        reply = query.lang["play_resumed"].format(user)

    elif action == "skip":
        await anon.play_next(chat_id)
        status = query.lang["skipped"]
        reply = query.lang["play_skipped"].format(user)

    elif action == "force":
        pos, media = queue.check_item(chat_id, args[3])
        if not media or pos == -1:
            return await query.edit_message_text(query.lang["play_expired"])

        m_id = queue.get_current(chat_id).message_id
        queue.force_add(chat_id, media, remove=pos)
        try:
            await app.delete_messages(
                chat_id=chat_id, message_ids=[m_id, media.message_id], revoke=True
            )
            media.message_id = None
        except Exception:
            pass

        msg = await app.send_message(chat_id=chat_id, text=query.lang["play_next"])
        if not media.file_path:
            media.file_path = await yt.download(media.id, video=media.video)
        media.message_id = msg.id
        return await anon.play_media(chat_id, msg, media)

    elif action == "replay":
        media = queue.get_current(chat_id)
        media.user = user
        await anon.replay(chat_id)
        status = query.lang["replayed"]
        reply = query.lang["play_replayed"].format(user)

    elif action == "stop":
        await anon.stop(chat_id)
        status = query.lang["stopped"]
        reply = query.lang["play_stopped"].format(user)

    try:
        if action in ["skip", "replay", "stop"]:
            await query.message.reply_text(reply, quote=False)
            await query.message.delete()
        else:
            source = query.message.caption or query.message.text
            mtext = re.sub(
                r"\n\n<blockquote>.*?</blockquote>",
                "",
                source.html,
                flags=re.DOTALL,
            )
            keyboard = buttons.controls(chat_id, status=status)
            await query.edit_message_text(
                f"{mtext}\n\n<blockquote>{reply}</blockquote>", reply_markup=keyboard
            )
    except Exception:
        pass


@app.on_callback_query(filters.regex("help") & ~app.bl_users)
@lang.language()
async def _help(_, query: types.CallbackQuery):
    data = query.data.split()
    if len(data) == 1:
        return await query.answer(url=f"https://t.me/{app.username}?start=help")

    if data[1] == "back":
        return await query.edit_message_text(
            text=query.lang["help_menu"], reply_markup=buttons.help_markup(query.lang)
        )
    elif data[1] == "close":
        try:
            await query.message.delete()
            return await query.message.reply_to_message.delete()
        except Exception:
            return

    await query.edit_message_text(
        text=query.lang[f"help_{data[1]}"],
        reply_markup=buttons.help_markup(query.lang, True),
    )


_playlist_owners: dict[int, int] = {}


@app.on_callback_query(filters.regex("playlist") & ~app.bl_users)
@lang.language()
async def _playlist_cb(_, query: types.CallbackQuery):
    data = query.data.split(maxsplit=2)
    action = data[1] if len(data) > 1 else ""

    if action in ("soon1", "soon2"):
        return await query.answer(
            query.lang["coming_soon"], show_alert=True
        )

    if action == "menu":
        msg = await query.edit_message_text(
            text=query.lang["pl_menu_title"],
            reply_markup=buttons.playlist_markup_1(query.lang, query.from_user.id),
        )
        _playlist_owners[msg.id] = query.from_user.id
        return

    owner_id = int(data[2].split()[0]) if len(data) > 2 else 0
    if owner_id and query.from_user.id != owner_id:
        return await query.answer(
            query.lang["pl_not_your_menu"],
            show_alert=True,
        )

    if action == "close":
        _playlist_owners.pop(query.message.id, None)
        await query.answer()
        try:
            await query.message.delete()
        except Exception:
            pass
        return

    if action == "back":
        await query.answer()
        return await query.edit_message_text(
            text=query.lang["pl_menu_title"],
            reply_markup=buttons.playlist_markup_1(query.lang, owner_id),
        )

    if action == "howto":
        await query.answer()
        return await query.edit_message_text(
            text=query.lang["pl_howto"],
            reply_markup=buttons.playlist_markup_1(query.lang, owner_id),
        )

    if action == "list":
        await query.answer()
        doc = await db.get_playlists(owner_id)
        playlists = list(doc["playlists"].keys())
        active = doc.get("active", "Liked Songs")
        custom_count = len([p for p in playlists if p != "Liked Songs"])
        return await query.edit_message_text(
            text=query.lang["pl_select_title"],
            reply_markup=buttons.playlist_markup_2(
                query.lang, owner_id, playlists, active, custom_count < 5
            ),
        )

    if action == "select":
        parts = query.data.split(maxsplit=3)
        name = parts[3] if len(parts) > 3 else "Liked Songs"
        await db.set_active_playlist(owner_id, name)
        await query.answer(
            query.lang["pl_selected"].format(name)
        )
        doc = await db.get_playlists(owner_id)
        playlists = list(doc["playlists"].keys())
        custom_count = len([p for p in playlists if p != "Liked Songs"])
        return await query.edit_message_reply_markup(
            reply_markup=buttons.playlist_markup_2(
                query.lang, owner_id, playlists, name, custom_count < 5
            ),
        )

    if action == "create":
        from anony.plugins.playlist import _waiting_name
        import asyncio
        import time
        
        now = time.time()
        _waiting_name[owner_id] = (query.message.chat.id, now)
        
        async def clear_state():
            await asyncio.sleep(60)
            if _waiting_name.get(owner_id) and _waiting_name[owner_id][1] == now:
                _waiting_name.pop(owner_id, None)
                
        asyncio.create_task(clear_state())
        
        return await query.answer(
            query.lang["pl_enter_name"],
            show_alert=True,
        )


@app.on_callback_query(filters.regex("leaderboard") & ~app.bl_users)
@lang.language()
async def _leaderboard_cb(_, query: types.CallbackQuery):
    data = query.data.split()
    action = data[1]

    if action not in ("close", "back"):
        now = time()
        last = _leaderboard_cooldown.get(query.from_user.id, 0)
        remaining = LEADERBOARD_COOLDOWN_SECONDS - (now - last)
        if remaining > 0:
            return await query.answer(
                query.lang["leaderboard_cooldown"].format(int(remaining) + 1),
                show_alert=True,
            )
        _leaderboard_cooldown[query.from_user.id] = now

    if action == "close":
        await query.answer()
        try:
            await query.message.delete()
        except Exception:
            pass
        return

    if action == "back":
        chat_id = int(data[2])
        await query.answer()
        return await query.edit_message_text(
            text=query.lang["leaderboard_menu"],
            reply_markup=buttons.leaderboard_markup(query.lang, chat_id),
        )

    if action == "users":
        chat_id = int(data[2])
        await query.answer()
        return await query.edit_message_text(
            text=query.lang["leaderboard_choose"],
            reply_markup=buttons.leaderboard_period_markup(query.lang, chat_id),
        )

    if action == "groups":
        await query.answer(query.lang["processing"])
        top = await db.get_top_chats()
        if not top:
            return await query.edit_message_text(
                text=query.lang["leaderboard_empty"],
                reply_markup=buttons.leaderboard_result_markup(
                    query.lang, query.message.chat.id, groups=True
                ),
            )

        text = query.lang["leaderboard_groups_title"]
        for i, entry in enumerate(top, start=1):
            name = entry.get("title")
            if not name:
                try:
                    name = (await app.get_chat(entry["_id"])).title
                except Exception:
                    name = str(entry["_id"])
            text += query.lang["leaderboard_group_item"].format(i, name, entry["count"])

        return await query.edit_message_text(
            text=text,
            reply_markup=buttons.leaderboard_result_markup(
                query.lang, query.message.chat.id, groups=True
            ),
        )

    if action == "period":
        chat_id, period = int(data[2]), data[3]
        await query.answer(query.lang["processing"])
        top = await db.get_top_users(chat_id, period)
        if not top:
            return await query.edit_message_text(
                text=query.lang["leaderboard_empty"],
                reply_markup=buttons.leaderboard_period_markup(query.lang, chat_id),
            )

        text = query.lang[f"leaderboard_{period}_title"]
        for i, entry in enumerate(top, start=1):
            mention = entry.get("name")
            if not mention:
                try:
                    member = await app.get_chat_member(chat_id, entry["_id"])
                    mention = member.user.mention
                except Exception:
                    mention = str(entry["_id"])
            text += query.lang["leaderboard_user_item"].format(i, mention, entry["count"])

        try:
            return await query.edit_message_text(
                text=text,
                reply_markup=buttons.leaderboard_period_markup(query.lang, chat_id),
            )
        except errors.RPCError:
            safe_text = text.replace("tg://openmessage?user_id=", "tg://user?id=")
            return await query.edit_message_text(
                text=safe_text,
                reply_markup=buttons.leaderboard_period_markup(query.lang, chat_id),
            )


@app.on_callback_query(filters.regex("settings") & ~app.bl_users)
@lang.language()
@admin_check
async def _settings_cb(_, query: types.CallbackQuery):
    cmd = query.data.split()
    if len(cmd) == 1:
        return await query.answer()
    await query.answer(query.lang["processing"], show_alert=True)

    chat_id = query.message.chat.id
    _admin = await db.get_play_mode(chat_id)
    _delete = await db.get_cmd_delete(chat_id)
    _language = await db.get_lang(chat_id)

    if cmd[1] == "delete":
        _delete = not _delete
        await db.set_cmd_delete(chat_id, _delete)
    elif cmd[1] == "play":
        await db.set_play_mode(chat_id, _admin)
        _admin = not _admin
    await query.edit_message_reply_markup(
        reply_markup=buttons.settings_markup(
            query.lang,
            _admin,
            _delete,
            _language,
            chat_id,
        )
    )

