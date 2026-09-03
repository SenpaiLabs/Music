# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic


import json
from functools import wraps
from pathlib import Path

from pyrogram import errors

from anony import db, logger

lang_codes = {
    "ar": "العربية",
    "de": "Deutsch",
    "en": "English",
    "es": "Español",
    "fr": "Français",
    "hi": "हिन्दी",
    "ja": "日本語",
    "my": "မြန်မာဘာသာ",
    "pa": "ਪੰਜਾਬੀ",
    "pt": "Português",
    "ru": "Русский",
    "tr": "Türkçe",
    "zh": "中文"
}


class Language:
    """
    Language class for managing multilingual support using JSON language files.
    """

    def __init__(self):
        self.lang_codes = lang_codes
        self.lang_dir = Path("anony/locales")
        self.languages = self.load_files()

    def load_files(self):
        languages = {f.stem: json.loads(f.read_text("utf-8")) for f in self.lang_dir.glob("*.json")}
        logger.info(f"Loaded languages: {', '.join(languages)}")
        return languages

    async def get_lang(self, chat_id: int) -> dict:
        lang_code = await db.get_lang(chat_id)
        return self.languages[lang_code]

    def get_languages(self) -> dict:
        return {code: self.lang_codes[code] for code in sorted(self.languages)}

    def language(self):
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                fallen = next((a for a in args if hasattr(a, "chat") or hasattr(a, "message")), None)

                if not fallen.from_user:
                    return

                chat = getattr(fallen, "chat", None) or getattr(getattr(fallen, "message", None), "chat", None)
                if not chat: return

                if chat.id in db.blacklisted:
                    logger.info(f"Chat {chat.id} is blacklisted, leaving...")
                    return await chat.leave()

                lang_code = await db.get_lang(chat.id)
                lang_dict = self.languages[lang_code]

                setattr(fallen, "lang", lang_dict)
                try:
                    return await func(*args, **kwargs)
                except (
                    errors.FloodWait, errors.SlowmodeWait,
                    errors.ChannelInvalid, errors.ChannelPrivate,
                    errors.MessageIdInvalid, errors.MessageNotModified,
                    errors.Forbidden, errors.ChatWriteForbidden,
                ):
                    return

            return wrapper

        return decorator
