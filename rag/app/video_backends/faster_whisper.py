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
Backend 2: faster-whisper
Local transcription via CTranslate2. Efficient on CPU (int8) or GPU (float16).
"""
import logging
from .whisper_shared import download_audio

logger = logging.getLogger("ragflow.video.faster_whisper")


def fetch_transcript(video_id: str, cfg: dict) -> list:
    """Transcribe via faster-whisper. Efficient on CPU with int8 quantisation."""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise RuntimeError(
            "faster-whisper is not installed. Run: pip install faster-whisper"
        )
    import os
    model_size = cfg.get("whisper_model", "base")
    device = cfg.get("whisper_device", "auto")
    if device == "auto":
        try:
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            device = "cpu"
    compute_type = "float16" if device == "cuda" else "int8"
    audio_path = None
    try:
        audio_path = download_audio(video_id)
        logger.info("faster-whisper transcribing %s (model=%s device=%s)",
                    video_id, model_size, device)
        model = WhisperModel(model_size, device=device, compute_type=compute_type)
        segments_iter, _ = model.transcribe(audio_path, beam_size=5)
        entries = []
        for seg in segments_iter:
            entries.append({
                "text":     seg.text.strip(),
                "start":    round(seg.start, 3),
                "duration": round(seg.end - seg.start, 3),
            })
        logger.info("faster-whisper produced %d segments for %s", len(entries), video_id)
        return entries
    except Exception as exc:
        raise RuntimeError(
            f"faster-whisper transcription failed for {video_id}: {exc}"
        ) from exc
    finally:
        if audio_path:
            import os as _os
            if _os.path.exists(audio_path):
                _os.remove(audio_path)
