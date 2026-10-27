"""Необязательная интеграция со Steamworks (достижения). Без Steam всё просто выключено.

Оверлей Steam для игры, добавленной в Steam как «сторонняя», от этого модуля не зависит:
он работает через вывод изображения на GPU (config.json: "gpu_present": true).
Для настоящего Steam API нужны пакет `steamworks`, steam_api64.dll и SteamworksPy64.dll рядом с игрой
и steam_appid.txt (или запуск из Steam с настоящим AppID).
"""


class Steam:
    def __init__(self, enabled=True):
        self.available = False
        self._sw = None
        if not enabled:
            return
        try:
            from steamworks import STEAMWORKS
        except ImportError:
            return
        try:
            sw = STEAMWORKS()
            sw.initialize()
        except Exception:  # noqa: BLE001 — нативная библиотека Steam может выбросить что угодно; игра из-за этого падать не должна
            return
        self._sw = sw
        self.available = True

    def update(self):
        if not self.available:
            return
        try:
            self._sw.run_callbacks()
        except Exception:  # noqa: BLE001
            self.available = False

    def unlock(self, name):
        """Открывает достижение Steam (если Steam подключён)."""
        if not self.available:
            return False
        try:
            self._sw.UserStats.SetAchievement(name)
            self._sw.UserStats.StoreStats()
        except Exception:  # noqa: BLE001
            return False
        return True
