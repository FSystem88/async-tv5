import asyncio
import json
import httpx
from bs4 import BeautifulSoup
import re
from pathlib import Path
from uuid import uuid4
import aiofiles
from typing import List, Dict, Optional, Any

from .models import SearchResult, TVShow, VideoQuality, NextEpisode, EpisodeData, SeasonInfo, SeriesData
from .exceptions import DomainNotFoundError, VideoNotFoundError, InvalidPlayerDataError


class AsyncTV5:
    """Асинхронный клиент для работы с TV5 API."""

    BASE_URL_PREFIX = "https://tv"
    BASE_URL_SUFFIX = ".ru"
    PROXY = None
    SEMAPHORE_LIMIT = 10
    DOWNLOAD_PAUSE = 0.01
    MAX_DOMAIN_ATTEMPTS = 10

    def __init__(self, proxy: Optional[str] = None, semaphore_limit: int = 10):
        """
        Инициализация клиента.
        
        Args:
            proxy: Прокси сервер (опционально)
            semaphore_limit: Лимит одновременных соединений
        """
        self.semaphore = asyncio.Semaphore(semaphore_limit)
        self.SEMAPHORE_LIMIT = semaphore_limit
        self.PROXY = proxy
        self.current_domain = 532
        self.base_url = f"{self.BASE_URL_PREFIX}{self.current_domain}{self.BASE_URL_SUFFIX}"

        client_params = {
            "http2": False,
            "follow_redirects": True,
            "timeout": httpx.Timeout(30.0),
            "verify": False
        }

        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            proxy=proxy,
            **client_params
        )
        self.client_no_proxy = httpx.AsyncClient(**client_params)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def close(self):
        """Закрытие HTTP-клиентов."""
        await self.client.aclose()
        await self.client_no_proxy.aclose()

    async def _find_valid_domain(self) -> str:
        """Поиск рабочего домена."""
        attempts = 0
        while attempts < self.MAX_DOMAIN_ATTEMPTS:
            try:
                response = await self.client_no_proxy.get(self.base_url, timeout=5.0)
                if response.status_code == 200:
                    return self.base_url
            except (httpx.RequestError, httpx.HTTPStatusError):
                pass

            self.current_domain += 1
            self.base_url = f"{self.BASE_URL_PREFIX}{self.current_domain}{self.BASE_URL_SUFFIX}"
            self.client.base_url = self.base_url
            attempts += 1
            await asyncio.sleep(1)

        raise DomainNotFoundError("Не удалось найти рабочий домен")

    async def _request(self, method: str, url: str, use_proxy: bool = True, **kwargs) -> httpx.Response:
        """Универсальный метод для выполнения HTTP-запросов."""
        client = self.client if use_proxy else self.client_no_proxy
        full_url = url if url.startswith("http") else f"{self.base_url}{url}"

        while True:
            try:
                response = await client.request(method=method.upper(), url=full_url, **kwargs)
                if response.status_code == 200:
                    return response
            except (httpx.RequestError, httpx.HTTPStatusError):
                await self._find_valid_domain()
                full_url = url if url.startswith("http") else f"{self.base_url}{url}"
                await asyncio.sleep(1)

    async def _extract_player_id_from_url(self, url: str) -> Optional[str]:
        """Извлечение player_id из URL страницы."""
        response = await self._request("GET", url)
        soup = BeautifulSoup(response.text, "html.parser")
        iframe = soup.find("iframe", src=re.compile(r"^//playep\.pro/pl/\d+"))
        if iframe:
            match = re.search(r"//playep\.pro/pl/(\d+)", iframe["src"])
            return match.group(1) if match else None
        return None

    async def search(self, query: str) -> List[SearchResult]:
        """
        Поиск контента по запросу.
        
        Args:
            query: Поисковый запрос
            
        Returns:
            List[SearchResult]: Список найденных результатов
        """
        response = await self._request("POST", "/catalog/1", data={"query": query, "a": "2"})
        soup = BeautifulSoup(response.text, "html.parser")
        
        results = []
        seen_players = set()
        maincol = soup.find("div", {"id": "maincol"})
        
        if not maincol:
            return results

        for entry_div in maincol.find_all("div", id=re.compile(r"^entryID\d+")):
            entry_id_match = re.match(r"entryID(\d+)", entry_div.get("id", ""))
            if not entry_id_match:
                continue

            title_tag = entry_div.find("span", style=re.compile(r"font-size:\d+pt"))
            name = title_tag.get_text(strip=True) if title_tag else "Неизвестно"
            
            # Обработка названия
            if "сезон" in name:
                name = name.split("сезон")[0] + "сезон"

            link_tag = entry_div.find("a", href=True)
            relative_url = link_tag["href"] if link_tag else ""
            full_url = f"{self.base_url}{relative_url}"

            player_id = await self._extract_player_id_from_url(full_url)
            if not player_id or player_id in seen_players:
                continue

            seen_players.add(player_id)
            results.append(SearchResult(
                name=name,
                url=full_url,
                player_id=player_id
            ))

        return results

    async def get_tv_show(self, query: str, player_id: Optional[str] = None) -> TVShow:
        """
        Получение информации о сериале по поисковому запросу и/или player_id.
        
        Args:
            query: Поисковый запрос для нахождения сериала
            player_id: ID плеера (опционально, если не указан - будет взят первый из результатов поиска)
            
        Returns:
            TVShow: Информация о сериале
            
        Raises:
            VideoNotFoundError: Если сериал не найден
        """
        # Ищем сериал по запросу
        search_results = await self.search(query)
        
        if not search_results:
            raise VideoNotFoundError(f"Сериал по запросу '{query}' не найден")
        
        # Определяем target player_id
        target_player_id = player_id
        target_url = None
        
        if target_player_id:
            # Ищем конкретный player_id в результатах
            for item in search_results:
                if item.player_id == target_player_id:
                    target_url = item.url
                    break
            if not target_url:
                raise VideoNotFoundError(f"Сериал с player_id {target_player_id} не найден в результатах поиска")
        else:
            # Берем первый результат
            target_player_id = search_results[0].player_id
            target_url = search_results[0].url

        # Получаем детальную информацию
        response = await self._request("GET", target_url)
        soup = BeautifulSoup(response.text, "html.parser")
        
        name_div = soup.find("div", {"style": "display:none"})
        name = name_div.text if name_div else "Неизвестно"
        
        description_td = soup.find("td", {"class": "eText"})
        if not description_td:
            raise VideoNotFoundError("Информация о сериале не найдена")

        img_tag = description_td.find("img")
        img_url = f"{self.base_url}{img_tag['src']}" if img_tag else ""

        # Очищаем описание от лишних тегов
        for div_tag in description_td.find_all("div"):
            div_tag.decompose()
        
        description = description_td.get_text().replace("\n\n\n", "").strip()

        return TVShow(
            name=name,
            player_id=target_player_id,
            img=img_url,
            description=description
        )

    async def get_player_data(self, player_id: str) -> Dict[str, Any]:
        """
        Получение данных плеера.
        
        Args:
            player_id: ID плеера
            
        Returns:
            Dict: Данные плеера
        """
        url = f"https://playep.pro/pl/{player_id}"
        response = await self._request("GET", url, use_proxy=False)
        soup = BeautifulSoup(response.text, "html.parser")
        
        input_data_div = soup.find("div", id="inputData")
        if not input_data_div:
            raise InvalidPlayerDataError("inputData div not found")
        
        try:
            return json.loads(input_data_div.get_text())
        except json.JSONDecodeError as e:
            raise InvalidPlayerDataError("Invalid JSON in inputData") from e

    async def get_series_data(self, player_id: str) -> SeriesData:
        """
        Получение полных данных о сериале со всеми сезонами и эпизодами.
        
        Args:
            player_id: ID плеера
            
        Returns:
            SeriesData: Полные данные сериала
        """
        raw_data = await self.get_player_data(player_id)
        
        seasons = {}
        available_voices = {}
        
        for season_num_str, episodes_data in raw_data.items():
            try:
                season_number = int(season_num_str)
                season_episodes = []
                
                for episode_num_str, episode_voices in episodes_data.items():
                    try:
                        episode_number = int(episode_num_str)
                        
                        for voice_data in episode_voices:
                            # Сохраняем информацию о доступных озвучках
                            voice_id = str(voice_data["voice_id"])
                            voice_name = voice_data["voice_name"]
                            available_voices[voice_id] = voice_name
                            
                            # Создаем объект EpisodeData
                            episode = EpisodeData(
                                video_id=voice_data["video_id"],
                                season=voice_data["season"],
                                episode=voice_data["episode"],
                                voice_name=voice_name,
                                voice_id=voice_id,
                                duration=voice_data["duration"],
                                video_sewnjunk=voice_data.get("video_sewnjunk", 0),
                                skip=voice_data.get("skip", [[], [], []])
                            )
                            season_episodes.append(episode)
                    
                    except (ValueError, KeyError):
                        continue
                
                # Сортируем эпизоды по номеру
                season_episodes.sort(key=lambda x: int(x.episode))
                
                seasons[season_number] = SeasonInfo(
                    season_number=season_number,
                    episodes=season_episodes
                )
            
            except ValueError:
                continue
        
        # Сортируем сезоны по номеру
        sorted_seasons = dict(sorted(seasons.items()))
        
        return SeriesData(
            player_id=player_id,
            seasons=sorted_seasons,
            available_voices=available_voices
        )

    async def get_episode_data(self, player_id: str, season: str, episode: str) -> List[EpisodeData]:
        """
        Получение данных конкретного эпизода со всеми доступными озвучками.
        
        Args:
            player_id: ID плеера
            season: Сезон
            episode: Эпизод
            
        Returns:
            List[EpisodeData]: Список данных эпизода для разных озвучек
        """
        series_data = await self.get_series_data(player_id)
        season_data = series_data.seasons.get(int(season))
        
        if not season_data:
            raise VideoNotFoundError(f"Сезон {season} не найден")
        
        episode_voices = [
            ep for ep in season_data.episodes 
            if ep.episode == str(episode)
        ]
        
        if not episode_voices:
            raise VideoNotFoundError(f"Эпизод {episode} не найден в сезоне {season}")
        
        return episode_voices

    async def get_available_qualities(self, player_id: str, season: str, episode: str, voice_id: str) -> List[VideoQuality]:
        """
        Получение списка доступных качеств видео.
        
        Args:
            player_id: ID плеера
            season: Сезон
            episode: Эпизод
            voice_id: ID озвучки
            
        Returns:
            List[VideoQuality]: Список доступных качеств
        """
        # Получаем video_id для указанной озвучки
        episode_voices = await self.get_episode_data(player_id, season, episode)
        video_id = None
        
        for episode_data in episode_voices:
            if str(episode_data.voice_id) == str(voice_id):
                video_id = episode_data.video_id
                break
        
        if not video_id:
            raise VideoNotFoundError("Озвучка не найдена")

        # Получаем M3U8 плейлист
        player_url = f"https://gencit.info/player/responce.php?video_id={video_id}"
        resp = await self._request("GET", player_url, use_proxy=False)
        m3u8_url = resp.json()["src"]
        
        resp = await self._request("GET", m3u8_url, use_proxy=False)
        m3u8_content = resp.text

        # Парсим доступные качества
        qualities = []
        seen_qualities = set()
        pattern = re.compile(r'#EXT-X-STREAM-INF:.*?\n(.*)')
        base_url = re.match(r"(https?://[^/]+)", m3u8_url).group(1)

        for match in pattern.finditer(m3u8_content):
            url = match.group(1).strip()
            if url.startswith("/"):
                url = base_url + url
            elif not url.startswith("http"):
                url = f"{m3u8_url.rsplit('/', 1)[0]}/{url}"
            
            quality_str = url.strip("/").split("/")[-2]
            try:
                quality = int(re.sub(r"\D", "", quality_str))
                if quality not in seen_qualities:
                    seen_qualities.add(quality)
                    qualities.append(VideoQuality(quality=quality, url=url))
            except ValueError:
                continue

        return sorted(qualities, key=lambda x: x.quality)

    async def get_next_episode(self, player_id: str, current_season: int, current_episode: int) -> NextEpisode:
        """
        Получение информации о следующем эпизоде.
        
        Args:
            player_id: ID плеера
            current_season: Текущий сезон
            current_episode: Текущий эпизод
            
        Returns:
            NextEpisode: Информация о следующем эпизоде
        """
        series_data = await self.get_series_data(player_id)
        seasons = sorted(series_data.seasons.keys())
        
        for season in seasons:
            season_info = series_data.seasons[season]
            episodes = [int(ep.episode) for ep in season_info.episodes]
            episodes.sort()
            
            if season == current_season:
                for episode in episodes:
                    if episode > current_episode:
                        return NextEpisode(exists=True, season=season, episode=episode)
            elif season > current_season:
                return NextEpisode(exists=True, season=season, episode=episodes[0])
        
        return NextEpisode(exists=False)

    async def download_segment(self, url: str, path: Path, index: int) -> tuple[Path, int, int]:
        """Скачивание одного сегмента видео."""
        async with self.semaphore:
            while True:
                try:
                    response = await self._request("GET", url, use_proxy=False)
                    if response.status_code == 200:
                        await asyncio.to_thread(self._sync_write_file, path, response.content)
                        return path, len(response.content), index
                    elif response.status_code == 429:
                        retry_after = int(response.headers.get('retry-after', '1'))
                        await asyncio.sleep(retry_after)
                    else:
                        await asyncio.sleep(1)
                except Exception:
                    await asyncio.sleep(1)

    def _sync_write_file(self, path: Path, data: bytes):
        """Синхронная запись файла."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)

    async def download_video(
        self, 
        player_id: str, 
        season: str, 
        episode: str, 
        voice_id: str, 
        quality: str,
        output_dir: str = "/tmp"
    ) -> str:
        """
        Скачивание видео в указанном качестве.
        
        Args:
            player_id: ID плеера
            season: Сезон
            episode: Эпизод
            voice_id: ID озвучки
            quality: Качество видео
            output_dir: Директория для сохранения
            
        Returns:
            str: Путь к скачанному файлу
        """
        qualities = await self.get_available_qualities(player_id, season, episode, voice_id)
        m3u8_url = next((item.url for item in qualities if str(item.quality) == str(quality)), None)
        
        if not m3u8_url:
            raise VideoNotFoundError(f"Качество {quality} не найдено")

        # Получаем список сегментов
        response = await self._request("GET", m3u8_url, use_proxy=False)
        m3u8_text = response.text
        base_url = m3u8_url.split("index.m3u8")[0]
        
        ts_urls = [
            line.strip() if line.startswith("http") else f"{base_url}{line.strip()}"
            for line in m3u8_text.splitlines() if line.endswith(".ts")
        ]
        
        if not ts_urls:
            raise VideoNotFoundError("Не найдено .ts сегментов")

        # Скачиваем сегменты
        temp_dir = Path(output_dir) / str(uuid4())
        temp_dir.mkdir(parents=True, exist_ok=True)

        tasks = [
            self.download_segment(url, temp_dir / f"segment_{i:06d}.ts", i)
            for i, url in enumerate(ts_urls)
        ]
        
        ts_results = await asyncio.gather(*tasks)
        ts_results = sorted(ts_results, key=lambda x: x[2])

        if len(ts_results) != len(ts_urls):
            raise VideoNotFoundError("Не все сегменты были успешно скачаны")

        # Создаем итоговый файл
        concat_list_path = temp_dir / "concat.txt"
        async with aiofiles.open(concat_list_path, "w") as f:
            for path, _, _ in ts_results:
                await f.write(f"file '{path.resolve()}'\n")

        output_file = temp_dir / f"{player_id}_s{season}e{episode}_v{voice_id}_q{quality}.mp4"
        
        # Используем ffmpeg для склейки
        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", str(concat_list_path), "-c", "copy", "-threads", "4",
            "-analyzeduration", "0", "-probesize", "32", str(output_file)
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL
        )
        return_code = await process.wait()

        if return_code != 0:
            raise RuntimeError("Ошибка при склейке сегментов с помощью FFmpeg")

        # Очистка временных файлов
        for path, _, _ in ts_results:
            path.unlink(missing_ok=True)
        concat_list_path.unlink(missing_ok=True)

        await asyncio.sleep(self.DOWNLOAD_PAUSE)
        return str(output_file)