from os import getenv
from dotenv import load_dotenv

load_dotenv()

class Config:
    def __init__(self):
        self.API_ID = int(getenv("API_ID", 35660683))
        self.API_HASH = getenv("API_HASH", "7afb42cd73fb5f3501062ffa6a1f87f7")

        self.BOT_TOKEN = getenv("BOT_TOKEN", "8999128627:AAHwO--RCPU_Drpzilq1BPzlEYoviuTyFRs")
        self.MONGO_URL = getenv("MONGO_URL", "mongodb+srv://piyush000yogi_db_user:rkhZr3vh1j06oCF9@piyush.t7w4qvr.mongodb.net/?retryWrites=true&w=majority")

        self.LOGGER_ID = int(getenv("LOGGER_ID", -1003150808065))
        self.OWNER_ID = int(getenv("OWNER_ID", 8900240311))

        self.DURATION_LIMIT = int(getenv("DURATION_LIMIT", 60)) * 60
        self.QUEUE_LIMIT = int(getenv("QUEUE_LIMIT", 20))
        self.PLAYLIST_LIMIT = int(getenv("PLAYLIST_LIMIT", 20))

        self.SESSION1 = getenv("SESSION", "BQHh-uAAKIA8NhjtCifC3xxoZcljo7h4srmS_ZgTtdbQL1IstVy8564WMHMYgpOj7OSj84AFnXrXZ911EDhhJduodnAY97rcmGNdr6YajD1UXJRPqmUF4xYjSvGTTPuqSlHFPLUMUnAhN7HTNdz7NVZIosiE9NOogIJNGIQ0hi7PJgt3L1ikj_HQWF_p636CT06dOQnB5COIpiIDjkmUs33-eZ_DlpKV9qeX45soUUxS3sxajyckHsDZEBCUvmhQhlQDU6jklG1mMSitUEyiGFkKEHLI0hIF9D4g-6q-zzCeDgfwMb9wLwFsJ5BOFo3lUW3MekhqzQLuQeiuEutSw3_3nNmeUgAAAAGxc_XUAA")
        self.SESSION2 = getenv("SESSION2", None)
        self.SESSION3 = getenv("SESSION3", None)

        self.SUPPORT_CHANNEL = getenv("SUPPORT_CHANNEL", "https://t.me/Senpai_Updates")
        self.SUPPORT_CHAT = getenv("SUPPORT_CHAT", "https://t.me/THE_DRAGON_SUPPORT")

        self.AUTO_LEAVE: bool = getenv("AUTO_LEAVE", "False").lower() == "true"
        self.AUTO_END: bool = getenv("AUTO_END", "False").lower() == "true"

        self.THUMB_GEN: bool = getenv("THUMB_GEN", "False").lower() == "true"
        self.VIDEO_PLAY: bool = getenv("VIDEO_PLAY", "True").lower() == "true"

        self.LANG_CODE = getenv("LANG_CODE", "en")

        self.COOKIES_URL = [
            url for url in getenv("COOKIES_URL", "https://batbin.me/deejay").split(" ")
            if url and "batbin.me" in url
        ]
        self.DEFAULT_THUMB = getenv("DEFAULT_THUMB", "https://te.legra.ph/file/3e40a408286d4eda24191.jpg")
        self.PING_IMG = getenv("PING_IMG", "https://ibb.co/xSdP4GkB")
        self.START_IMG = getenv("START_IMG", "https://ibb.co/v4tWZdCh")

    def check(self):
        missing = [
            var
            for var in ["API_ID", "API_HASH", "BOT_TOKEN", "MONGO_URL", "LOGGER_ID", "OWNER_ID", "SESSION1"]
            if not getattr(self, var)
        ]
        if missing:
            raise SystemExit(f"Missing required environment variables: {', '.join(missing)}")
