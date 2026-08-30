# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic


import os
import re
import time
import yt_dlp
import asyncio
import aiohttp
import itertools
import contextlib
from pathlib import Path
from difflib import SequenceMatcher

from py_yt import Playlist

from anony import logger
from anony.helpers import Track, utils


class YouTube:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.cookies = []
        self.checked = False
        self.cookie_dir = "anony/cookies"
        self.warned = False
        self._locks = {}
        self._cookie_cycle = None
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
            if self.cookies:
                self._cookie_cycle = itertools.cycle(self.cookies)
        if not self.cookies:
            if not self.warned:
                self.warned = True
                logger.warning("Cookies are missing; downloads might fail.")
            return None
        return next(self._cookie_cycle)

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
            def _extract():
                cookie = self.get_cookies()
                opts = {
                    "format": "bestaudio",
                    "quiet": True,
                    "noplaylist": True,
                    "geo_bypass": True,
                    "nocheckcertificate": True,
                    "extract_flat": True,
                    "force_ipv4": True,
                }
                if cookie:
                    opts["cookiefile"] = cookie

                search_query = query if self.valid(query) or "youtube.com" in query else f"ytsearch1:{query}"
                with yt_dlp.YoutubeDL(opts) as ydl:
                    return ydl.extract_info(search_query, download=False)

            info = await asyncio.to_thread(_extract)
            if not info:
                return None

            if "entries" in info:
                if not info["entries"]:
                    return None
                data = info["entries"][0]
            else:
                data = info

            return Track(
                id=data.get("id"),
                channel_name=data.get("uploader"),
                duration=time.strftime("%M:%S", time.gmtime(int(data.get("duration") or 0))),
                duration_sec=int(data.get("duration") or 0),
                message_id=m_id,
                title=data.get("title", "")[:25],
                thumbnail=data.get("thumbnail", "").split("?")[0] if data.get("thumbnail") else "",
                url=self.base + data.get("id", ""),
                view_count=str(data.get("view_count", "")),
                video=video,
            )
        except Exception as e:
            logger.warning(f"Search failed for {query}: {e}")
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
                    duration_sec=sum(int(x) * 60**i for i, x in enumerate(reversed(str(data.get("duration") or "0").split(":")))),
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
            def _extract_mix():
                cookie = self.get_cookies()
                opts = {
                    "format": "bestaudio",
                    "quiet": True,
                    "extract_flat": True,
                    "geo_bypass": True,
                    "nocheckcertificate": True,
                    "force_ipv4": True,
                    "playlistend": 8,
                }
                if cookie:
                    opts["cookiefile"] = cookie

                with yt_dlp.YoutubeDL(opts) as ydl:
                    return ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}&list=RD{video_id}", download=False)

            info = await asyncio.to_thread(_extract_mix)
            if not info or "entries" not in info or not info["entries"]:
                logger.warning("Autoplay exhausted: No new tracks found in RD mix.")
                return None

            # Find the entry matching the current video_id; fall back to the
            # first entry if it isn't present (RD mixes usually place the
            # currently playing video first, but this isn't guaranteed).
            current_title = next(
                (e.get("title", "") for e in info["entries"] if e.get("id") == video_id),
                info["entries"][0].get("title", ""),
            )

            next_id = None
            for entry in info["entries"]:
                vid = entry.get("id")
                if vid and vid != video_id and vid not in history:
                    candidate_title = entry.get("title", "")

                    if current_title and candidate_title:
                        sim = SequenceMatcher(None, current_title, candidate_title).ratio()
                        if sim > 0.55:
                            continue

                    next_id = vid
                    break

            if not next_id:
                logger.warning("Autoplay exhausted: No valid tracks found in RD mix.")
                return None

            track = await self.search(f"https://www.youtube.com/watch?v={next_id}", 0, video)
            return track

        except Exception as e:
            logger.warning(f"Autoplay fetch failed: {e}")
            return None



    async def download(
        self, video_id: str, video: bool = False, title: str = "", duration: str = "", duration_sec: int = 0
    ) -> str | None:
        url = self.base + video_id
        ext = "mp4" if video else "webm"
        filename = os.path.abspath(f"downloads/{video_id}.{ext}")

        if video_id not in self._locks:
            self._locks[video_id] = asyncio.Lock()

        async with self._locks[video_id]:
            try:
                if Path(filename).exists() and os.path.getsize(filename) > 0:
                    return filename

                from anony import app, config, db

                if config.DB_CHANNEL:
                    try:
                        cache_data = await db.get_song_cache(video_id, video)
                        if cache_data:
                            try:
                                if cache_data.get("file_id"):
                                    downloaded_path = await app.download_media(cache_data["file_id"], file_name=filename)
                                    if downloaded_path and os.path.getsize(downloaded_path) > 0:
                                        await db.increment_play_count(video_id, video)
                                        return downloaded_path
                            except Exception:
                                if os.path.exists(filename):
                                    with contextlib.suppress(OSError):
                                        os.remove(filename)

                            if cache_data.get("msg_id"):
                                try:
                                    msg = await app.get_messages(config.DB_CHANNEL, cache_data["msg_id"])
                                    if msg and (getattr(msg, "audio", None) or getattr(msg, "video", None) or getattr(msg, "document", None) or getattr(msg, "voice", None)):
                                        downloaded_path = await app.download_media(msg, file_name=filename)
                                        if downloaded_path and os.path.getsize(downloaded_path) > 0:
                                            await db.increment_play_count(video_id, video)
                                            return downloaded_path
                                except Exception as e:
                                    logger.warning(f"Cache fallback download failed for {video_id}: {e}")
                                finally:
                                    if os.path.exists(filename) and os.path.getsize(filename) == 0:
                                        with contextlib.suppress(OSError):
                                            os.remove(filename)
                    except Exception as e:
                        logger.warning(f"Cache check failed for {video_id}: {e}")

                cookie = self.get_cookies()
                base_opts = {
                    "outtmpl": f"{os.path.abspath('downloads')}/%(id)s.%(ext)s",
                    "quiet": True,
                    "noplaylist": True,
                    "geo_bypass": True,
                    "no_warnings": True,
                    "overwrites": True,
                    "nocheckcertificate": True,
                    "force_ipv4": True,
                    "remote_components": ["ejs:github"],
                }
                if cookie:
                    base_opts["cookiefile"] = cookie

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
                        except (yt_dlp.utils.DownloadError, yt_dlp.utils.ExtractorError) as e:
                            logger.warning(f"yt-dlp error for {url}: {e}")
                            return None
                        except Exception as ex:
                            logger.warning("Download failed: %s", ex)
                            return None
                    return filename

                result_filename = await asyncio.to_thread(_download)

                if not result_filename or not Path(filename).exists():
                    logger.warning(f"Download failed for {video_id}")
                    if Path(filename).exists():
                        Path(filename).unlink()
                    return None

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

                    bg_task = asyncio.create_task(_upload_to_cache())
                    from anony import tasks
                    tasks.append(bg_task)

                return result_filename
            finally:
                # Cleanup lock to prevent memory leak
                self._locks.pop(video_id, None)
