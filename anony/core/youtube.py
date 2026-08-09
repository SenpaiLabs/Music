# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic


import os
import re
import yt_dlp
import random
import asyncio
import aiohttp
from pathlib import Path

from py_yt import Playlist, VideosSearch

from anony import logger
from anony.helpers import Track, utils


class YTDLLogger:
    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        pass


class YouTube:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.cookies = []
        self.checked = False
        self.cookie_dir = "anony/cookies"
        self.warned = False
        self._locks = {}
        self.regex = re.compile(
            r"(https?://)?(www\.|m\.|music\.)?"
            r"(youtube\.com/(watch\?v=|shorts/|playlist\?list=)|youtu\.be/)"
            r"([A-Za-z0-9_-]{11}|PL[A-Za-z0-9_-]+)([&?][^\s]*)?"
        )
        self.iregex = re.compile(
            r"https?://(?:www\.|m\.|music\.)?(?:youtube\.com|youtu\.be)"
            r"(?!/(watch\?v=[A-Za-z0-9_-]{11}|shorts/[A-Za-z0-9_-]{11}"
            r"|playlist\?list=PL[A-Za-z0-9_-]+|[A-Za-z0-9_-]{11}))\S*"
        )

    def get_cookies(self):
        if not self.checked:
            for file in os.listdir(self.cookie_dir):
                if file.endswith(".txt"):
                    self.cookies.append(f"{self.cookie_dir}/{file}")
            self.checked = True
        if not self.cookies:
            if not self.warned:
                self.warned = True
                logger.warning("Cookies are missing; downloads might fail.")
            return None
        return random.choice(self.cookies)

    async def save_cookies(self, urls: list[str]) -> None:
        logger.info("Saving cookies from urls...")
        async with aiohttp.ClientSession() as session:
            for url in urls:
                name = url.split("/")[-1]
                link = "https://batbin.me/raw/" + name
                async with session.get(link) as resp:
                    resp.raise_for_status()
                    with open(f"{self.cookie_dir}/{name}.txt", "wb") as fw:
                        fw.write(await resp.read())
        logger.info(f"Cookies saved in {self.cookie_dir}.")

    def valid(self, url: str) -> bool:
        return bool(re.match(self.regex, url))

    def invalid(self, url: str) -> bool:
        return bool(re.match(self.iregex, url))

    async def search(self, query: str, m_id: int, video: bool = False) -> Track | None:
        try:
            _search = VideosSearch(query, limit=1, with_live=False)
            results = await _search.next()
        except Exception:
            return None
        if results and results["result"]:
            data = results["result"][0]
            return Track(
                id=data.get("id"),
                channel_name=data.get("channel", {}).get("name"),
                duration=data.get("duration"),
                duration_sec=utils.to_seconds(data.get("duration")),
                message_id=m_id,
                title=data.get("title")[:25],
                thumbnail=data.get("thumbnails", [{}])[-1].get("url").split("?")[0],
                url=data.get("link"),
                view_count=data.get("viewCount", {}).get("short"),
                video=video,
            )
        return None

    async def playlist(self, limit: int, user: str, url: str, video: bool) -> list[Track | None]:
        tracks = []
        try:
            plist = await Playlist.get(url)
            for data in plist["videos"][:limit]:
                track = Track(
                    id=data.get("id"),
                    channel_name=data.get("channel", {}).get("name", ""),
                    duration=data.get("duration"),
                    duration_sec=utils.to_seconds(data.get("duration")),
                    title=data.get("title")[:25],
                    thumbnail=data.get("thumbnails")[-1].get("url").split("?")[0],
                    url=data.get("link").split("&list=")[0],
                    user=user,
                    view_count="",
                    video=video,
                )
                tracks.append(track)
        except Exception:
            pass
        return tracks

    async def autoplay(self, video_id: str, history: set, video: bool = False) -> Track | None:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"https://www.youtube.com/watch?v={video_id}") as resp:
                    if resp.status != 200:
                        return None
                    text = await resp.text()
                    
            match = re.search(r'var ytInitialData = (\{.*?\});</script>', text)
            if not match:
                return None
                
            import json
            data = json.loads(match.group(1))
            
            def find_videos(obj):
                videos = []
                if isinstance(obj, dict):
                    if "compactVideoRenderer" in obj:
                        videos.append(("compact", obj["compactVideoRenderer"]))
                    if "lockupViewModel" in obj:
                        videos.append(("lockup", obj["lockupViewModel"]))
                    for k, v in obj.items():
                        videos.extend(find_videos(v))
                elif isinstance(obj, list):
                    for item in obj:
                        videos.extend(find_videos(item))
                return videos
                
            renderers = find_videos(data)
            next_id = None
            title = "Unknown"
            duration = "0:00"
            duration_sec = 0
            uploader = "Autoplay"
            thumbnail = ""
            view_count = ""
            
            for r_type, rnd in renderers:
                if r_type == "compact":
                    vid = rnd.get("videoId")
                    if vid and vid != video_id and vid not in history:
                        next_id = vid
                        t_obj = rnd.get("title", {})
                        title = t_obj.get("simpleText") or (t_obj.get("runs", [{}])[0].get("text", "Unknown"))
                        
                        l_obj = rnd.get("lengthText", {})
                        duration = l_obj.get("simpleText") or (l_obj.get("runs", [{}])[0].get("text", "0:00"))
                        
                        u_obj = rnd.get("shortBylineText", {})
                        uploader = u_obj.get("simpleText") or (u_obj.get("runs", [{}])[0].get("text", uploader))
                        
                        thumbs = rnd.get("thumbnail", {}).get("thumbnails", [])
                        if thumbs:
                            thumbnail = thumbs[-1].get("url", "")
                            
                        v_obj = rnd.get("viewCountText", {})
                        view_count = v_obj.get("simpleText") or (v_obj.get("runs", [{}])[0].get("text", ""))
                        break
                        
                elif r_type == "lockup":
                    vid = rnd.get("contentId")
                    if vid and vid != video_id and vid not in history:
                        next_id = vid
                        m_obj = rnd.get("metadata", {}).get("lockupMetadataViewModel", {})
                        title = m_obj.get("title", {}).get("content", "Unknown")
                        break

            if not next_id:
                return None
                
            parts = duration.split(":")
            if len(parts) == 3:
                duration_sec = int(parts[0])*3600 + int(parts[1])*60 + int(parts[2])
            elif len(parts) == 2:
                duration_sec = int(parts[0])*60 + int(parts[1])

            return Track(
                id=next_id,
                channel_name=uploader,
                duration=duration,
                duration_sec=duration_sec,
                message_id=0,
                title=title[:25],
                thumbnail=thumbnail.split("?")[0] if thumbnail else "",
                url=self.base + next_id,
                view_count=view_count,
                video=video,
            )
        except Exception as e:
            logger.warning(f"Autoplay fetch failed: {e}")
            return None

    @staticmethod
    def format_duration(seconds: int) -> str:
        if seconds <= 0:
            return "0:00"
        h, rem = divmod(seconds, 3600)
        m, s = divmod(rem, 60)
        return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

    async def download(
        self, video_id: str, video: bool = False, title: str = "", duration: str = "", duration_sec: int = 0
    ) -> str | None:
        url = self.base + video_id
        ext = "mp4" if video else "webm"
        filename = f"downloads/{video_id}.{ext}"

        if video_id not in self._locks:
            self._locks[video_id] = asyncio.Lock()

        async with self._locks[video_id]:
            if Path(filename).exists():
                return filename

            from anony import app, config, db

            if config.DB_CHANNEL:
                try:
                    cache_data = await db.get_song_cache(video_id, video)
                    if cache_data:
                        try:
                            if cache_data.get("file_id"):
                                downloaded_path = await app.download_media(cache_data["file_id"], file_name=filename)
                                if downloaded_path:
                                    await db.increment_play_count(video_id, video)
                                    return downloaded_path
                        except Exception:
                            pass
                        
                        if cache_data.get("msg_id"):
                            try:
                                msg = await app.get_messages(config.DB_CHANNEL, cache_data["msg_id"])
                                if msg and (msg.audio or msg.video or msg.document):
                                    downloaded_path = await app.download_media(msg, file_name=filename)
                                    if downloaded_path:
                                        await db.increment_play_count(video_id, video)
                                        return downloaded_path
                            except Exception as e:
                                logger.warning(f"Cache fallback download failed for {video_id}: {e}")
                except Exception as e:
                    logger.warning(f"Cache check failed for {video_id}: {e}")

            cookie = self.get_cookies()
            base_opts = {
                "outtmpl": "downloads/%(id)s.%(ext)s",
                "quiet": True,
                "noplaylist": True,
                "geo_bypass": True,
                "no_warnings": True,
                "overwrites": False,
                "nocheckcertificate": True,
                "cookiefile": cookie,
                "logger": YTDLLogger(),
            }

            if video:
                ydl_opts = {
                    **base_opts,
                    "format": "(bestvideo[height<=?720][width<=?1280][ext=mp4])+(bestaudio)/best[height<=?720]",
                    "merge_output_format": "mp4",
                }
            else:
                ydl_opts = {
                    **base_opts,
                    "format": "bestaudio[ext=webm][acodec=opus]/bestaudio/best",
                }

            def _download():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    try:
                        ydl.download([url])
                    except (yt_dlp.utils.DownloadError, yt_dlp.utils.ExtractorError):
                        return None
                    except Exception as ex:
                        logger.warning("Download failed: %s", ex)
                        return None
                return filename

            result_filename = await asyncio.to_thread(_download)

            if result_filename and config.DB_CHANNEL:
                async def _upload_to_cache():
                    try:
                        sent = None
                        if video:
                            sent = await app.send_video(config.DB_CHANNEL, video=result_filename, duration=duration_sec)
                        else:
                            sent = await app.send_audio(config.DB_CHANNEL, audio=result_filename, title=title, duration=duration_sec)
                        
                        if sent:
                            media = sent.video or sent.audio or sent.voice or sent.document
                            if not media:
                                logger.warning(f"Failed to find media attribute in sent message for {video_id}")
                                return
                            
                            file_id = getattr(media, "file_id", None)
                            if file_id:
                                await db.save_song_cache(
                                    video_id, video, sent.id, file_id, title, duration, duration_sec
                                )
                    except Exception as e:
                        logger.warning(f"Background cache upload failed for {video_id}: {e}")
                
                asyncio.create_task(_upload_to_cache())

            return result_filename

