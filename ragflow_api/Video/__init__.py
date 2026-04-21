"""YouTube video ingestion and completion polling module."""

from .video_api import VideoRagflowAPI
from .video_dto import (
    IngestVideoRequest,
    IngestVideoResponse,
    WaitForCompletionRequest,
    WaitForCompletionResponse,
)

__all__ = [
    "VideoRagflowAPI",
    "IngestVideoRequest",
    "IngestVideoResponse",
    "WaitForCompletionRequest",
    "WaitForCompletionResponse",
]