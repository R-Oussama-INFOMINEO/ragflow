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
Backend 4: openai-api
Cloud transcription via OpenAI Whisper REST API.
Requires OPENAI_API_KEY or parser_config["openai_api_key"].

Resilience strategy:
  - Retry Pattern applied to the API call (max 3 attempts, 2s base backoff).
    Longer backoff than youtube_transcript because OpenAI rate limits require
    more recovery time between attempts.
  - Circuit Breaker applied at module level — after MAX_FAILURES consecutive
    failures, the circuit opens for OPEN_SECONDS to avoid hammering the API.
    This protects against quota exhaustion and runaway retries.
  - Authentication errors (missing/invalid API key) are non_retryable —
    they are configuration issues, not transient failures.
  - Circuit Breaker NOT used for youtube_transcript or download_audio because
    those are cheaper, faster calls where retry alone is sufficient.
"""
import logging
import time
from .whisper_shared import download_audio, with_retry

logger = logging.getLogger("ragflow.video.openai_api")

# ── Circuit Breaker state ─────────────────────────────────────────────────────
# Module-level state — shared across all calls in this process.
# No external library needed — simple counter + timestamp pattern.
#
# Tune these constants to adjust circuit sensitivity:
#   MAX_FAILURES : consecutive failures before circuit opens (default: 3)
#   OPEN_SECONDS : how long circuit stays open before half-open retry (default: 60)
MAX_FAILURES: int = 3
OPEN_SECONDS: int = 60

_circuit: dict = {
    "failures":   0,        # consecutive failure count
    "open_until": 0.0,      # timestamp when circuit closes again (0 = closed)
}


def _check_circuit() -> None:
    """
    Circuit Breaker check — raises immediately if circuit is open.
    Transitions OPEN → HALF-OPEN when OPEN_SECONDS has elapsed.
    """
    now = time.time()
    if _circuit["open_until"] > now:
        remaining = int(_circuit["open_until"] - now)
        raise RuntimeError(
            f"OpenAI API circuit breaker is OPEN — "
            f"too many consecutive failures. Retry in {remaining}s."
        )


def _record_success() -> None:
    """Reset circuit on success — closes circuit, clears failure count."""
    _circuit["failures"] = 0
    _circuit["open_until"] = 0.0


def _record_failure() -> None:
    """Record a failure — opens circuit if MAX_FAILURES reached."""
    _circuit["failures"] += 1
    if _circuit["failures"] >= MAX_FAILURES:
        _circuit["open_until"] = time.time() + OPEN_SECONDS
        logger.error(
            "openai_api: circuit breaker OPEN after %d consecutive failures "
            "— pausing for %ds",
            _circuit["failures"], OPEN_SECONDS,
        )


# ── Main function ─────────────────────────────────────────────────────────────

def fetch_transcript(video_id: str, cfg: dict,
                     max_attempts: int = 3,
                     backoff_seconds: float = 2.0) -> list:
    """
    Transcribe via OpenAI Whisper API. Fastest option; requires API key.

    Retry Pattern: retries up to max_attempts times with exponential backoff.
    Circuit Breaker: fails immediately if circuit is open (too many recent
    failures). Circuit resets automatically after OPEN_SECONDS.

    Args:
        video_id        : 11-char YouTube video ID
        cfg             : parser_config dict (must contain openai_api_key or
                          OPENAI_API_KEY env var must be set)
        max_attempts    : retry attempts for the API call (default: 3)
        backoff_seconds : base backoff in seconds (default: 2.0)
    """
    try:
        from openai import OpenAI, AuthenticationError
    except ImportError:
        raise RuntimeError(
            "openai package is not installed. Run: pip install openai"
        )
    import os

    api_key = cfg.get("openai_api_key") or os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        # Configuration error — not retryable, not a circuit breaker event
        raise RuntimeError(
            "openai-api backend requires 'openai_api_key' in parser_config "
            "or the OPENAI_API_KEY environment variable."
        )

    # Circuit Breaker check — fail fast if circuit is open
    _check_circuit()

    audio_path = None
    try:
        audio_path = download_audio(video_id)
        logger.info("openai-api transcribing %s", video_id)
        client = OpenAI(api_key=api_key)

        def _call_api() -> list:
            with open(audio_path, "rb") as f:
                response = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=f,
                    response_format="verbose_json",
                    timestamp_granularities=["segment"],
                )
            entries = []
            for seg in response.segments:
                entries.append({
                    "text":     seg.text.strip(),
                    "start":    round(seg.start, 3),
                    "duration": round(seg.end - seg.start, 3),
                })
            return entries

        # Retry Pattern: API call subject to transient failures (rate limits,
        # timeouts, temporary OpenAI outages).
        # AuthenticationError is non_retryable — wrong key won't fix itself.
        result = with_retry(
            _call_api,
            max_attempts=max_attempts,
            backoff_seconds=backoff_seconds,
            non_retryable=(AuthenticationError,),
        )

        # Success — reset circuit breaker
        _record_success()
        logger.info("openai-api produced %d segments for %s", len(result), video_id)
        return result

    except Exception as exc:
        # Record failure for circuit breaker (skip auth errors — not a
        # transient failure, recording would unfairly trip the circuit)
        try:
            from openai import AuthenticationError as _AE
            if not isinstance(exc, _AE):
                _record_failure()
        except ImportError:
            _record_failure()

        raise RuntimeError(
            f"OpenAI API transcription failed for {video_id}: {exc}"
        ) from exc

    finally:
        if audio_path:
            import os as _os
            if _os.path.exists(audio_path):
                _os.remove(audio_path)
