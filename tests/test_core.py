"""Базовые тесты чистой логики (запуск: python -m unittest discover tests)."""
import json
import os
import random
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

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
        self.assertEqual(ZONE_ORDER, ["forest", "suburbs", "city", "center", "shine", "hell"])

    def test_center_zone_music_and_boss_keys(self):
        z = ZONES["center"]
        self.assertEqual(z["boss"], "chaos")
        self.assertEqual(z["music_boss"], "chaos_boss")
        self.assertEqual(z["music_combat"], "center_combat")
        self.assertIn("eye_swarm", dict(z["enemy_pool"]))

    def test_all_music_keys_have_files_declared(self):
        import re
        src = (Path(__file__).resolve().parent.parent / "game" / "systems" / "audio.py").read_text(encoding="utf-8")
        for key in ("combat", "calm", "boss", "suburb_combat", "city_combat", "center_combat", "chaos_boss", "shine_boss", "hell_combat", "hell_boss", "menu"):
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

    def test_active_items_have_cooldown_or_kill_recharge(self):
        actives = [i for i in self.db.items.values() if i.active]
        self.assertGreaterEqual(len(actives), 4)   # бомба, граната, аптечка, телефон
        for a in actives:
            by_time = a.active.get("cooldown", 0) > 0
            by_kills = a.active.get("recharge") == "kills" and a.active.get("kills", 0) > 0
            self.assertTrue(by_time or by_kills, a.id)


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


class CharacterTests(unittest.TestCase):
    def setUp(self):
        from game.systems.characters import load_characters
        self.db = ItemDatabase.from_file()
        self.chars = load_characters(self.db)

    def _stats(self, cid):
        c = self.chars[cid]
        return self.db.stats(c["start_items"], c["mods"])

    def test_five_plus_default_characters(self):
        self.assertEqual(list(self.chars), ["rob", "lumberjack", "tom", "bigshot", "glitch", "angel", "devil"])
        self.assertIsNone(self.chars["rob"]["unlock"])

    def test_hearts_match_design(self):
        hearts = {cid: self._stats(cid)["max_hp"] / 2 for cid in self.chars}
        self.assertEqual(hearts["rob"], 3)
        self.assertEqual(hearts["lumberjack"], 3)
        self.assertEqual(hearts["tom"], 6)
        self.assertEqual(hearts["bigshot"], 2)
        self.assertEqual(hearts["glitch"], 1)
        self.assertEqual(hearts["angel"], 3)
        self.assertEqual(hearts["devil"], 10)

    def test_speed_and_size(self):
        base = BASE_STATS["speed"]
        self.assertLess(self._stats("tom")["speed"], base)
        self.assertGreater(self.chars["tom"]["scale"], 1.0)
        self.assertGreater(self._stats("bigshot")["speed"], base)
        self.assertGreater(self._stats("glitch")["speed"], self._stats("bigshot")["speed"])

    def test_start_items(self):
        self.assertEqual(self.chars["lumberjack"]["start_items"], ["axe", "faulty_compass"])
        self.assertEqual(self.chars["tom"]["start_items"], ["baby_monitor", "half_nuke"])
        self.assertEqual(self.chars["bigshot"]["start_items"], ["toy_soldier", "pressure_kettle"])
        self.assertEqual(self.chars["glitch"]["start_items"], ["old_tv", "pressure_kettle"])
        self.assertEqual(self.chars["angel"]["start_items"], ["shotgun"])
        self.assertEqual(self.chars["devil"]["start_items"], ["compact_imp", "anchor", "angel_wings"])

    def test_angel_traits(self):
        self.assertEqual(set(self.chars["angel"]["traits"]), {"ghost", "gravity_immune"})

    def test_unlock_after_ten_boss_kills(self):
        from game.systems.characters import record_boss_kill, is_unlocked, unlocked_ids, progress
        save = {"boss_kills": {}}
        self.assertEqual(unlocked_ids(self.chars, save), ["rob"])
        for i in range(9):
            self.assertEqual(record_boss_kill(save, self.chars, "lumberjack"), [])
        self.assertFalse(is_unlocked(self.chars["lumberjack"], save))
        self.assertEqual(progress(self.chars["lumberjack"], save), (9, 10))
        self.assertEqual(record_boss_kill(save, self.chars, "lumberjack"), ["lumberjack"])   # ровно на 10-й
        self.assertTrue(is_unlocked(self.chars["lumberjack"], save))
        self.assertEqual(record_boss_kill(save, self.chars, "lumberjack"), [])               # на 11-й повторно не объявляется
        self.assertFalse(is_unlocked(self.chars["tom"], save))                                # другой босс — другой персонаж

    def test_each_character_has_own_boss(self):
        bosses = [c["unlock"]["boss"] for c in self.chars.values() if c["unlock"]]
        self.assertEqual(bosses, ["lumberjack", "neighbor", "mayor", "chaos", "shine", "imp"])
        self.assertTrue(all(c["unlock"]["kills"] == 10 for c in self.chars.values() if c["unlock"] and c["id"] != "devil"))
        self.assertEqual(self.chars["devil"]["unlock"]["kills"], 1)   # Дьявол открывается с первой победы над Бесом

    def test_devil_is_fast_and_unlocks_after_first_imp_kill(self):
        from game.systems.characters import record_boss_kill, is_unlocked
        self.assertGreater(self._stats("devil")["speed"], self._stats("glitch")["speed"])
        save = {"boss_kills": {}}
        self.assertFalse(is_unlocked(self.chars["devil"], save))
        self.assertEqual(record_boss_kill(save, self.chars, "imp"), ["devil"])
        self.assertTrue(is_unlocked(self.chars["devil"], save))

    def test_unlock_all_flag(self):
        from game.systems.characters import unlocked_ids
        self.assertEqual(len(unlocked_ids(self.chars, {}, unlock_all=True)), len(self.chars))

    def test_axe_and_shotgun_items(self):
        self.assertIn("axe", self.db.items["axe"].flags)
        self.assertIn("shotgun", self.db.items["shotgun"].flags)
        self.assertGreater(self.db.stats(["shotgun"])["fire_delay"], BASE_STATS["fire_delay"])

    def test_new_items_exist_with_expected_behaviour(self):
        items = self.db.items
        for item_id in ("grenade", "medkit", "anchor", "angel_wings", "bat", "smg", "broken_phone", "compact_imp"):
            self.assertIn(item_id, items)
        self.assertEqual(items["grenade"].active["cooldown"], 50.0)
        self.assertEqual(items["grenade"].active["damage"], 50.0)
        self.assertEqual(items["grenade"].active["radius"] * 2 / 16, 5.0)          # диаметр 5 блоков
        self.assertEqual(items["medkit"].active["kills"], 5)
        self.assertEqual(set(items["angel_wings"].flags), {"ghost", "gravity_immune"})
        self.assertLess(self.db.stats(["smg"])["fire_delay"], BASE_STATS["fire_delay"] / 2)   # скорострельный
        self.assertIn("anchor", items["anchor"].flags)
        self.assertIn("imp", items["compact_imp"].flags)

    def test_steam_is_optional(self):
        from game.steam import Steam
        s = Steam(enabled=False)
        self.assertFalse(s.available)
        s.update()
        self.assertFalse(s.unlock("ANYTHING"))


class AnchorTests(unittest.TestCase):
    def test_reach_grows_with_hold_and_is_capped_at_ten_blocks(self):
        from game.systems.anchor import reach_for_hold, MAX_REACH, MIN_REACH
        self.assertEqual(MAX_REACH, 160.0)
        self.assertEqual(reach_for_hold(0), MIN_REACH)
        self.assertLess(reach_for_hold(0.3), reach_for_hold(0.9))
        self.assertEqual(reach_for_hold(5.0), MAX_REACH)

    def test_orbit_release_fly_return(self):
        from game.systems.anchor import Anchor, reach_for_hold
        a = Anchor()
        player = (100.0, 100.0)
        for _ in range(30):
            a.holding(0.016, player)
        self.assertEqual(a.state, "orbit")
        dist = ((a.pos[0] - player[0]) ** 2 + (a.pos[1] - player[1]) ** 2) ** 0.5
        self.assertAlmostEqual(dist, 28.0, places=3)                       # вертится вокруг игрока
        hold = a.hold
        self.assertTrue(a.release((1.0, 0.0)))
        self.assertEqual(a.state, "fly")
        first_pass = a.pass_id
        start = a.pos
        for _ in range(400):
            a.step(0.016, player)
            if a.state == "return":
                break
        self.assertEqual(a.state, "return")
        self.assertAlmostEqual(a.pos[0] - start[0], reach_for_hold(hold), delta=10)
        self.assertGreater(a.pass_id, first_pass)                           # на возврате цель можно бить снова
        for _ in range(400):
            a.step(0.016, player)
            if a.state == "idle":
                break
        self.assertEqual(a.state, "idle")
        self.assertGreater(a.cooldown, 0)

    def test_longer_hold_flies_farther(self):
        from game.systems.anchor import Anchor
        def distance(hold_frames):
            a = Anchor()
            for _ in range(hold_frames):
                a.holding(0.016, (0.0, 0.0))
            a.release((1.0, 0.0))
            return a.target_dist
        self.assertGreater(distance(60), distance(10))


class InventoryKillRechargeTests(unittest.TestCase):
    def test_medkit_style_recharge_by_kills(self):
        from game.systems.inventory import Inventory
        db = ItemDatabase.from_file()
        inv = Inventory()
        inv.add(db.items["medkit"])
        self.assertTrue(inv.can_use_active())
        inv.start_kill_recharge(5)
        self.assertFalse(inv.can_use_active())
        for _ in range(4):
            inv.register_kill()
        self.assertFalse(inv.can_use_active())
        inv.register_kill()
        self.assertTrue(inv.can_use_active())
        inv.tick(100)    # время на такую перезарядку не влияет
        inv.register_kill()
        self.assertEqual(inv.kills_left, 0)


class StatsViewTests(unittest.TestCase):
    def test_stat_rows_show_hp_damage_speed(self):
        from game.systems.characters import load_characters
        from game.systems.statsview import build_stat_rows
        db = ItemDatabase.from_file()
        chars = load_characters(db)
        c = chars["tom"]
        owned = list(c["start_items"])
        player = SimpleNamespace(stats=db.stats(owned, c["mods"]), hp=12, max_hp=12, RADIUS=7.5, char=c,
                                 temp_buffs=[["damage", "mul", 1.5, 4.2]], inv=SimpleNamespace(items=owned), coins=7)
        rows = dict(build_stat_rows(player, rooms_cleared=3))
        self.assertEqual(rows["Персонаж"], "Том")
        self.assertIn("6 / 6 сердец", rows["Здоровье"])
        self.assertIn("Урон за выстрел", rows)
        self.assertIn("%", rows["Скорость движения"])
        self.assertEqual(rows["Монет"], "7")
        self.assertEqual(rows["Комнат пройдено"], "3")
        self.assertTrue(any(k.startswith("Временно") for k in rows))
        angel = chars["angel"]
        a = SimpleNamespace(stats=db.stats(angel["start_items"]), hp=6, max_hp=6, RADIUS=5, char=angel, temp_buffs=[],
                            inv=SimpleNamespace(items=angel["start_items"]), coins=0)
        self.assertIn("Особенности", dict(build_stat_rows(a)))


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
        for zid in ("forest", "suburbs", "city", "center", "hell"):
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


@unittest.skipUnless(HAS_PYGAME, "pygame не установлен")
class WeaponTests(unittest.TestCase):
    def _player(self, item_ids):
        import pygame
        db = ItemDatabase.from_file()
        return SimpleNamespace(stats=db.stats(item_ids), flags=db.flags(item_ids), pos=pygame.Vector2(100, 100))

    def test_shotgun_fires_five_pellets_and_axe_one_swing(self):
        import pygame
        from game.systems.combat import build_player_shots
        aim = pygame.Vector2(1, 0)
        pellets = build_player_shots(self._player(["shotgun"]), aim, random.Random(1))
        self.assertEqual(len(pellets), 5)
        swing = build_player_shots(self._player(["axe"]), aim, random.Random(1))
        self.assertEqual(len(swing), 1)
        self.assertEqual(swing[0].kind, "swing")
        self.assertTrue(swing[0].pierce)
        plain = build_player_shots(self._player([]), aim, random.Random(1))
        self.assertEqual(len(plain), 1)
        self.assertGreater(swing[0].damage, plain[0].damage)

    def test_character_sprites_build(self):
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        from game.sprites import make_player_sprite
        import json
        from game.settings import DATA_DIR
        with open(DATA_DIR / "characters.json", encoding="utf-8") as f:
            chars = json.load(f)["characters"]
        sizes = {c["id"]: make_player_sprite(c["id"], c["scale"]).get_size() for c in chars}
        self.assertGreater(sizes["tom"][0], sizes["rob"][0])

    def test_player_traits_and_hitbox(self):
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        from game.entities.player import Player
        from game.systems.characters import load_characters
        db = ItemDatabase.from_file()
        chars = load_characters(db)
        tom, rob, angel, glitch = (Player(db, chars[c]) for c in ("tom", "rob", "angel", "glitch"))
        self.assertGreater(tom.RADIUS, rob.RADIUS)
        self.assertTrue(angel.ghost and angel.gravity_immune and not rob.ghost)
        self.assertEqual(glitch.max_hp, 2)
        self.assertEqual(glitch.hp, 2)


@unittest.skipUnless(HAS_PYGAME, "pygame не установлен")
class BehaviorTests(unittest.TestCase):
    class FakeRoom:
        def __init__(self):
            self.hazards, self.notices, self.rule_requests, self.player_effects = [], [], [], []
            self.enemies, self.spawn_requests, self.player_shots, self.obstacles = [], [], [], []
            self.shake_request, self.reshuffle_t = None, None

        def confine(self, pos, r):
            return False

        def push_out(self, pos, r):
            return False

        def clamp_player(self, pos, r):
            pass

        def begin_reshuffle(self, *a, **k):
            return True

        def enable_gravity(self):
            pass

    def _player(self, item_ids=()):
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        from game.entities.player import Player
        return Player(ItemDatabase.from_file())

    def test_player_movement_has_inertia(self):
        import pygame
        p = self._player()
        room = self.FakeRoom()
        right = pygame.Vector2(1, 0)
        p.update(0.016, right, room)
        self.assertTrue(0 < p.cur_vel.length() < p.stats["speed"])          # не мгновенный разгон
        for _ in range(30):
            p.update(0.016, right, room)
        self.assertAlmostEqual(p.cur_vel.length(), p.stats["speed"], places=3)
        p.update(0.016, pygame.Vector2(), room)
        self.assertGreater(p.cur_vel.length(), 0)                            # и не мгновенная остановка
        for _ in range(60):
            p.update(0.016, pygame.Vector2(), room)
        self.assertEqual(p.cur_vel.length(), 0)

    def test_enemy_chase_has_inertia(self):
        import pygame
        from game.entities.enemy import Enemy, load_enemy_defs
        data = load_enemy_defs()["rad_rat"] if "rad_rat" in load_enemy_defs() else load_enemy_defs()["bush"]
        e = Enemy("rat", (100, 100), data)
        e.spawn_t = 0
        player = SimpleNamespace(pos=pygame.Vector2(300, 100))
        e.update(0.016, self.FakeRoom(), player, lambda *a, **k: None)
        self.assertTrue(0 < e.mv.length() < e.speed)

    def test_boss_hp_buffs(self):
        from game.entities.boss import SHINE, LUMBERJACK, MAYOR
        self.assertGreaterEqual(SHINE["hp"], 800)
        self.assertGreater(LUMBERJACK["hp"], 150)
        self.assertGreater(MAYOR["hp"], 270)

    def test_shine_dive_lands_on_player_and_is_untargetable_in_air(self):
        import pygame
        from game.entities.boss import Shine
        random.seed(3)
        room = self.FakeRoom()
        boss = Shine(pygame.Vector2(120, 120))
        boss.spawn_t = 0
        player = SimpleNamespace(pos=pygame.Vector2(300, 150), temp_buffs=[])
        shots = []
        shoot = lambda *a, **k: shots.append(a)
        boss._atk_dive(room, player, shoot)
        self.assertTrue(boss.airborne)
        self.assertFalse(boss.take_damage(5))        # в воздухе неуязвим
        self.assertFalse(boss.harmful)
        for _ in range(200):
            boss.update(0.016, room, player, shoot)
            if not boss.airborne:
                break
        self.assertFalse(boss.airborne)
        self.assertLess(boss.pos.distance_to(player.pos), 1.0)               # приземлился прямо на игрока
        self.assertTrue(any(h.active and h.rect.collidepoint(player.pos) for h in room.hazards))

    def test_shine_sometimes_dodges_incoming_shots(self):
        import pygame
        from game.entities.boss import Shine
        from game.entities.projectile import Projectile
        random.seed(1)
        room = self.FakeRoom()
        boss = Shine(pygame.Vector2(300, 150))
        boss.spawn_t = 0
        dodged = 0
        for _ in range(40):
            boss.dodge_cd = boss.dodge_t = 0
            shot = Projectile((220, 150), (220, 0), 3, 1, 3, True, (255, 255, 255))
            room.player_shots = [shot]
            boss._try_dodge(room)
            if boss.dodge_t > 0:
                dodged += 1
                self.assertAlmostEqual(abs(boss.dodge_vec.x), 0, places=3)   # уворот строго вбок от траектории
        self.assertGreater(dodged, 0)
        self.assertLess(dodged, 40)                                           # «иногда», а не всегда

    def test_shine_keeps_distance(self):
        import pygame
        from game.entities.boss import Shine
        room = self.FakeRoom()
        boss = Shine(pygame.Vector2(300, 150))
        boss.spawn_t = 0
        boss.timer = 99
        player = SimpleNamespace(pos=pygame.Vector2(280, 150), temp_buffs=[])
        start = boss.pos.distance_to(player.pos)
        for _ in range(30):
            boss.update(0.016, room, player, lambda *a, **k: None)
        self.assertGreater(boss.pos.distance_to(player.pos), start)


@unittest.skipUnless(HAS_PYGAME, "pygame не установлен")
class HellTests(unittest.TestCase):
    def test_imp_is_stronger_than_shine(self):
        from game.entities.boss import IMP, SHINE
        self.assertGreater(IMP["hp"], SHINE["hp"])

    def test_imp_sprites_have_same_size_as_shine_style(self):
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        from game.sprites import make_imp_boss, make_shine, IMP_IRIS
        sizes = {make_imp_boss(v).get_size() for v in (1, 2, 3)}
        self.assertEqual(len(sizes), 1)
        self.assertEqual(sizes, {make_shine(1).get_size()})     # тот же размер и форма: глаз с крыльями
        self.assertEqual(set(IMP_IRIS), {1, 2, 3})

    def test_arena_clamps_player_and_enemies_to_platform(self):
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        import pygame
        from game.entities.enemy import load_enemy_defs
        from game.world.dungeon import RoomSpec
        from game.world.room import Room
        data = SimpleNamespace(items=ItemDatabase.from_file(), enemies=load_enemy_defs(), events=load_events())
        room = Room(RoomSpec((0, 0), "boss", {"N": (0, -1)}, 3), ZONES["hell"], 1, data, [], "hell:")
        platform = pygame.Rect(110, 64, 260, 144)
        room.set_arena(platform)
        pos = pygame.Vector2(10, 10)
        room.clamp_player(pos, 5)
        self.assertTrue(platform.collidepoint(pos))
        far = pygame.Vector2(470, 260)
        self.assertTrue(room.confine(far, 6))
        self.assertTrue(platform.collidepoint(far))
        self.assertIsNone(room.check_exit(pygame.Vector2(240, 5)))      # из арены выйти нельзя

    def test_arena_shrinks_after_warning_and_keeps_minimum_size(self):
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        import pygame
        from game.entities.enemy import load_enemy_defs
        from game.world.dungeon import RoomSpec
        from game.world.room import Room
        data = SimpleNamespace(items=ItemDatabase.from_file(), enemies=load_enemy_defs(), events=load_events())
        room = Room(RoomSpec((0, 0), "boss", {}, 3), ZONES["hell"], 1, data, [], "hell:")
        room.set_arena(pygame.Rect(110, 64, 260, 144))
        before = room.arena.copy()
        self.assertTrue(room.begin_shrink())
        self.assertEqual(room.arena, before)                              # сначала только предупреждение
        room.update_dynamic(2.0, pygame.Vector2(240, 136))
        self.assertLess(room.arena.w, before.w)
        for _ in range(10):
            room.update_dynamic(2.0, pygame.Vector2(240, 136))
            room.begin_shrink()
        self.assertGreaterEqual(room.arena.w, 180)
        self.assertGreaterEqual(room.arena.h, 110)

    def test_imp_hovers_outside_platform_and_has_cooldowns(self):
        import pygame
        from game.entities.boss import Imp
        room = BehaviorTests.FakeRoom()
        room.arena, room.arena_warn_t = pygame.Rect(110, 64, 260, 144), None
        boss = Imp(pygame.Vector2(240, 30))
        boss.spawn_t = 0
        boss.timer = 99
        player = SimpleNamespace(pos=pygame.Vector2(240, 136), temp_buffs=[])
        for _ in range(200):
            boss.update(0.016, room, player, lambda *a, **k: None)
        self.assertFalse(room.arena.collidepoint(boss.pos))               # парит над лавой, а не на платформе
        boss.timer = 0
        random.seed(2)
        used = set()
        for _ in range(80):
            boss.state, boss.timer = "idle", 0
            room.hazards.clear()
            boss._choose(room, player, lambda *a, **k: None)
            used.add(boss.last)
        self.assertTrue({"fire", "breath", "geyser", "swoop"} <= used)
        self.assertTrue(all(boss.cd[k] > 0 for k in ("breath", "geyser") if k in used))

    def test_player_wings_item_gives_ghost_and_gravity_immunity(self):
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        from game.entities.player import Player
        db = ItemDatabase.from_file()
        p = Player(db)
        self.assertFalse(p.ghost)
        p.inv.add(db.items["angel_wings"])
        p.recompute()
        self.assertTrue(p.ghost and p.gravity_immune)


if __name__ == "__main__":
    unittest.main()
