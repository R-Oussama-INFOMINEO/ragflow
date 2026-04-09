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
YouTube video transcript parser for RagFlow.

Orchestrates transcript fetching across 4 backends (see video_backends/)
and produces RagFlow-compatible chunk dicts.

Backends (selected via parser_config["whisper_backend"]):
  - youtube-transcript-api  : fast caption fetch, no download (default)
  - faster-whisper          : local Whisper via CTranslate2 (CPU/GPU)
  - openai-whisper          : local Whisper via original OpenAI lib (CPU/GPU)
  - openai-api              : cloud Whisper via OpenAI REST API (needs key)
"""
import logging
import re
from typing import Optional

from rag.nlp import rag_tokenizer, tokenize
from rag.app.video_backends import youtube_transcript as _yta
from rag.app.video_backends import faster_whisper as _fw
from rag.app.video_backends import openai_whisper as _ow
from rag.app.video_backends import openai_api as _oa

logger = logging.getLogger("ragflow.video")

# ── tuneable constants ────────────────────────────────────────────────────────
SEGMENT_SECONDS: int = 60    # merge raw cues into ~60-second windows
OVERLAP_SECONDS: int = 10    # trailing overlap to avoid context cuts
# ─────────────────────────────────────────────────────────────────────────────


def _extract_video_id(url: str) -> Optional[str]:
    """Extract the 11-char YouTube video ID from any common URL format."""
    patterns = [
        r"(?:v=)([A-Za-z0-9_-]{11})",
        r"(?:youtu\.be/)([A-Za-z0-9_-]{11})",
        r"(?:embed/)([A-Za-z0-9_-]{11})",
    ]
    for pat in patterns:
        m = re.search(pat, url)
        if m:
            return m.group(1)
    return None


def _fetch_transcript(video_id: str, parser_config: dict | None = None) -> list:
    """
    Dispatch transcript fetching to the configured backend.

    parser_config schema:
      {
        "whisper_backend": "youtube-transcript-api",  # default
        "whisper_model":   "base",
        "openai_api_key":  ""
      }

    Returns:
      [{"text": str, "start": float, "duration": float}, ...]
    """
    cfg = parser_config or {}
    backend = cfg.get("whisper_backend", "youtube-transcript-api")

    if backend == "youtube-transcript-api":
        return _yta.fetch_transcript(video_id)
    elif backend == "faster-whisper":
        return _fw.fetch_transcript(video_id, cfg)
    elif backend == "openai-whisper":
        return _ow.fetch_transcript(video_id, cfg)
    elif backend == "openai-api":
        return _oa.fetch_transcript(video_id, cfg)
    else:
        raise RuntimeError(
            f"Unknown whisper_backend '{backend}'. "
            "Choose: youtube-transcript-api | faster-whisper | openai-whisper | openai-api"
        )


def _merge_into_segments(entries: list) -> list:
    """
    Merge raw cue-level entries into overlapping ~60-second segments.
    Returns list of {"text", "start", "end", "timestamp_seconds"}.
    """
    if not entries:
        return []

    segments = []
    window_start = entries[0]["start"]
    window_texts = []
    window_end = window_start

    for entry in entries:
        cue_start: float = entry["start"]
        cue_text: str = entry["text"].replace("\n", " ").strip()
        cue_end: float = cue_start + entry.get("duration", 0.0)

        if cue_start - window_start >= SEGMENT_SECONDS and window_texts:
            segments.append({
                "text": " ".join(window_texts),
                "start": window_start,
                "end": window_end,
                "timestamp_seconds": int(window_start),
            })
            # trailing overlap: carry back OVERLAP_SECONDS of context
            overlap_texts = [
                e["text"].replace("\n", " ").strip()
                for e in entries
                if e["start"] >= (window_end - OVERLAP_SECONDS)
                and e["start"] < cue_start
            ]
            window_start = cue_start
            window_texts = overlap_texts + [cue_text]
            window_end = cue_end
        else:
            window_texts.append(cue_text)
            window_end = cue_end

    if window_texts:
        segments.append({
            "text": " ".join(window_texts),
            "start": window_start,
            "end": window_end,
            "timestamp_seconds": int(window_start),
        })

    return segments


def chunk(filename, binary=None, from_page=0, to_page=100_000,
          lang="English", callback=None, kb_id=None,
          parser_config=None, tenant_id=None, **kwargs):
    """
    Main entry point called by task_executor.build_chunks().

    `filename` carries the YouTube URL — RagFlow stores the document
    source path here, and for video documents we register the URL as
    the filename.

    Returns a list of chunk dicts. Each must contain `content_with_weight`
    (the text to embed). All other keys become stored metadata.
    """
    youtube_url: str = filename.strip()

    logger.info("video.chunk: starting ingestion for %s", youtube_url)

    if callback:
        callback(0.05, "Extracting video ID from URL")

    video_id = _extract_video_id(youtube_url)
    if not video_id:
        msg = f"Cannot extract video ID from URL: {youtube_url!r}"
        logger.error("video.chunk: %s", msg)
        if callback:
            callback(-1, msg)
        return []

    if callback:
        callback(0.1, f"Fetching transcript for video {video_id}")

    try:
        raw_entries = _fetch_transcript(video_id, parser_config=parser_config)
    except RuntimeError as exc:
        logger.error("video.chunk: %s", exc)
        if callback:
            callback(-1, str(exc))
        return []

    if callback:
        callback(0.4, f"Fetched {len(raw_entries)} transcript cues — merging into segments")

    segments = _merge_into_segments(raw_entries)

    if not segments:
        msg = "Transcript is empty — no chunks produced"
        logger.warning("video.chunk: %s for %s", msg, youtube_url)
        if callback:
            callback(-1, msg)
        return []

    # retrieve video title from kwargs (passed by task_executor from doc metadata)
    # falls back to parser_config["video_title"], then to the URL itself
    video_title = kwargs.get("video_title", "")
    if not video_title and parser_config and isinstance(parser_config, dict):
        video_title = parser_config.get("video_title", "")
    if not video_title:
        video_title = youtube_url

    chunks = []
    for seg in segments:
        deeplink = f"https://www.youtube.com/watch?v={video_id}&t={seg['timestamp_seconds']}s"
        d = {
            "docnm_kwd": filename,
            "title_tks": rag_tokenizer.tokenize(
                re.sub(r"\.[a-zA-Z]+$", "", filename)
            ),
        }
        d["title_sm_tks"] = rag_tokenizer.fine_grained_tokenize(d["title_tks"])
        tokenize(d, seg["text"], lang.lower() == "english")
        d["content_with_weight"] = seg["text"]
        # ── video-specific metadata ────────────────────────────────────────
        d["youtube_url"] = youtube_url
        d["video_id"] = video_id
        d["video_title"] = video_title
        d["timestamp_seconds"] = seg["timestamp_seconds"]
        d["transcript_segment"] = deeplink
        chunks.append(d)

    logger.info(
        "video.chunk: produced %d chunks for video_id=%s",
        len(chunks), video_id,
    )
    if callback:
        callback(0.9, f"Produced {len(chunks)} transcript chunks")

    return chunks
