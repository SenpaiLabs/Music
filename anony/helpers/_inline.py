# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic


from pyrogram import enums, types

from anony import app, config, lang
from anony.core.lang import lang_codes

ikm = types.InlineKeyboardMarkup
ikb = types.InlineKeyboardButton


def cancel_dl(text: str) -> types.InlineKeyboardMarkup:
    return ikm([[ikb(text=text, callback_data="cancel_dl", style=enums.ButtonStyle.DANGER)]])


def controls(
    chat_id: int,
    status: str = None,
    timer: str = None,
    autoplay: str = None,
    remove: bool = False,
) -> types.InlineKeyboardMarkup:
    keyboard = []
    if status:
        keyboard.append(
            [ikb(text=status, callback_data=f"controls status {chat_id}", style=enums.ButtonStyle.DANGER)]
        )
    else:
        if timer:
            keyboard.append(
                [ikb(text=timer, callback_data=f"controls status {chat_id}")]
            )
        if autoplay:
            keyboard.append(
                [ikb(text=autoplay, callback_data=f"controls autoplay {chat_id}")]
            )

    if not remove:
        keyboard.append(
            [
                ikb(text="▷", callback_data=f"controls resume {chat_id}", style=enums.ButtonStyle.PRIMARY),
                ikb(text="II", callback_data=f"controls pause {chat_id}", style=enums.ButtonStyle.PRIMARY),
                ikb(text="⥁", callback_data=f"controls replay {chat_id}", style=enums.ButtonStyle.PRIMARY),
                ikb(text="‣‣I", callback_data=f"controls skip {chat_id}", style=enums.ButtonStyle.PRIMARY),
                ikb(text="▢", callback_data=f"controls stop {chat_id}", style=enums.ButtonStyle.PRIMARY),
            ]
        )
    return ikm(keyboard)


def help_markup(_lang: dict, back: bool = False) -> types.InlineKeyboardMarkup:
    if back:
        rows = [
            [
                ikb(text=_lang["back"], callback_data="help back", style=enums.ButtonStyle.PRIMARY),
                ikb(text=_lang["close"], callback_data="help close", style=enums.ButtonStyle.DANGER),
            ]
        ]
    else:
        cbs = ["admins", "auth", "blist", "lang", "ping", "play", "queue", "stats", "sudo", "tgm", "mention", "manage"]
        buttons_list = [
            ikb(text=_lang[f"help_{i}"], callback_data=f"help {cb}")
            for i, cb in enumerate(cbs)
        ]
        rows = [buttons_list[i : i + 3] for i in range(0, len(buttons_list), 3)]

    return ikm(rows)


def lang_markup(_lang: str) -> types.InlineKeyboardMarkup:
    langs = lang.get_languages()

    buttons_list = [
        ikb(
            text=f"{name} ({code}) {'✔️' if code == _lang else ''}",
            callback_data=f"lang_change {code}",
            style=enums.ButtonStyle.PRIMARY if code == _lang else enums.ButtonStyle.DEFAULT,
        )
        for code, name in langs.items()
    ]
    rows = [buttons_list[i : i + 2] for i in range(0, len(buttons_list), 2)]
    return ikm(rows)


def ping_markup(text: str) -> types.InlineKeyboardMarkup:
    return ikm([[ikb(text=text, url=config.SUPPORT_CHAT)]])


def play_queued(chat_id: int, item_id: str, _text: str) -> types.InlineKeyboardMarkup:
    return ikm(
        [
            [
                ikb(
                    text=_text, callback_data=f"controls force {chat_id} {item_id}", style=enums.ButtonStyle.PRIMARY
                )
            ]
        ]
    )


def queue_markup(chat_id: int, _text: str, playing: bool) -> types.InlineKeyboardMarkup:
    _action = "pause" if playing else "resume"
    return ikm(
        [[ikb(text=_text, callback_data=f"controls {_action} {chat_id} q", style=enums.ButtonStyle.PRIMARY if playing else enums.ButtonStyle.SUCCESS)]]
    )


def settings_markup(
    lang_dict: dict, admin_only: bool, cmd_delete: bool, language: str, chat_id: int
) -> types.InlineKeyboardMarkup:
    return ikm(
        [
            [
                ikb(
                    text=lang_dict["play_mode"] + " ➜",
                    callback_data="settings",
                ),
                ikb(text=str(admin_only), callback_data="settings play", style=enums.ButtonStyle.PRIMARY),
            ],
            [
                ikb(
                    text=lang_dict["cmd_delete"] + " ➜",
                    callback_data="settings",
                ),
                ikb(text=str(cmd_delete), callback_data="settings delete", style=enums.ButtonStyle.PRIMARY),
            ],
            [
                ikb(
                    text=lang_dict["language"] + " ➜",
                    callback_data="settings",
                ),
                ikb(text=lang_codes[language], callback_data="language", style=enums.ButtonStyle.PRIMARY),
            ],
        ]
    )


def start_key(lang_dict: dict, private: bool = False) -> types.InlineKeyboardMarkup:
    rows = [
        [
            ikb(
                text=lang_dict["add_me"],
                url=f"https://t.me/{app.username}?startgroup=true",
                style=enums.ButtonStyle.PRIMARY,
            )
        ],
        [
            ikb(text=lang_dict["help"], callback_data="help"),
            ikb(text=lang_dict["language"], callback_data="language"),
        ],
        [
            ikb(text=lang_dict["support"], url=config.SUPPORT_CHAT),
            ikb(text=lang_dict["channel"], url=config.SUPPORT_CHANNEL),
        ],
    ]
    return ikm(rows)


def yt_key(link: str) -> types.InlineKeyboardMarkup:
    return ikm(
        [
            [
                ikb(text="❐", copy_text=link),
                ikb(text="Youtube", url=link),
            ],
        ]
    )
