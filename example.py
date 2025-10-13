#!/usr/bin/env python3
"""
Пример использования библиотеки AsyncTV5
"""

import asyncio
import os
from async_tv5 import AsyncTV5, VideoNotFoundError

async def main(query: str):
	"""Основной пример использования библиотеки AsyncTV5."""
	
	# Инициализация клиента
	async with AsyncTV5() as client:
		try:
			print(f"{'='*60}")
			print(f"🎬 Демонстрация библиотеки AsyncTV5")
			print(f"🔍 Поисковый запрос: {query}")
			print(f"{'='*60}")
			
			# 1. Поиск контента
			print(f"\n1️⃣ 🔍 Поиск контента...")
			results = await client.search(query)
			
			if not results:
				print("❌ Контент не найден")
				return
			
			print(f"✅ Найдено результатов: {len(results)}")
			for i, result in enumerate(results, 1):
				print(f"   {i}. {result.name} (ID: {result.player_id})")
			
			# Выбираем первый результат для демонстрации
			selected_result = results[0]
			player_id = selected_result.player_id
			
			print(f"\n🎯 Выбран контент: {selected_result.name}")
			print(f"   Player ID: {player_id}")
			
			# 2. Получение информации о сериале (новый метод с query)
			print(f"\n2️⃣ 📋 Получение информации о сериале...")
			tv_show = await client.get_tv_show(query=query, player_id=player_id)
			print(f"✅ Название: {tv_show.name}")
			print(f"📝 Описание: {tv_show.description[:150]}...")
			print(f"🖼️ Изображение: {tv_show.img}")
			
			# 3. Получение полных данных сериала
			print(f"\n3️⃣ 📊 Получение полных данных сериала...")
			series_data = await client.get_series_data(player_id)
			
			print(f"✅ Всего сезонов: {len(series_data.seasons)}")
			print("🎙️ Доступные озвучки:")
			for voice_id, voice_name in series_data.available_voices.items():
				print(f"   - {voice_name} (ID: {voice_id})")
			
			# 4. Детальная информация по сезонам
			print(f"\n4️⃣ 🎞️ Детальная информация по сезонам:")
			for season_num, season_info in series_data.seasons.items():
				unique_episodes = len(set(ep.episode for ep in season_info.episodes))
				unique_voices = len(set(ep.voice_id for ep in season_info.episodes))
				
				print(f"\n   📺 Сезон {season_num}:")
				print(f"      Эпизодов: {unique_episodes}")
				print(f"      Озвучек: {unique_voices}")
				
				# Покажем первые 2 эпизода для примера
				print(f"      Примеры эпизодов:")
				shown_episodes = set()
				for ep in season_info.episodes:
					if ep.episode not in shown_episodes and len(shown_episodes) < 2:
						shown_episodes.add(ep.episode)
						ep_voices = [e for e in season_info.episodes if e.episode == ep.episode]
						print(f"        - Эпизод {ep.episode}: {len(ep_voices)} озвучек")
			
			# 5. Получение данных конкретного эпизода
			print(f"\n5️⃣ 🎪 Получение данных конкретного эпизода...")
			try:
				episode_data_list = await client.get_episode_data(player_id, "1", "1")
				print(f"✅ Эпизод 1чx1 имеет {len(episode_data_list)} вариантов озвучки:")
				
				for i, episode_data in enumerate(episode_data_list[:3], 1):  # Покажем первые 3
					print(f"   {i}. {episode_data.voice_name} (ID: {episode_data.voice_id})")
					print(f"      Video ID: {episode_data.video_id}")
					print(f"      Длительность: {episode_data.duration} сек")
					
			except VideoNotFoundError:
				print("❌ Эпизод 1x1 не найден")
				# Попробуем найти любой доступный эпизод
				for season_num, season_info in series_data.seasons.items():
					if season_info.episodes:
						first_episode = season_info.episodes[0]
						print(f"🔄 Пробуем эпизод {season_num}x{first_episode.episode}...")
						try:
							episode_data_list = await client.get_episode_data(
								player_id, str(season_num), first_episode.episode
							)
							print(f"✅ Найден эпизод {season_num}x{first_episode.episode}")
							break
						except VideoNotFoundError:
							continue
			
			# 6. Получение доступных качеств
			if episode_data_list:
				first_voice_id = episode_data_list[0].voice_id
				first_voice_name = episode_data_list[0].voice_name
				
				print(f"\n6️⃣ 🎯 Получение доступных качеств...")
				print(f"   Озвучка: {first_voice_name} (ID: {first_voice_id})")
				
				qualities = await client.get_available_qualities(
					player_id=player_id,
					season=episode_data_list[0].season,
					episode=episode_data_list[0].episode, 
					voice_id=episode_data_list[0].voice_id
				)
				
				print("   📏 Доступные качества:")
				for quality in qualities:
					print(f"      - {quality.quality}p")
				
				# 7. Получение информации о следующем эпизоде
				print(f"\n7️⃣ ⏭️ Получение информации о следующем эпизоде...")
				next_ep = await client.get_next_episode(player_id, 1, 1)
				if next_ep.exists:
					print(f"   ✅ Следующий эпизод: Сезон {next_ep.season}, Эпизод {next_ep.episode}")
				else:
					print("   ⏹️ Следующий эпизод не найден (возможно, это последний эпизод)")
				
				# 8. Демонстрация скачивания
				print(f"\n8️⃣ 📥 Демонстрация функции скачивания...")
				if qualities:
					quality_to_download = str(qualities[0].quality)
					print(f"   🎯 Готово к скачиванию:")
					print(f"      - Качество: {quality_to_download}p")
					print(f"      - Озвучка: {first_voice_name}")
					print(f"      - Эпизод: 1x1")
					
					print(f"   ⬇️ Начинаем скачивание...")
					output_path = await client.download_video(
					    player_id=player_id,
					    season="1",
					    episode="1",
					    voice_id=first_voice_id, 
					    quality=quality_to_download,
					    output_dir="./downloads"
					)
					print(f"   ✅ Видео скачано: {output_path}")
				else:
					print("   ❌ Нет доступных качеств для скачивания")
			
			# 9. Дополнительная информация
			print(f"\n9️⃣ 📈 Статистика сериала:")
			total_episodes = 0
			total_voices = 0
			
			for season_num, season_info in series_data.seasons.items():
				episodes_in_season = len(set(ep.episode for ep in season_info.episodes))
				voices_in_season = len(season_info.episodes)
				total_episodes += episodes_in_season
				total_voices += voices_in_season
				print(f"   📺 Сезон {season_num}: {episodes_in_season} эпизодов, {voices_in_season} вариантов озвучки")
			
			print(f"   📊 Итого: {total_episodes} эпизодов, {total_voices} вариантов озвучки")
			
			print(f"\n{'='*60}")
			print(f"🎉 Демонстрация завершена успешно!")
			print(f"{'='*60}")
				
		except VideoNotFoundError as e:
			print(f"❌ Ошибка: {e}")
		except Exception as e:
			print(f"❌ Неожиданная ошибка: {e}")

if __name__ == "__main__":

	query = "Ван-пис"
	print("🚀 Запуск основного примера...")
	asyncio.run(main(query))
	
