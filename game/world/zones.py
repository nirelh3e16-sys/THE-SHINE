"""Описание зон. Новую зону можно добавить записью в ZONES и в ZONE_ORDER."""

ZONES = {
    "forest": {
        "id": "forest", "name": "ЛЕС", "outdoor": True,
        "floor": ((92, 176, 88), (84, 166, 82)), "wall": (52, 86, 60),
        "wall_decor": "trees", "obstacle": "rock",
        "enemy_pool": (("bush", 3), ("crow", 2), ("face_tree", 2)),
        "boss": "lumberjack", "boss_name": "ЛЕСНИК", "boss_testimony": "lumberjack_slain",
        "music_combat": "combat", "hp_mult": 1.0,
        "miniboss": "living_spruce",   # мини-босс — в комнате перед комнатой босса
    },
    "suburbs": {
        "id": "suburbs", "name": "ПРИГОРОД", "outdoor": True,
        "floor": ((130, 200, 102), (122, 192, 96)), "wall": (178, 124, 98),
        "wall_decor": "fence", "obstacle": "hedge", "road": True,
        "enemy_pool": (("mutant_dog", 3), ("mailman", 2), ("sprinkler", 2), ("cart", 2)),
        "boss": "neighbor", "boss_name": "СОСЕД", "boss_testimony": "neighbor_slain",
        "music_combat": "suburb_combat", "hp_mult": 1.3, "extra_kinds": ("house", "house"),
        "house_miniboss": "landlord",  # мини-босс живёт в одном из домов (в комнате перед наградой)
    },
    "city": {
        "id": "city", "name": "ГОРОД", "outdoor": True,
        "floor": ((116, 118, 134), (106, 108, 124)), "wall": (74, 68, 98),
        "wall_decor": "fence", "obstacle": "barrier", "road": True,
        "enemy_pool": (("rad_rat", 3), ("mutant_cop", 2), ("drone", 2), ("living_car", 1), ("ad_tv", 2)),
        "boss": "mayor", "boss_name": "МЭР", "boss_testimony": "mayor_slain",
        "music_combat": "city_combat", "hp_mult": 1.6,
        "modifiers": True, "shifted_doors": True,
        "miniboss": "tank",
    },
    "center": {
        "id": "center", "name": "ЦЕНТР", "outdoor": True,
        "floor": ((150, 60, 200), (138, 50, 188)), "wall": (46, 30, 90),
        "wall_decor": "acid", "obstacle": "mixed", "road": True, "road_v": True, "patchwork": True,
        "enemy_pool": (("eye_swarm", 3), ("fragment", 2), ("glitch", 2), ("face_tree", 1), ("ad_tv", 1), ("living_car", 1)),
        "boss": "chaos", "boss_name": "ХАОС", "boss_testimony": "chaos_slain",
        "music_combat": "center_combat", "music_boss": "chaos_boss", "hp_mult": 1.9,
        "modifiers": True, "shifted_doors": True,
    },
    "shine": {
        "id": "shine", "name": "ВРАТА", "outdoor": False, "ambient": (45, 45, 88, 0.72),
        "floor": ((255, 250, 225), (246, 238, 205)), "wall": (255, 238, 170),
        "wall_decor": "fence", "obstacle": "rock", "arena": True,
        "enemy_pool": (), "boss": "shine", "boss_name": "THE SHINE", "boss_testimony": "shine_defeated",
        "music_combat": "combat", "music_boss": "shine_boss", "hp_mult": 1.0,
        # после предательства «рай» рассыпается
        "judgment_theme": {"floor": ((72, 40, 96), (60, 30, 82)), "wall": (28, 10, 40), "wall_decor": "acid"},
    },
    "hell": {
        "id": "hell", "name": "АД", "outdoor": False, "ambient": (46, 10, 8, 0.68),
        "floor": ((54, 44, 52), (46, 37, 46)), "wall": (30, 22, 28),
        "wall_decor": "lava", "obstacle": "basalt", "burning": True,
        "enemy_pool": (("hellhound", 3), ("fire_imp", 2), ("magma_golem", 1), ("ember", 2), ("idol", 1)),
        "boss": "imp", "boss_name": "БЕС", "boss_testimony": "imp_slain",
        "music_combat": "hell_combat", "music_boss": "hell_boss", "hp_mult": 2.6,
        "modifiers": True, "shifted_doors": True, "boss_cutscene": "imp",
        "ends_run": "evil",   # портал после Беса — злая концовка (она открывает Небеса)
    },
    # Небеса: открываются после злой концовки; в них ведёт портал после The Shine
    "heaven": {
        "id": "heaven", "name": "НЕБЕСА", "outdoor": True, "always_day": True, "sky": True,
        "floor": ((250, 252, 255), (237, 243, 252)), "wall": (126, 196, 247),
        "wall_decor": "sky", "obstacle": "cloud", "passive_enemies": True,
        "enemy_pool": (("cherub", 3), ("cloudling", 2), ("halo_ring", 2), ("dove", 2), ("trumpeter", 1), ("stone_angel", 1)),
        "boss": "god", "boss_name": "БОГ", "boss_testimony": "god_slain", "final_boss": True,
        "music_combat": "heaven_combat", "music_boss": "god_boss", "hp_mult": 2.8,
        "boss_cutscene": "god", "miniboss": "gate_keeper",
    },
    # Внутренность дома: мини-данж, в который входят из комнаты «house»
    "house": {
        "id": "house", "name": "ДОМ", "outdoor": False, "ambient": (34, 28, 54, 0.72),
        "floor": ((178, 132, 92), (168, 122, 84)), "wall": (122, 86, 66),
        "wall_decor": "wallpaper", "obstacle": "crate", "interior": True,
        "enemy_pool": (("mutant_dog", 2), ("mailman", 1), ("sprinkler", 1)),
        "music_combat": "suburb_combat", "hp_mult": 1.2,
        "miniboss": "landlord",
    },
}
# В Ад попадают из разлома после The Shine, на Небеса — из небесного портала после The Shine (после злой концовки)
ZONE_ORDER = ["forest", "suburbs", "city", "center", "shine", "hell", "heaven"]
SIDE_ZONES = ("hell", "heaven")   # в обычном порядке порталов эти зоны не идут


def zone_room_count(zone_id, cfg):
    """Число комнат зоны из конфига, ограничено 5..20."""
    n = cfg.get("zones", {}).get(zone_id, {}).get("rooms", 8)
    try:
        n = int(n)
    except (TypeError, ValueError):
        n = 8
    return max(5, min(20, n))
