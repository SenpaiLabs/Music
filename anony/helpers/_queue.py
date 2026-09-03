# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic


from collections import defaultdict, deque
from typing import Optional

from ._dataclass import Track

MediaItem = Track


class Queue:
    def __init__(self):
        self.queues: dict[int, deque[Track]] = defaultdict(deque)
        self.history: dict[int, deque[str]] = defaultdict(lambda: deque(maxlen=20))
        self.prefetched: dict[int, Track] = {}

    def add(self, chat_id: int, item: Track) -> int:
        """Add an item to the queue and return its position (1-based)."""
        self.queues[chat_id].append(item)
        return len(self.queues[chat_id]) - 1

    def check_item(self, chat_id: int, item_id: str) -> tuple[int, Optional[Track]]:
        """Check if an item with the given ID exists in the queue."""
        pos, track = next(
            (
                (i, track)
                for i, track in enumerate(self.queues[chat_id])
                if track.id == item_id
            ),
            (-1, None),
        )
        return pos, track

    def force_add(
        self, chat_id: int, item: Track, remove: int | bool = False
    ) -> None:
        """Replace the currently playing item with a new one."""
        self.remove_current(chat_id)
        self.queues[chat_id].appendleft(item)
        if remove:
            del self.queues[chat_id][remove]

    def get_current(self, chat_id: int) -> Optional[Track]:
        """Return the currently playing item (first in queue), if any."""
        return self.queues[chat_id][0] if self.queues[chat_id] else None

    def get_next(self, chat_id: int, check: bool = False) -> Optional[Track]:
        """Remove current item and return the next one, or None if empty."""
        if not self.queues[chat_id]:
            return None
        if check:
            return self.queues[chat_id][1] if len(self.queues[chat_id]) > 1 else None

        self.queues[chat_id].popleft()
        return self.queues[chat_id][0] if self.queues[chat_id] else None

    def get_queue(self, chat_id: int) -> list[Track]:
        """Return the full queue including the currently playing item."""
        return list(self.queues[chat_id])

    def remove_current(self, chat_id: int) -> None:
        """Remove the currently playing item only (if exists)."""
        if self.queues[chat_id]:
            self.queues[chat_id].popleft()

    def add_history(self, chat_id: int, video_id: str) -> None:
        """Record a played video ID for autoplay repeat-avoidance."""
        if video_id:
            self.history[chat_id].append(video_id)

    def get_history(self, chat_id: int) -> set[str]:
        """Return the set of recently played video IDs for a chat."""
        return set(self.history[chat_id])

    def set_prefetched_autoplay(self, chat_id: int, item: Track) -> None:
        """Store a prefetched autoplay track for a chat."""
        self.prefetched[chat_id] = item

    def get_prefetched_autoplay(self, chat_id: int) -> Optional[Track]:
        """Retrieve and remove the prefetched autoplay track for a chat."""
        return self.prefetched.pop(chat_id, None)

    def clear(self, chat_id: int) -> None:
        """Clear the entire queue and its play history."""
        self.queues.pop(chat_id, None)
        self.history.pop(chat_id, None)
        self.prefetched.pop(chat_id, None)

