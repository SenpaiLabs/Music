from os import getenv
from dotenv import load_dotenv

load_dotenv()

class Config:
    def __init__(self):
        self.API_ID = int(getenv("API_ID", 0))
        self.API_HASH = getenv("API_HASH", "")

        self.BOT_TOKEN = getenv("BOT_TOKEN", "")
        self.IMGBB_API_KEY = getenv("IMGBB_API_KEY", "")
        self.MONGO_URL = getenv("MONGO_URL", "")
        self.SONG_CACHE_MONGO_URI = getenv("SONG_CACHE_MONGO_URI", "")

        self.LOGGER_ID = int(getenv("LOGGER_ID", 0))
        self.DB_CHANNEL = int(getenv("DB_CHANNEL", 0))
        self.OWNER_ID = int(getenv("OWNER_ID", 0))

        self.DURATION_LIMIT = int(getenv("DURATION_LIMIT", 60)) * 60
        self.QUEUE_LIMIT = int(getenv("QUEUE_LIMIT", 20))
        self.PLAYLIST_LIMIT = int(getenv("PLAYLIST_LIMIT", 20))

        self.SESSION1 = getenv("SESSION", "")
        self.SESSION2 = getenv("SESSION2", None)
        self.SESSION3 = getenv("SESSION3", None)

        self.SUPPORT_CHANNEL = getenv("SUPPORT_CHANNEL", "https://t.me/Senpai_Updates")
        self.SUPPORT_CHAT = getenv("SUPPORT_CHAT", "https://t.me/THE_DRAGON_SUPPORT")

        self.AUTO_LEAVE: bool = getenv("AUTO_LEAVE", "False").lower() == "true"
        self.AUTO_END: bool = getenv("AUTO_END", "True").lower() == "true"

        self.VIDEO_PLAY: bool = getenv("VIDEO_PLAY", "True").lower() == "true"

        self.LANG_CODE = getenv("LANG_CODE", "en")

        self.COOKIES_URL = [
            url for url in getenv("COOKIES_URL", "https://batbin.me/deejay").split(" ")
            if url and "batbin.me" in url
        ]
        self.PING_IMG = getenv("PING_IMG", "https://ibb.co/xSdP4GkB")
        self.START_IMG = getenv("START_IMG", "https://ibb.co/v4tWZdCh")

    def check(self):
        assert all([
            self.API_ID, self.API_HASH, self.BOT_TOKEN, self.IMGBB_API_KEY, 
            self.MONGO_URL, self.LOGGER_ID, self.OWNER_ID, self.SESSION1, 
            self.SONG_CACHE_MONGO_URI
        ]), "Missing required environment variables"
