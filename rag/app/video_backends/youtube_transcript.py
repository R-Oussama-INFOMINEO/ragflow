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
Backend 1: youtube-transcript-api
Fast caption fetch — no audio download required.

Resilience strategy:
  - Retry Pattern applied to the API call (max 3 attempts, 1s base backoff).
  - TranscriptsDisabled and VideoUnavailable are permanent errors — marked
    as non_retryable so they fail immediately without wasting retry cycles.
  - Circuit Breaker NOT used here — the YouTube transcript API is stateless
    and fast; retry alone is sufficient for transient failures.
"""
import logging
from .whisper_shared import with_retry

logger = logging.getLogger("ragflow.video.youtube_transcript")


def fetch_transcript(video_id: str, max_attempts: int = 3,
                     backoff_seconds: float = 1.0) -> list:
    """
    Fetch captions via youtube-transcript-api. Fast, no audio download.

    Retry Pattern: retries up to max_attempts times with exponential backoff.
    Permanent errors (TranscriptsDisabled, VideoUnavailable) are not retried.

    Args:
        video_id        : 11-char YouTube video ID
        max_attempts    : retry attempts (default: 3)
        backoff_seconds : base backoff in seconds (default: 1.0)
    """
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        from youtube_transcript_api._errors import (
            TranscriptsDisabled,
            NoTranscriptFound,
            VideoUnavailable,
        )
    except ImportError:
        raise RuntimeError(
            "youtube-transcript-api is not installed. "
            "Run: pip install youtube-transcript-api"
        )

    api = YouTubeTranscriptApi()

    def _fetch() -> list:
        # First attempt: direct English fetch (fastest path)
        try:
            fetched = api.fetch(video_id, languages=("en",))
            return fetched.to_raw_data()
        except (TranscriptsDisabled, VideoUnavailable):
            # Permanent errors — re-raise immediately, do not retry
            raise
        except Exception:
            pass

        # Fallback: list available transcripts and pick the best one
        transcript_list = api.list(video_id)
        try:
            transcript = transcript_list.find_manually_created_transcript(["en"])
        except NoTranscriptFound:
            try:
                transcript = transcript_list.find_generated_transcript(["en"])
            except NoTranscriptFound:
                available = [t.language_code for t in transcript_list]
                transcript = transcript_list.find_generated_transcript(available)

        fetched = api.fetch(video_id, languages=(transcript.language_code,))
        return fetched.to_raw_data()

    # Retry Pattern: TranscriptsDisabled and VideoUnavailable are permanent —
    # passing them as non_retryable ensures immediate failure without retries.
    # All other exceptions (network errors, rate limits) are retried.
    return with_retry(
        _fetch,
        max_attempts=max_attempts,
        backoff_seconds=backoff_seconds,
        non_retryable=(TranscriptsDisabled, VideoUnavailable),
    )
