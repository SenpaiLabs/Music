# Ponytail changes applied

All requested changes were applied locally. Nothing was committed or pushed.

| File | Change | Lines removed | Verification |
| --- | --- | ---: | --- |
| `anony/core/youtube.py` | Merged the two no-op yt-dlp loggers into `QuietLogger`. | 4 | Safe |
| `anony/core/mongo.py` | Removed the unused `get_top_songs()` method. The review incorrectly named `youtube.py`; the method existed here. | 18 | Safe |
| `anony/core/userbot.py` | Made `Userbot` a plain class and passed the selected `Client` straight through `boot_client()`. | 6 | Manual testing recommended: assistant startup and shutdown |
| `anony/core/calls.py` | Made `TgCall` a plain manager class. | 0 | Manual testing recommended: voice-call startup and playback |
| `anony/helpers/_thumbnails.py` | Removed unused `self.fill`. | 2 | Safe |
| `anony/helpers/_utilities.py` | Removed the empty initializer. | 3 | Safe |
| `anony/helpers/_queue.py` | Enumerates the deque directly instead of copying it. | 0 | Manual testing recommended: queue force-play action |
| `anony/plugins/banall.py` | Removed the unused worker ID argument. | 1 | Safe |
| `anony/plugins/active.py` | Removed redundant close after the context-managed file write. | 1 | Safe |

The diff removes 35 net lines (50 removed, 15 added).

## Verification

- `uv run python -m py_compile` passed for all edited Python files.
- No project test files were found.
- A stale-reference search found no remaining references to the deleted loggers, method, worker parameter, thumbnail field, or redundant close.
