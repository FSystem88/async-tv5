# AsyncTV5

[English](#english) | [Русский](#русский)

<a name="english"></a>
# AsyncTV5 🇺🇸

AsyncTV5 is an asynchronous Python library for working with the TV5 API. It provides a convenient interface for searching, retrieving information, and downloading video content.

## 🚀 Features

- 🔍 **Content Search** - Search for series and movies by title
- 📺 **Content Information** - Get detailed information about TV shows
- 🎯 **Available Qualities** - Get list of available video qualities
- ⏭️ **Episode Navigation** - Find next episode information
- 📥 **Video Download** - Async video download in selected quality
- ⚡ **High Performance** - Asynchronous requests and parallel downloading
- 🔄 **Auto Domain Switching** - Automatic working domain discovery

## 📦 Installation

```bash
pip install async-tv5
```

Or from source:
```bash
git clone https://github.com/yourusername/async-tv5.git
cd async-tv5
pip install -e .
```

## 🛠️ Quick Start

```python
import asyncio
from async_tv5 import AsyncTV5

async def main():
    async with AsyncTV5() as client:
        # Search content
        results = await client.search("Charlotte's Web")
        
        for result in results:
            print(f"Found: {result.name} (ID: {result.player_id})")
        
        if results:
            # Get TV show info
            tv_show = await client.get_tv_show("Charlotte's Web")
            print(f"Title: {tv_show.name}")
            print(f"Description: {tv_show.description}")

asyncio.run(main())
```

## 📚 Basic Usage

```python
import asyncio
from async_tv5 import AsyncTV5

async def main():
    async with AsyncTV5() as client:
        # 1. Search
        results = await client.search("Movie Title")
        
        # 2. Get TV show info
        tv_show = await client.get_tv_show("Movie Title", results[0].player_id)
        
        # 3. Get series data
        series_data = await client.get_series_data(tv_show.player_id)
        
        # 4. Get available qualities
        qualities = await client.get_available_qualities(
            player_id=tv_show.player_id,
            season="1",
            episode="1",
            voice_id="152"
        )
        
        # 5. Download video
        # output_path = await client.download_video(
        #     player_id=tv_show.player_id,
        #     season="1",
        #     episode="1",
        #     voice_id="152",
        #     quality="720",
        #     output_dir="./downloads"
        # )

asyncio.run(main())
```

## 🔧 API Reference

### Main Methods

- `search(query: str) -> List[SearchResult]`
- `get_tv_show(query: str, player_id: Optional[str] = None) -> TVShow`
- `get_series_data(player_id: str) -> SeriesData`
- `get_episode_data(player_id: str, season: str, episode: str) -> List[EpisodeData]`
- `get_available_qualities(player_id: str, season: str, episode: str, voice_id: str) -> List[VideoQuality]`
- `get_next_episode(player_id: str, current_season: int, current_episode: int) -> NextEpisode`
- `download_video(player_id: str, season: str, episode: str, voice_id: str, quality: str, output_dir: str = "/tmp") -> str`

### Data Models

- `SearchResult`: Search result (name, url, player_id)
- `TVShow`: TV show information (name, player_id, img, description)
- `SeriesData`: Full series data (seasons, episodes, voices)
- `EpisodeData`: Episode details (video_id, duration, voice_id, etc.)
- `VideoQuality`: Available quality (quality, url)
- `NextEpisode`: Next episode information

## ⚠️ Important Notes

- **FFmpeg required** for download functionality
- **Legal usage** - Ensure you have rights to download and use content
- **API stability** - Service API may change, requiring library updates

## 📄 License

MIT

---

<a name="русский"></a>
# AsyncTV5 🇷🇺

AsyncTV5 - асинхронная Python библиотека для работы с TV5 API. Предоставляет удобный интерфейс для поиска, получения информации и скачивания видео контента.

## 🚀 Возможности

- 🔍 **Поиск контента** - Поиск сериалов и фильмов по названию
- 📺 **Информация о контенте** - Получение подробной информации о сериалах
- 🎯 **Доступные качества** - Получение списка доступных качеств видео
- ⏭️ **Навигация по эпизодам** - Поиск следующего эпизода
- 📥 **Скачивание видео** - Асинхронное скачивание видео в выбранном качестве
- ⚡ **Высокая производительность** - Асинхронные запросы и параллельная загрузка
- 🔄 **Автопереключение доменов** - Автоматический поиск рабочих доменов

## 📦 Установка

```bash
pip install async-tv5
```

Или из исходного кода:
```bash
git clone https://github.com/yourusername/async-tv5.git
cd async-tv5
pip install -e .
```

## 🛠️ Быстрый старт

```python
import asyncio
from async_tv5 import AsyncTV5

async def main():
    async with AsyncTV5() as client:
        # Поиск контента
        results = await client.search("Паутина Шарлотты")
        
        for result in results:
            print(f"Найден: {result.name} (ID: {result.player_id})")
        
        if results:
            # Получение информации о сериале
            tv_show = await client.get_tv_show("Паутина Шарлотты")
            print(f"Название: {tv_show.name}")
            print(f"Описание: {tv_show.description}")

asyncio.run(main())
```

## 📚 Базовое использование

```python
import asyncio
from async_tv5 import AsyncTV5

async def main():
    async with AsyncTV5() as client:
        # 1. Поиск
        results = await client.search("Название фильма")
        
        # 2. Информация о сериале
        tv_show = await client.get_tv_show("Название фильма", results[0].player_id)
        
        # 3. Полные данные сериала
        series_data = await client.get_series_data(tv_show.player_id)
        
        # 4. Доступные качества
        qualities = await client.get_available_qualities(
            player_id=tv_show.player_id,
            season="1",
            episode="1",
            voice_id="152"
        )
        
        # 5. Скачивание видео
        # output_path = await client.download_video(
        #     player_id=tv_show.player_id,
        #     season="1",
        #     episode="1",
        #     voice_id="152",
        #     quality="720",
        #     output_dir="./downloads"
        # )

asyncio.run(main())
```

## 🔧 Справочник API

### Основные методы

- `search(query: str) -> List[SearchResult]` - Поиск контента
- `get_tv_show(query: str, player_id: Optional[str] = None) -> TVShow` - Информация о сериале
- `get_series_data(player_id: str) -> SeriesData` - Полные данные сериала
- `get_episode_data(player_id: str, season: str, episode: str) -> List[EpisodeData]` - Данные эпизода
- `get_available_qualities(player_id: str, season: str, episode: str, voice_id: str) -> List[VideoQuality]` - Доступные качества
- `get_next_episode(player_id: str, current_season: int, current_episode: int) -> NextEpisode` - Следующий эпизод
- `download_video(player_id: str, season: str, episode: str, voice_id: str, quality: str, output_dir: str = "/tmp") -> str` - Скачивание видео

### Модели данных

- `SearchResult`: Результат поиска (название, url, player_id)
- `TVShow`: Информация о сериале (название, player_id, изображение, описание)
- `SeriesData`: Полные данные сериала (сезоны, эпизоды, озвучки)
- `EpisodeData`: Данные эпизода (video_id, длительность, voice_id и др.)
- `VideoQuality`: Доступное качество (качество, url)
- `NextEpisode`: Информация о следующем эпизоде

## ⚠️ Важные заметки

- **Требуется FFmpeg** для функции скачивания
- **Правовое использование** - Убедитесь, что имеете право на скачивание и использование контента
- **Стабильность API** - API сервиса может изменяться, что потребует обновления библиотеки

## 📄 Лицензия

MIT