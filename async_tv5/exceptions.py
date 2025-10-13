class TV5Error(Exception):
    """Базовое исключение для библиотеки TV5."""
    pass

class DomainNotFoundError(TV5Error):
    """Не удалось найти рабочий домен."""
    pass

class VideoNotFoundError(TV5Error):
    """Видео не найдено."""
    pass

class InvalidPlayerDataError(TV5Error):
    """Неверные данные плеера."""
    pass