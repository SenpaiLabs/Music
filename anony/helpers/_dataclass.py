# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic


import asyncio
from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class Track:
    id: Optional[str] = None
    channel_name: Optional[str] = None
    duration: Optional[str] = "00:00"
    duration_sec: int = 0
    file_path: Optional[str] = None
    message_id: int = 0
    time: int = 0
    title: Optional[str] = None
    url: Optional[str] = None
    thumbnail: Optional[str] = None
    user: Optional[str] = None
    view_count: Optional[str] = None
    video: bool = False
    vidid: Optional[str] = None
    stream_type: Optional[str] = None
    prefetched_for: Optional[str] = None
    download_task: Optional[asyncio.Task] = None
