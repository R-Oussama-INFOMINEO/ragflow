#
#  Copyright 2025 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
"""
Shared helpers for Whisper backends.
Audio download via yt-dlp, result normalisation, and resilience utilities.

Resilience strategy (see summary table in video_backends/):
  - with_retry()   : defined here, used by youtube_transcript.py, download_audio(), and openai_api.py
  - Circuit Breaker: used only by openai_api.py (expensive cloud call)
  - faster_whisper.py and openai_whisper.py: no extra retry needed, download_audio() already benefits from the retry added here.
"""
import logging
import time

logger = logging.getLogger("ragflow.video.whisper_shared")


# ── Resilience utility ────────────────────────────────────────────────────────

def with_retry(fn, max_attempts: int = 3, backoff_seconds: float = 1.0, non_retryable: tuple = ()):
    """
    Retry Pattern — retry fn up to max_attempts times with exponential backoff.

    Parameters are intentionally exposed so callers can tune per use case:
      - youtube_transcript : max_attempts=3, backoff_seconds=1.0 (fast API)
      - download_audio     : max_attempts=3, backoff_seconds=2.0 (slow network)
      - openai_api         : max_attempts=3, backoff_seconds=2.0 (rate limits)

    Args:
        fn              : zero-argument callable to retry
        max_attempts    : total number of attempts (default: 3)
        backoff_seconds : base wait in seconds; doubles each attempt (default: 1.0)
        non_retryable   : tuple of exception types that are permanent errors and should NOT be retried (e.g. auth errors, disabled videos, missing API keys)

    Returns:
        return value of fn() on success

    Raises:
        last exception if all attempts fail
    """
    last_exc = None
    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except non_retryable as exc:
            # Permanent error — retrying will not help, fail immediately
            raise exc
        except Exception as exc:
            last_exc = exc
            if attempt < max_attempts:
                wait = backoff_seconds * (2 ** (attempt - 1))
                logger.warning(
                    "with_retry: attempt %d/%d failed (%s) — retrying in %.1fs",
                    attempt, max_attempts, exc, wait,
                )
                time.sleep(wait)
            else:
                logger.error(
                    "with_retry: all %d attempts failed — last error: %s",
                    max_attempts, exc,
                )
    raise last_exc


# ── Audio download ────────────────────────────────────────────────────────────

def download_audio(video_id: str, max_attempts: int = 3,
                   backoff_seconds: float = 2.0) -> str:
    """
    Download YouTube audio to a temp .m4a file using yt-dlp.
    Returns the path to the temp file. Caller is responsible for deletion.
    Requires ffmpeg to be installed in the container.

    Retry Pattern applied to ydl.download() — network timeouts and transient
    YouTube errors are retryable. Longer backoff (2s base) used because
    downloads are slow operations.

    File verification after download is NOT retried — if the file does not
    exist after a successful download() call, it is a yt-dlp configuration
    issue, not a transient network failure. Retrying would not help.

    Args:
        video_id        : 11-char YouTube video ID
        max_attempts    : retry attempts for ydl.download() (default: 3)
        backoff_seconds : base backoff in seconds, doubles each attempt (default: 2.0)
    """
    try:
        import yt_dlp
    except ImportError:
        raise RuntimeError("yt-dlp is not installed. Run: pip install yt-dlp")
    import os
    import tempfile

    tmp = tempfile.NamedTemporaryFile(suffix=".m4a", delete=False)
    tmp.close()
    os.unlink(tmp.name)  # remove so yt-dlp always downloads fresh
    out_path = tmp.name

    ydl_opts = {
        "format": "140/139/bestaudio[ext=m4a]/bestaudio",
        "outtmpl": out_path,
        "quiet": True,
        "no_warnings": True,
        "ffmpeg_location": "/usr/bin",
        "no_cache_dir": True,
    }

    url = f"https://www.youtube.com/watch?v={video_id}"

    # Retry Pattern: ydl.download() is a network call subject to transient
    # failures (rate limits, connection resets, YouTube throttling).
    # yt-dlp has internal retry for segment downloads but not for the overall
    # call initiation — we add an outer retry here for robustness.
    def _do_download():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

    with_retry(_do_download, max_attempts=max_attempts,
               backoff_seconds=backoff_seconds)

    # File verification — NOT retried (see docstring above)
    candidate = out_path + ".m4a"
    if os.path.exists(candidate) and not os.path.exists(out_path):
        return candidate
    if os.path.exists(out_path):
        return out_path

    raise RuntimeError(
        f"yt-dlp did not produce expected audio file for video {video_id}"
    )


# ── Result normalisation ──────────────────────────────────────────────────────

def segments_from_whisper_result(result: dict) -> list:
    """Convert openai-whisper result dict to standard segment format."""
    entries = []
    for seg in result.get("segments", []):
        start = float(seg.get("start", 0.0))
        end   = float(seg.get("end", start))
        entries.append({
            "text":     seg.get("text", "").strip(),
            "start":    round(start, 3),
            "duration": round(end - start, 3),
        })
    return entries
