# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic


from pyrogram import filters, types

from anony import app, db, lang, queue, yt
from anony.helpers import buttons, Media


_waiting_name: dict[int, tuple[int, float]] = {}
_playlist_state: dict[int, dict] = {}


async def _play_playlist(chat_id, m, playlist_name, user_id, songs, video=False):
    if not songs:
        return await m.reply_text(
            m.lang["pl_no_songs"].format(playlist_name)
        )
    _playlist_state[chat_id] = {
        "user_id": user_id,
        "playlist": playlist_name,
        "songs": list(songs),
        "index": 0,
        "video": video,
    }
    first = songs[0]
    from anony.plugins.play import play_hndlr
    url = first.get("url") or first.get("title")
    await play_hndlr(app, m, video=video, url=url)


async def advance_playlist(chat_id):
    state = _playlist_state.get(chat_id)
    if not state:
        return None
    state["index"] += 1
    if state["index"] >= len(state["songs"]):
        _playlist_state.pop(chat_id, None)
        return None
    song = state["songs"][state["index"]]
    video = state.get("video", False)
    file = Media(
        id=song["id"],
        title=song.get("title", ""),
        url=song.get("url", ""),
        duration=song.get("duration", "00:00"),
    )
    file.video = video
    file.user = "Playlist"
    return file


@app.on_message(
    filters.command(["playlist"]) & filters.group & ~app.bl_users
)
@lang.language()
async def _playlist_cmd(_, m: types.Message):
    if len(m.command) >= 2 and m.command[1].lower() == "play":
        name = " ".join(m.command[2:]) if len(m.command) > 2 else None
        user_id = m.from_user.id
        if not name:
            name = await db.get_active_playlist(user_id)
        doc = await db.get_playlists(user_id)
        if name not in doc["playlists"]:
            return await m.reply_text(m.lang["pl_not_found"])
        songs = doc["playlists"][name]
        return await _play_playlist(m.chat.id, m, name, user_id, songs, video=False)

    sent = await m.reply_text(
        m.lang["pl_menu_title"],
        reply_markup=buttons.playlist_markup_1(m.lang, m.from_user.id),
    )
    from anony.plugins.callbacks import _playlist_owners
    _playlist_owners[sent.id] = m.from_user.id


@app.on_message(
    filters.command(["vplaylist"]) & filters.group & ~app.bl_users
)
@lang.language()
async def _vplaylist_cmd(_, m: types.Message):
    name = " ".join(m.command[2:]) if len(m.command) > 2 else None
    user_id = m.from_user.id
    if not name:
        name = await db.get_active_playlist(user_id)
    doc = await db.get_playlists(user_id)
    if name not in doc["playlists"]:
        return await m.reply_text(m.lang["pl_not_found"])
    songs = doc["playlists"][name]
    await _play_playlist(m.chat.id, m, name, user_id, songs, video=True)


@app.on_message(
    filters.command(["createplaylist", "cplaylist"]) & filters.group & ~app.bl_users
)
@lang.language()
async def _create_playlist(_, m: types.Message):
    if len(m.command) < 2:
        return await m.reply_text(
            m.lang["pl_usage"]
        )
    name = " ".join(m.command[1:])
    if len(name.split()) > 2:
        return await m.reply_text(
            m.lang["pl_name_too_long"]
        )
    user_id = m.from_user.id
    doc = await db.get_playlists(user_id)
    custom_count = len([p for p in doc["playlists"] if p != "Liked Songs"])
    if custom_count >= 5:
        return await m.reply_text(
            m.lang["pl_limit_reached"]
        )
    created = await db.create_playlist(user_id, name)
    if not created:
        return await m.reply_text(
            m.lang["pl_exists"]
        )
    await m.reply_text(
        m.lang["pl_created"].format(name)
    )


@app.on_message(
    filters.command(["deleteplaylist", "dplaylist"]) & filters.group & ~app.bl_users
)
@lang.language()
async def _delete_playlist(_, m: types.Message):
    if len(m.command) < 2:
        return await m.reply_text(
            m.lang["pl_usage"]
        )
    name = " ".join(m.command[1:])
    if name == "Liked Songs":
        return await m.reply_text(
            m.lang["pl_default_guard"]
        )
    deleted = await db.delete_playlist(m.from_user.id, name)
    if not deleted:
        return await m.reply_text(
            m.lang["pl_not_found"]
        )
    await m.reply_text(
        m.lang["pl_deleted"].format(name)
    )


@app.on_message(
    filters.command(["removesong", "rsong", "rplaylist"]) & filters.group & ~app.bl_users
)
@lang.language()
async def _remove_song(_, m: types.Message):
    if len(m.command) < 3:
        return await m.reply_text(
            m.lang["pl_usage"]
        )
    playlist_name = m.command[1]
    song_query = " ".join(m.command[2:])
    user_id = m.from_user.id
    doc = await db.get_playlists(user_id)
    if playlist_name not in doc["playlists"]:
        return await m.reply_text(
            m.lang["pl_not_found"]
        )
    songs = doc["playlists"][playlist_name]
    target = next(
        (s for s in songs if song_query.lower() in s.get("title", "").lower()),
        None,
    )
    if not target:
        return await m.reply_text(
            m.lang["pl_song_not_found"]
        )
    await db.remove_song_from_playlist(user_id, playlist_name, target["id"])
    await m.reply_text(
        m.lang["pl_song_removed"].format(playlist_name)
    )


@app.on_message(
    filters.command(["showplaylist", "splaylist"]) & filters.group & ~app.bl_users
)
@lang.language()
async def _show_playlist(_, m: types.Message):
    user_id = m.from_user.id
    name = m.command[1] if len(m.command) > 1 else await db.get_active_playlist(user_id)
    doc = await db.get_playlists(user_id)
    if name not in doc["playlists"]:
        return await m.reply_text(
            m.lang["pl_not_found"]
        )
    songs = doc["playlists"][name]
    if not songs:
        return await m.reply_text(
            m.lang["pl_empty"]
        )

    start_idx, end_idx = 0, len(songs)
    if len(m.command) > 2:
        range_arg = m.command[2]
        if "-" in range_arg:
            parts = range_arg.split("-", 1)
            try:
                start_idx = max(int(parts[0]) - 1, 0)
                end_idx = min(int(parts[1]), len(songs))
            except ValueError:
                pass
        else:
            try:
                end_idx = min(int(range_arg), len(songs))
            except ValueError:
                pass

    text = m.lang["pl_show_title"].format(name, len(songs))
    for i, song in enumerate(songs[start_idx:end_idx], start=start_idx + 1):
        text += m.lang["pl_show_item"].format(
            i, song.get("url", "#"), song.get("title", "?"), song.get("duration", "00:00")
        )
    text = text[:4000]
    await m.reply_text(text, disable_web_page_preview=True)


@app.on_message(filters.group & filters.text & ~app.bl_users, group=8)
@lang.language()
async def _playlist_name_input(_, m: types.Message):
    if m.from_user.id not in _waiting_name:
        return
    chat_id, _ = _waiting_name.pop(m.from_user.id)
    if m.chat.id != chat_id:
        return
    name = m.text.strip()
    if len(name.split()) > 2:
        return await m.reply_text(
            m.lang["pl_name_too_long"]
        )
    user_id = m.from_user.id
    doc = await db.get_playlists(user_id)
    custom_count = len([p for p in doc["playlists"] if p != "Liked Songs"])
    if custom_count >= 5:
        return await m.reply_text(
            m.lang["pl_limit_reached"]
        )
    created = await db.create_playlist(user_id, name)
    if not created:
        return await m.reply_text(
            m.lang["pl_exists"]
        )
    await m.reply_text(
        m.lang["pl_created"].format(name)
    )
