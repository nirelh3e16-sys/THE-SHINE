"""Базовые тесты чистой логики (запуск: python -m unittest discover tests)."""
import json
import os
import random
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from game.save_system import SaveSystem, SINS, DEFAULT_SAVE
from game.settings import load_config
from game.systems.events import load_events, apply_effects, can_choose
from game.systems.items import ItemDatabase, BASE_STATS
from game.systems.morality import Morality, TESTIMONIES
from game.world.dungeon import Dungeon, generate_layout, validate_layout, DIRS
from game.world.zones import ZONES, ZONE_ORDER

try:
    import pygame  # noqa: F401
    HAS_PYGAME = True
except ImportError:
    HAS_PYGAME = False


class LayoutTests(unittest.TestCase):
    def test_layouts_are_connected_for_many_seeds(self):
        for seed in range(300):
            for n in (5, 8, 10, 20):
                rooms = generate_layout(n, random.Random(seed))
                self.assertEqual(validate_layout(rooms), [], f"seed={seed} n={n}")
                self.assertGreaterEqual(len(rooms), 5)

    def test_special_rooms_exist(self):
        rooms = generate_layout(8, random.Random(1))
        kinds = {r.kind for r in rooms.values()}
        self.assertTrue({"start", "boss", "treasure", "shop"} <= kinds)

    def test_dungeon_items_unique(self):
        db = ItemDatabase.from_file()
        d = Dungeon(7, 10, sorted(db.items))
        used = [i for ids in d.item_for_room.values() for i in ids]
        self.assertEqual(len(used), len(set(used)))

    def test_suburb_layout_has_houses_and_is_valid(self):
        for seed in range(200):
            rooms = generate_layout(9, random.Random(seed), extra_kinds=("house", "house"))
            self.assertEqual(validate_layout(rooms), [], f"seed={seed}")
            self.assertGreaterEqual(sum(1 for r in rooms.values() if r.kind == "house"), 1)

    def test_house_layout_is_small_valid_and_has_reward(self):
        for seed in range(200):
            d = Dungeon(f"h{seed}", 3 + seed % 2, ["broom", "old_tv", "black_halo"], house=True)
            self.assertEqual(validate_layout(d.specs, require_boss=False), [], f"seed={seed}")
            kinds = [s.kind for s in d.specs.values()]
            self.assertNotIn("boss", kinds)
            self.assertNotIn("shop", kinds)
            self.assertEqual(kinds.count("treasure"), 1)
            self.assertLessEqual(len(d.specs), 4)

    def test_zones_are_complete(self):
        for zid in ZONE_ORDER:
            z = ZONES[zid]
            for key in ("name", "floor", "wall", "obstacle", "enemy_pool", "boss", "boss_name", "boss_testimony", "music_combat"):
                self.assertIn(key, z, f"{zid}.{key}")
            self.assertIn(z["boss_testimony"], TESTIMONIES)
        self.assertIn("house", ZONES)

    @unittest.skipUnless(HAS_PYGAME, "pygame не установлен")
    def test_city_enemy_behaviors_are_known(self):
        from game.entities.enemy import BEHAVIORS
        from game.settings import DATA_DIR
        with open(DATA_DIR / "enemies.json", encoding="utf-8") as f:
            enemies = json.load(f)
        for kind, d in enemies.items():
            self.assertIn(d["behavior"], BEHAVIORS, kind)
        for kind in ("rad_rat", "mutant_cop", "drone", "living_car", "ad_tv", "eye_swarm", "fragment", "glitch"):
            self.assertIn(kind, enemies)

    def test_zone_order(self):
        self.assertEqual(ZONE_ORDER, ["forest", "suburbs", "city", "center", "shine"])

    def test_center_zone_music_and_boss_keys(self):
        z = ZONES["center"]
        self.assertEqual(z["boss"], "chaos")
        self.assertEqual(z["music_boss"], "chaos_boss")
        self.assertEqual(z["music_combat"], "center_combat")
        self.assertIn("eye_swarm", dict(z["enemy_pool"]))

    def test_all_music_keys_have_files_declared(self):
        import re
        src = (Path(__file__).resolve().parent.parent / "game" / "systems" / "audio.py").read_text(encoding="utf-8")
        for key in ("combat", "calm", "boss", "suburb_combat", "city_combat", "center_combat", "chaos_boss", "shine_boss", "menu"):
            self.assertRegex(src, rf'"{key}": "[^"]+\.mp3"')

    def test_final_arena_is_single_boss_room(self):
        d = Dungeon("x", 5, [], arena=True)
        self.assertEqual(list(d.specs), [(0, 0)])
        self.assertEqual(d.specs[(0, 0)].kind, "boss")
        self.assertEqual(d.specs[(0, 0)].doors, {})
        z = ZONES["shine"]
        self.assertTrue(z["arena"] and z["music_boss"] == "shine_boss" and "judgment_theme" in z)

    def test_secret_ending_needs_all_specific_testimonies(self):
        from game.systems.morality import SECRET_REQUIRED
        m = Morality(1)
        self.assertFalse(m.secret_unlocked())
        for t in SECRET_REQUIRED[:-1]:
            m.add_testimony(t)
        self.assertFalse(m.secret_unlocked())
        self.assertEqual(m.secret_progress(), len(SECRET_REQUIRED) - 1)
        m.add_testimony(SECRET_REQUIRED[-1])
        self.assertTrue(m.secret_unlocked())
        # свидетельства прошлых забегов тоже считаются
        legacy = Morality(2, legacy_testimonies=list(SECRET_REQUIRED))
        self.assertTrue(legacy.secret_unlocked())

    def test_endings_defined(self):
        import re
        src = (Path(__file__).resolve().parent.parent / "game" / "states.py").read_text(encoding="utf-8")
        for text in ("Ты всё ещё не заслужил это.", "Но, наверное, никто не заслуживает.", "Ну... правила есть правила."):
            self.assertIn(text, src)
        self.assertIn("endings", DEFAULT_SAVE)

    def test_zone_enemies_exist(self):
        from game.settings import DATA_DIR
        with open(DATA_DIR / "enemies.json", encoding="utf-8") as f:
            enemies = json.load(f)
        for z in ZONES.values():
            for kind, _ in z["enemy_pool"]:
                self.assertIn(kind, enemies)
        self.assertIn("neighbor", enemies)

    def test_same_seed_same_layout(self):
        a = generate_layout(9, random.Random(5))
        b = generate_layout(9, random.Random(5))
        self.assertEqual({p: (s.kind, s.doors) for p, s in a.items()}, {p: (s.kind, s.doors) for p, s in b.items()})


class ItemTests(unittest.TestCase):
    def setUp(self):
        self.db = ItemDatabase.from_file()

    def test_at_least_12_items_with_valid_fields(self):
        self.assertGreaterEqual(len(self.db.items), 12)

    def test_base_stats(self):
        self.assertEqual(self.db.stats([])["damage"], BASE_STATS["damage"])

    def test_mask_trades_hp_for_damage(self):
        s = self.db.stats(["cracked_mask"])
        self.assertEqual(s["max_hp"], 4)
        self.assertGreater(s["damage"], BASE_STATS["damage"])

    def test_revolver_slow_and_strong(self):
        s = self.db.stats(["rusty_revolver"])
        self.assertGreater(s["damage"], BASE_STATS["damage"] * 2)
        self.assertGreater(s["fire_delay"], BASE_STATS["fire_delay"] * 2)

    def test_add_applies_before_mul(self):
        s = self.db.stats(["rusty_revolver", "radioactive_burger"])
        self.assertAlmostEqual(s["damage"], (BASE_STATS["damage"] + 1.0) * 2.4)

    def test_combos(self):
        self.assertIn("explosive_shots", self.db.flags(["rusty_revolver", "black_halo"]))
        self.assertIn("toxic_sweep", self.db.flags(["broom", "radioactive_burger"]))
        self.assertIn("tv_soldier", self.db.flags(["old_tv", "toy_soldier"]))
        self.assertNotIn("toxic_sweep", self.db.flags(["broom"]))
        self.assertGreaterEqual(len(self.db.combos), 3)

    def test_new_suburb_items(self):
        s = self.db.stats(["baby_monitor"])
        self.assertEqual(s["max_hp"], 8)
        self.assertLess(s["speed"], BASE_STATS["speed"])
        self.assertLess(self.db.stats(["pressure_kettle"])["fire_delay"], BASE_STATS["fire_delay"])
        self.assertGreaterEqual(len(self.db.items), 16)

    def test_card_options_are_three_unique_unowned_items(self):
        for seed in range(50):
            rng = random.Random(seed)
            owned = ["broom", "old_tv"]
            options = self.db.card_options(owned, rng)
            self.assertEqual(len(options), 3)
            self.assertEqual(len(set(options)), 3)
            self.assertFalse(set(options) & set(owned))

    def test_card_options_when_few_items_left(self):
        owned = [i for i in self.db.items if i not in ("broom", "old_tv")]
        self.assertEqual(sorted(self.db.card_options(owned, random.Random(1))), ["broom", "old_tv"])
        self.assertEqual(self.db.card_options(list(self.db.items), random.Random(1)), [])

    def test_exactly_one_active_item_has_cooldown(self):
        actives = [i for i in self.db.items.values() if i.active]
        self.assertTrue(actives and all(a.active["cooldown"] > 0 for a in actives))


class SaveTests(unittest.TestCase):
    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            s = SaveSystem(Path(d) / "save.json")
            s.data["runs"] = 3
            s.data["testimonies"] = ["helped_dog"]
            self.assertTrue(s.write())
            self.assertEqual(SaveSystem(Path(d) / "save.json").data["runs"], 3)

    def test_missing_file_gives_defaults(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(SaveSystem(Path(d) / "none.json").data["runs"], 0)

    def test_corrupt_file_is_handled_and_backed_up(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "save.json"
            p.write_text("{not json", encoding="utf-8")
            s = SaveSystem(p)
            self.assertEqual(s.data["runs"], 0)
            self.assertTrue(p.with_suffix(".corrupt").exists())

    def test_wrong_types_are_ignored(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "save.json"
            p.write_text(json.dumps({"runs": "many", "seen_items": 5, "settings": 3}), encoding="utf-8")
            data = SaveSystem(p).data
            self.assertEqual(data["runs"], 0)
            self.assertEqual(data["seen_items"], [])
            self.assertEqual(data["settings"], DEFAULT_SAVE["settings"])


class MoralityEventTests(unittest.TestCase):
    class Ctx:
        def __init__(self):
            self.morality = Morality(1)
            self.hp = self.max_hp = self.coins = 0
            self.mods, self.msgs = [], []

        def change_hp(self, v): self.hp += v
        def change_max_hp(self, v): self.max_hp += v
        def add_coins(self, v): self.coins += v
        def add_run_mod(self, *a): self.mods.append(a)
        def give_random_item(self): self.items = getattr(self, "items", 0) + 1
        def spawn(self, kind, count): self.spawned = (kind, count)
        def notify(self, t, c="white"): self.msgs.append(t)

    def test_all_event_effects_apply(self):
        events = load_events()
        for ev in events.values():
            for choice in ev.get("choices", []):
                ctx = self.Ctx()
                apply_effects(choice["effects"], ctx)
            ctx = self.Ctx()
            apply_effects(ev.get("effects", []), ctx)

    def test_steal_raises_greed_and_logs_testimony(self):
        ev = load_events()["lost_dog"]
        ctx = self.Ctx()
        apply_effects(ev["choices"][2]["effects"], ctx)
        self.assertGreater(ctx.morality.run_sins["greed"], 0)
        self.assertIn("stole_from_man", ctx.morality.run_testimonies)
        self.assertEqual(ctx.coins, 8)

    def test_help_raises_mercy(self):
        ev = load_events()["lost_dog"]
        ctx = self.Ctx()
        apply_effects(ev["choices"][0]["effects"], ctx)
        self.assertGreater(ctx.morality.run_sins["mercy"], 0)
        self.assertEqual(ctx.hp, -1)

    def test_garage_sale_requires_coins_and_theft_spawns_enemies(self):
        ev = load_events()["garage_sale"]
        buy, steal, _ = ev["choices"]
        self.assertFalse(can_choose(buy, 5))
        self.assertTrue(can_choose(buy, 6))
        ctx = self.Ctx()
        apply_effects(buy["effects"], ctx)
        self.assertEqual((ctx.coins, ctx.items), (-6, 1))
        ctx = self.Ctx()
        apply_effects(steal["effects"], ctx)
        self.assertEqual(ctx.spawned, ("mutant_dog", 2))
        self.assertGreater(ctx.morality.run_sins["greed"], 0)

    def test_event_zones_reference_real_zones(self):
        for ev in load_events().values():
            for z in ev.get("zones", []):
                self.assertIn(z, ZONES)

    def test_testimony_only_once_and_unknown_rejected(self):
        m = Morality(1)
        self.assertTrue(m.add_testimony("helped_dog"))
        self.assertFalse(m.add_testimony("helped_dog"))
        with self.assertRaises(ValueError):
            m.add_testimony("nope")
        with self.assertRaises(ValueError):
            m.add_sin("nope", 1)

    def test_killing_overrides_numbers_and_legacy_separate(self):
        m = Morality(1, legacy_testimonies=["witness_saw"])
        m.add_sin("mercy", 10)
        m.add_testimony("killed_peaceful")
        self.assertIn("Убийца", m.verdict())
        self.assertEqual(m.all_testimonies(), ["killed_peaceful", "witness_saw"])
        self.assertEqual(Morality(2).run_testimonies, [])

    def test_all_sins_known(self):
        self.assertEqual(set(Morality(0).run_sins), set(SINS))


class IconTests(unittest.TestCase):
    PNG = b"\x89PNG\r\n\x1a\n" + b"fake-image-data"

    def _ico(self, entries):
        import struct
        head = struct.pack("<HHH", 0, 1, len(entries))
        offset = 6 + 16 * len(entries)
        table, blobs = b"", b""
        for width, blob in entries:
            table += struct.pack("<BBBBHHII", width, width, 0, 0, 1, 32, len(blob), offset + len(blobs))
            blobs += blob
        return head + table + blobs

    def test_extracts_largest_png_from_ico(self):
        from game.app_icon import extract_ico_png
        big = self.PNG + b"BIG"
        data = self._ico([(16, self.PNG + b"s"), (0, big)])   # ширина 0 означает 256
        self.assertEqual(extract_ico_png(data), big)

    def test_bad_ico_returns_none(self):
        from game.app_icon import extract_ico_png
        self.assertIsNone(extract_ico_png(b"nope"))
        self.assertIsNone(extract_ico_png(self._ico([(32, b"not a png")])))

    def test_publisher(self):
        from game.settings import PUBLISHER
        self.assertEqual(PUBLISHER, "FreeDom Studio")


class ConfigTests(unittest.TestCase):
    def test_bad_config_falls_back(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "c.json"
            p.write_text("garbage", encoding="utf-8")
            self.assertEqual(load_config(p)["window_scale"], 2)
            self.assertEqual(load_config(Path(d) / "missing.json")["zones"]["forest"]["rooms"], 8)


@unittest.skipUnless(HAS_PYGAME, "pygame не установлен")
class RoomTests(unittest.TestCase):
    def test_rooms_build_and_doors_are_passable(self):
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        from types import SimpleNamespace
        from game.entities.enemy import load_enemy_defs
        from game.world.room import Room
        from game.world.zones import ZONES
        data = SimpleNamespace(items=ItemDatabase.from_file(), enemies=load_enemy_defs(), events=load_events())
        for zid in ("forest", "suburbs", "city", "center"):
            for seed in range(50):
                d = Dungeon(seed, 8, sorted(data.items.items), extra_kinds=ZONES[zid].get("extra_kinds", ()))
                for pos, spec in d.specs.items():
                    room = Room(spec, ZONES[zid], seed, data, d.item_for_room.get(pos, []), zid + ":")
                    for direction in spec.doors:
                        p = room.door_pos(direction)
                        self.assertFalse(any(o.inflate(10, 10).collidepoint(p) for o in room.obstacles))


@unittest.skipUnless(HAS_PYGAME, "pygame не установлен")
class CityRoomTests(unittest.TestCase):
    def test_reshuffle_keeps_lanes_and_player_clear(self):
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        import pygame
        from types import SimpleNamespace
        from game.entities.enemy import load_enemy_defs
        from game.world.room import Room
        data = SimpleNamespace(items=ItemDatabase.from_file(), enemies=load_enemy_defs(), events=load_events())
        d = Dungeon(3, 9, sorted(data.items.items))
        spec = next(s for s in d.specs.values() if s.kind == "combat")
        room = Room(spec, ZONES["city"], 3, data, [], "city:")
        player = pygame.Vector2(240, 136)
        for _ in range(30):
            room.reshuffle_t = None
            self.assertTrue(room.begin_reshuffle(player))
            room.update_dynamic(2.0, player)
            for o in room.obstacles:
                self.assertFalse(o.inflate(40, 40).collidepoint(player))
                for direction in spec.doors:
                    self.assertFalse(o.inflate(10, 10).collidepoint(room.door_pos(direction)))


@unittest.skipUnless(HAS_PYGAME, "pygame не установлен")
class LaserTests(unittest.TestCase):
    def test_laser_hits_only_near_the_line(self):
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        import pygame
        from game.entities.hazard import Laser
        laser = Laser((0, 0), 0.0, warmup=0.0, width=12)
        self.assertTrue(laser.hits(pygame.Vector2(100, 3), 5))
        self.assertFalse(laser.hits(pygame.Vector2(100, 40), 5))
        self.assertFalse(laser.hits(pygame.Vector2(-50, 0), 5))


if __name__ == "__main__":
    unittest.main()
