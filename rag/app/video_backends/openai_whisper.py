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
Backend 3: openai-whisper
Local transcription via the original OpenAI Whisper library.
"""
import logging
import os
from .whisper_shared import download_audio, segments_from_whisper_result

logger = logging.getLogger("ragflow.video.openai_whisper")


def fetch_transcript(video_id: str, cfg: dict) -> list:
    """Transcribe via openai-whisper (original local library)."""
    try:
        import whisper
    except ImportError:
        raise RuntimeError(
            "openai-whisper is not installed. Run: pip install openai-whisper"
        )
    model_size = cfg.get("whisper_model", "base")
    audio_path = None
    try:
        audio_path = download_audio(video_id)
        logger.info("openai-whisper transcribing %s (model=%s)", video_id, model_size)
        import ssl
        ssl._create_default_https_context = ssl._create_unverified_context
        model  = whisper.load_model(model_size)
        result = model.transcribe(audio_path)
        entries = segments_from_whisper_result(result)
        logger.info("openai-whisper produced %d segments for %s", len(entries), video_id)
        return entries
    except Exception as exc:
        raise RuntimeError(
            f"openai-whisper transcription failed for {video_id}: {exc}"
        ) from exc
    finally:
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)
