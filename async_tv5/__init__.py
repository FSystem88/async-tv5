"""AsyncTV5 - Асинхронная библиотека для работы с TV5 API."""

from .client import AsyncTV5
from .models import SearchResult, TVShow, VideoQuality, NextEpisode
from .exceptions import TV5Error, DomainNotFoundError, VideoNotFoundError

__version__ = "1.0.0"
__all__ = [
    "AsyncTV5",
    "SearchResult", 
    "TVShow",
    "VideoQuality",
    "NextEpisode",
    "TV5Error",
    "DomainNotFoundError",
    "VideoNotFoundError"
]