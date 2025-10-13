from dataclasses import dataclass
from typing import List, Dict, Optional, Any

@dataclass
class SearchResult:
    """Результат поиска контента."""
    name: str
    url: str
    player_id: str

@dataclass
class TVShow:
    """Информация о сериале."""
    name: str
    player_id: str
    img: str
    description: str

@dataclass
class VideoQuality:
    """Доступное качество видео."""
    quality: int
    url: str

@dataclass
class NextEpisode:
    """Информация о следующем эпизоде."""
    exists: bool
    season: Optional[int] = None
    episode: Optional[int] = None

@dataclass
class EpisodeData:
    """Данные эпизода."""
    video_id: str
    season: str
    episode: str
    voice_name: str
    voice_id: str
    duration: str
    video_sewnjunk: int
    skip: List[List[str]]

@dataclass
class SeasonInfo:
    """Информация о сезоне."""
    season_number: int
    episodes: List['EpisodeData']

@dataclass
class SeriesData:
    """Полные данные сериала."""
    player_id: str
    seasons: Dict[int, SeasonInfo]
    available_voices: Dict[str, str]  # voice_id -> voice_name