"""Константы и загрузка config.json (без зависимости от pygame)."""
import json
import sys
from pathlib import Path

FROZEN = getattr(sys, "frozen", False)  # запуск из собранного exe (PyInstaller)
# RES_ROOT — ресурсы, упакованные в сборку; APP_ROOT — папка рядом с игрой (сохранения, внешние mus/config)
RES_ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
APP_ROOT = Path(sys.executable).resolve().parent if FROZEN else Path(__file__).resolve().parent.parent
ROOT = APP_ROOT
DATA_DIR = RES_ROOT / "data"
SAVE_DIR = APP_ROOT / "saves"
ASSET_DIR = RES_ROOT / "assets"
CONFIG_PATH = APP_ROOT / "config.json" if (APP_ROOT / "config.json").is_file() else RES_ROOT / "config.json"
MUSIC_DIRS = (APP_ROOT / "mus", RES_ROOT / "mus")  # внешняя папка mus рядом с игрой важнее упакованной
ICON_PATHS = (APP_ROOT / "icon.ico", RES_ROOT / "icon.ico", RES_ROOT / "assets" / "icon.ico")
PUBLISHER = "FreeDom Studio"

GAME_W, GAME_H = 480, 270
FPS = 60
# Игровое поле комнаты (внутренняя часть, без стен)
ROOM_X, ROOM_Y, ROOM_W, ROOM_H = 24, 32, 432, 208
DOOR_HALF = 16  # половина ширины проёма
MAX_DT = 0.05

DEFAULT_CONFIG = {
    "window_scale": 2,
    "fullscreen": False,
    "seed": None,
    "god_mode": False,
    "screen_shake": True,
    "master_volume": 0.6,
    "zones": {"forest": {"rooms": 8}, "suburbs": {"rooms": 9}, "city": {"rooms": 9}, "center": {"rooms": 9}},
    "max_player_projectiles": 120,
    "max_enemy_projectiles": 160,
    "max_particles": 300,
}


def load_config(path=CONFIG_PATH):
    """Читает config.json; при ошибке возвращает значения по умолчанию."""
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))
    try:
        with open(path, "r", encoding="utf-8") as f:
            user = json.load(f)
    except (OSError, json.JSONDecodeError):
        return cfg
    if not isinstance(user, dict):
        return cfg
    for key, value in user.items():
        if key == "zones" and isinstance(value, dict):
            for zone_id, zone_cfg in value.items():
                if isinstance(zone_cfg, dict):
                    cfg["zones"].setdefault(zone_id, {}).update(zone_cfg)
        elif key in cfg:
            cfg[key] = value
    return cfg
