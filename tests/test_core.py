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
        self.assertEqual(ZONE_ORDER, ["forest", "suburbs", "city", "center", "shine", "hell", "heaven"])

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
        self.assertEqual(list(self.chars), ["rob", "lumberjack", "tom", "bigshot", "glitch", "angel", "devil", "soul"])
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
        bosses = [c["unlock"]["boss"] for c in self.chars.values() if c["unlock"] and "boss" in c["unlock"]]
        self.assertEqual(bosses, ["lumberjack", "neighbor", "mayor", "chaos", "shine", "imp"])
        self.assertTrue(all(c["unlock"]["kills"] == 10 for c in self.chars.values()
                            if c["unlock"] and "boss" in c["unlock"] and c["id"] != "devil"))
        self.assertEqual(self.chars["soul"]["unlock"], {"ending": "true"})   # Душа открывается True Ending
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


class DayCycleTests(unittest.TestCase):
    def test_run_starts_at_dawn_with_little_sun(self):
        from game.daycycle import day_state
        st = day_state(0.0)
        self.assertTrue(0 < st.elevation < 0.15)            # солнце только поднимается
        self.assertGreater(st.tint[0], st.tint[2])          # тёплый красноватый рассвет
        self.assertLess(st.sun_dx, -0.9)                    # солнце у левого горизонта

    def test_day_peak_sunset_and_night(self):
        from game.daycycle import day_state
        noon, sunset, night = day_state(0.25), day_state(0.52), day_state(0.75)
        self.assertEqual(noon.elevation, 1.0)
        self.assertEqual(noon.darkness, 0.0)
        self.assertEqual(noon.tint, (255, 255, 245))
        self.assertLess(sunset.elevation, 0.2)
        self.assertGreater(sunset.sun_dx, 0.9)              # закат справа
        self.assertLessEqual(night.elevation, 0)
        self.assertGreaterEqual(night.darkness, 0.7)
        self.assertFalse(night.has_sun)

    def test_cycle_is_continuous_and_loops(self):
        from game.daycycle import day_state
        prev = day_state(0.0)
        for i in range(1, 1001):
            cur = day_state(i / 1000)
            self.assertLess(abs(cur.darkness - prev.darkness), 0.05)
            self.assertLess(abs(cur.elevation - prev.elevation), 0.06)
            prev = cur
        self.assertEqual(day_state(1.0).tint, day_state(0.0).tint)
        self.assertEqual(day_state(1.25).elevation, day_state(0.25).elevation)

    def test_shadows_are_longer_and_flipped_at_low_sun(self):
        from game.daycycle import day_state, shadow_params
        dx_m, _, len_m, str_m = shadow_params(day_state(0.04))     # утро
        dx_n, _, len_n, str_n = shadow_params(day_state(0.25))     # полдень
        dx_e, _, len_e, _ = shadow_params(day_state(0.50))         # вечер
        self.assertGreater(len_m, len_n)
        self.assertGreater(len_e, len_n)
        self.assertGreater(dx_m, 0)                                  # утром тень падает вправо
        self.assertLess(dx_e, 0)                                     # вечером — влево
        self.assertAlmostEqual(dx_n, 0, delta=0.15)                  # в полдень почти строго вниз
        self.assertEqual(shadow_params(day_state(0.75)), (0.0, 0.0, 0.0, 0.0))   # ночью солнечных теней нет

    def test_indoor_zones_are_dark_like_night_and_outdoor_follow_clock(self):
        from game.daycycle import effective_state
        from game.world.zones import ZONES
        for zid in ("house", "hell", "shine"):
            st = effective_state(ZONES[zid], 120.0, time_mode="day")
            self.assertFalse(st.outdoor)
            self.assertFalse(st.has_sun)                              # нет солнца даже «днём»
            self.assertGreaterEqual(st.darkness, 0.6)
        for zid in ("forest", "suburbs", "city", "center"):
            self.assertTrue(ZONES[zid]["outdoor"])
        day = effective_state(ZONES["forest"], 0, time_mode="day")
        night = effective_state(ZONES["forest"], 0, time_mode="night")
        self.assertLess(day.darkness, 0.1)
        self.assertGreater(night.darkness, 0.6)
        auto0 = effective_state(ZONES["forest"], 0.0, 480.0)
        auto_noon = effective_state(ZONES["forest"], 480 * 0.25, 480.0)
        self.assertGreater(auto0.darkness, auto_noon.darkness)

    def test_night_brightness_and_lights_off_keep_game_playable(self):
        from game.daycycle import effective_state
        from game.world.zones import ZONES
        dark = effective_state(ZONES["forest"], 0, time_mode="night", night_mult=1.0)
        light = effective_state(ZONES["forest"], 0, time_mode="night", night_mult=0.6)
        self.assertLess(light.darkness, dark.darkness)
        no_lights = effective_state(ZONES["hell"], 0, lights_on=False)
        self.assertLessEqual(no_lights.darkness, 0.35)               # без света нельзя оставлять почти чёрный экран


class GraphicsSettingsTests(unittest.TestCase):
    def test_defaults_and_sanitize(self):
        from game.graphics_settings import sanitize, DEFAULTS
        self.assertEqual(sanitize(None), DEFAULTS)
        cfg = sanitize({"shadows": False, "shadow_strength": 2, "time_mode": "night", "night_brightness": 7, "sun_glare": "yes", "junk": 1})
        self.assertFalse(cfg["shadows"])
        self.assertEqual(cfg["shadow_strength"], 2)
        self.assertEqual(cfg["time_mode"], "night")
        self.assertEqual(cfg["night_brightness"], DEFAULTS["night_brightness"])   # некорректное значение заменено
        self.assertTrue(cfg["sun_glare"])
        self.assertNotIn("junk", cfg)

    def test_every_effect_can_be_toggled_independently(self):
        from game.graphics_settings import sanitize, cycle, TIME_MODES
        cfg = sanitize(None)
        for key in ("shaders", "shadows", "sun_glare", "lights"):
            before = dict(cfg)
            cycle(cfg, key)
            self.assertNotEqual(cfg[key], before[key])
            self.assertEqual({k: v for k, v in cfg.items() if k != key}, {k: v for k, v in before.items() if k != key})
        seen = {cfg["time_mode"]}
        for _ in range(len(TIME_MODES)):
            seen.add(cycle(cfg, "time_mode"))
        self.assertEqual(seen, set(TIME_MODES))
        for _ in range(3):
            cycle(cfg, "shadow_strength")
        self.assertEqual(cfg["shadow_strength"], sanitize(None)["shadow_strength"])   # цикл из трёх значений


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


@unittest.skipUnless(HAS_PYGAME, "pygame не установлен")
class LightingRenderTests(unittest.TestCase):
    def setUp(self):
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        import pygame
        from game.graphics_settings import sanitize
        from game.lighting import Lighting
        self.pygame, self.gfx, self.light = pygame, sanitize(None), Lighting()

    def _frame(self):
        surf = self.pygame.Surface((480, 270))
        surf.fill((200, 200, 200))
        return surf

    def test_shadow_darkens_ground_next_to_actor_only_with_sun(self):
        from game.daycycle import day_state
        v = self.pygame.Vector2
        morning = self._frame()
        self.light.draw_shadows(morning, v(0, 0), [(240, 135, 14, 16)], day_state(0.04), self.gfx)
        self.assertLess(morning.get_at((250, 137))[0], 200)            # утром тень лежит справа от моба
        self.assertEqual(morning.get_at((225, 137))[0], 200)           # а слева — чисто
        self.assertEqual(morning.get_at((20, 20))[0], 200)             # далеко от моба кадр не тронут
        night = self._frame()
        self.light.draw_shadows(night, v(0, 0), [(240, 135, 14, 16)], day_state(0.75), self.gfx)
        self.assertEqual(night.get_at((250, 137))[0], 200)             # ночью солнечных теней нет

    def test_night_is_dark_but_player_light_reveals_surroundings(self):
        from game.daycycle import effective_state
        from game.world.zones import ZONES
        state = effective_state(ZONES["forest"], 0, time_mode="night")
        surf = self._frame()
        self.light.apply(surf, state, [(240, 135, 70, (255, 236, 190), 1.0)], self.gfx)
        near, far = surf.get_at((240, 135)), surf.get_at((15, 15))
        self.assertGreater(sum(near[:3]), sum(far[:3]) * 2)             # рядом со светом заметно ярче
        self.assertLess(sum(far[:3]), 3 * 100)                          # вдали темно

    def test_lights_off_does_not_crash_and_sun_glare_brightens_day(self):
        from game.daycycle import effective_state
        from game.world.zones import ZONES
        gfx = dict(self.gfx, sun_glare=False)
        state = effective_state(ZONES["forest"], 0, time_mode="day")
        plain = self._frame()
        self.light.apply(plain, state, [], gfx)
        glare = self._frame()
        self.light.apply(glare, state, [], dict(gfx, sun_glare=True))
        self.assertGreaterEqual(sum(glare.get_at((100, 20))[:3]), sum(plain.get_at((100, 20))[:3]))
        self.light.apply(self._frame(), effective_state(ZONES["hell"], 0), [(100, 100, 50, (255, 100, 30), 1.0)], dict(gfx, lights=False))


class MiniBossLayoutTests(unittest.TestCase):
    """Мини-босс стоит в комнате прямо перед комнатой босса (в доме — перед наградой)."""

    @staticmethod
    def _reachable_without(rooms, banned):
        seen, stack = {(0, 0)}, [(0, 0)]
        while stack:
            for nxt in rooms[stack.pop()].doors.values():
                if nxt != banned and nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        return seen

    def test_miniboss_blocks_the_way_to_the_boss(self):
        from game.world.dungeon import miniboss_host
        for seed in range(300):
            rooms = generate_layout(5 + seed % 8, random.Random(seed), mini_kind="miniboss")
            self.assertEqual(validate_layout(rooms), [], f"seed={seed}")
            minis = [r for r in rooms.values() if r.kind == "miniboss"]
            self.assertEqual(len(minis), 1, f"seed={seed}")
            boss = next(r for r in rooms.values() if r.kind == "boss")
            if miniboss_host(rooms, boss) is not None:
                self.assertIn(minis[0].pos, boss.doors.values(), f"seed={seed}")
                self.assertNotIn(boss.pos, self._reachable_without(rooms, minis[0].pos), f"seed={seed}")

    def test_no_miniboss_without_request_and_specials_survive(self):
        for seed in range(100):
            rooms = generate_layout(9, random.Random(seed))
            self.assertFalse(any(r.kind == "miniboss" for r in rooms.values()))
            kinds = {r.kind for r in generate_layout(9, random.Random(seed), mini_kind="miniboss").values()}
            self.assertTrue({"start", "boss", "miniboss", "treasure", "shop"} <= kinds, f"seed={seed}")

    def test_house_has_miniboss_before_reward(self):
        from game.world.dungeon import miniboss_host
        for seed in range(200):
            d = Dungeon(f"h{seed}", 3 + seed % 2, ["broom", "old_tv"], house=True, mini_kind="miniboss")
            self.assertEqual(validate_layout(d.specs, require_boss=False), [], f"seed={seed}")
            kinds = [s.kind for s in d.specs.values()]
            self.assertEqual(kinds.count("miniboss"), 1)
            self.assertEqual(kinds.count("treasure"), 1)
            reward = next(s for s in d.specs.values() if s.kind == "treasure")
            if miniboss_host(d.specs, reward) is not None:
                mini = next(s for s in d.specs.values() if s.kind == "miniboss")
                self.assertIn(mini.pos, reward.doors.values())

    def test_zone_config(self):
        self.assertEqual(ZONES["forest"]["miniboss"], "living_spruce")
        self.assertEqual(ZONES["city"]["miniboss"], "tank")
        self.assertEqual(ZONES["suburbs"]["house_miniboss"], "landlord")
        self.assertEqual(ZONES["house"]["miniboss"], "landlord")
        for zid in ("center", "hell", "shine"):
            self.assertNotIn("miniboss", ZONES[zid])


class MiniBossItemTests(unittest.TestCase):
    def setUp(self):
        self.db = ItemDatabase.from_file()

    def test_drops_exist_and_are_drop_only(self):
        for item_id in ("thorn_cannon", "old_remote", "kevlar_vest"):
            self.assertTrue(self.db.items[item_id].drop_only, item_id)
        self.assertNotIn("thorn_cannon", self.db.regular_ids())
        for seed in range(100):
            for opt in self.db.card_options([], random.Random(seed)):
                self.assertFalse(self.db.items[opt].drop_only)

    def test_vest_adds_three_hearts_and_armor_flag(self):
        self.assertEqual(self.db.stats(["kevlar_vest"])["max_hp"], BASE_STATS["max_hp"] + 6)
        self.assertIn("armor", self.db.flags(["kevlar_vest"]))

    def test_new_combos(self):
        self.assertIn("thorn_fury", self.db.flags(["thorn_cannon", "smg"]))
        self.assertNotIn("thorn_fury", self.db.flags(["thorn_cannon"]))
        self.assertIn("channel_loot", self.db.flags(["old_remote", "old_tv"]))
        self.assertIn("homing", self.db.flags(["old_remote"]))
        for item_id in ("thorn_cannon", "old_remote", "kevlar_vest"):
            self.assertIn(item_id, {i for c in self.db.combos for i in c["needs"]} | {"kevlar_vest"})

    def test_drop_items_have_names_and_icons_defined(self):
        for item_id in ("thorn_cannon", "old_remote", "kevlar_vest"):
            self.assertTrue(self.db.items[item_id].name)
            self.assertIn(self.db.items[item_id].icon, ("thorn", "remote", "vest"))


class NeedlesTests(unittest.TestCase):
    def test_stab_only_when_moving_and_expires_after_three_seconds(self):
        from game.systems.needles import Needles
        n = Needles()
        self.assertEqual(n.update(0.1, 0, 0), 0)          # иголок нет
        n.add()
        self.assertEqual(n.update(0.1, 0, 0), 0)          # запомнили позицию
        self.assertEqual(n.update(0.1, 0, 0), 0)          # стоит на месте — не колет
        self.assertEqual(n.update(0.1, 30, 0), 1)         # сдвинулся — укол
        self.assertEqual(n.update(0.1, 31, 0), 0)         # мелкий шаг копится
        n.update(2.9, 31, 0)
        self.assertEqual(n.count, 0)                      # через 3 секунды иголка выпала
        self.assertEqual(n.update(0.1, 90, 0), 0)         # без иголок движение безопасно

    def test_damage_grows_with_three_needles_and_stack_is_limited(self):
        from game.systems.needles import Needles, MAX_STUCK
        n = Needles()
        n.add(2)
        self.assertEqual(n.stab_damage(), 1)
        n.add()
        self.assertEqual(n.stab_damage(), 2)
        n.add(20)
        self.assertEqual(n.count, MAX_STUCK)


@unittest.skipUnless(HAS_PYGAME, "pygame не установлен")
class MiniBossBehaviorTests(unittest.TestCase):
    class FakeRoom:
        def __init__(self):
            from game.entities.enemy import load_enemy_defs
            self.hazards, self.notices, self.enemies, self.spawn_requests = [], [], [], []
            self.shake_request = None
            self.data = SimpleNamespace(enemies=load_enemy_defs())

        def confine(self, pos, r):
            pos.x = max(24 + r, min(24 + 432 - r, pos.x))
            pos.y = max(32 + r, min(32 + 208 - r, pos.y))
            return False

    def setUp(self):
        import pygame
        random.seed(5)
        self.V = pygame.Vector2
        self.room = self.FakeRoom()
        self.player = SimpleNamespace(pos=self.V(380, 200))
        self.shots = []

    def shoot(self, pos, direction, speed, dmg, radius=3, color=(0, 0, 0), kind="shot"):
        self.shots.append((self.t, kind, dmg, self.V(pos), self.V(direction) * speed))

    def simulate(self, boss, seconds, dt=1 / 60):
        self.t = 0.0
        self.room.enemies = [boss] + [e for e in self.room.enemies if e is not boss]
        while self.t < seconds:
            for e in list(self.room.enemies):
                e.update(dt, self.room, self.player, self.shoot)
            for h in self.room.hazards:
                h.update(dt)
            self.t += dt

    def make(self, kind):
        from game.entities.miniboss import create_miniboss
        boss = create_miniboss(kind, self.V(240, 90))
        boss.spawn_t = 0
        return boss

    def test_all_three_exist_with_drops_and_names(self):
        from game.entities.miniboss import MINIBOSSES, create_miniboss
        self.assertEqual(set(MINIBOSSES), {"living_spruce", "landlord", "tank", "gate_keeper"})
        drops = {k: MINIBOSSES[k].drop_item for k in MINIBOSSES}
        self.assertEqual(drops, {"living_spruce": "thorn_cannon", "landlord": "old_remote", "tank": "kevlar_vest",
                                 "gate_keeper": None})
        for k in MINIBOSSES:
            b = create_miniboss(k, self.V(100, 100))
            self.assertTrue(b.is_miniboss)
            self.assertFalse(getattr(b, "is_boss", False))   # не считается боссом зоны
        with self.assertRaises(ValueError):
            create_miniboss("nope", self.V(0, 0))

    def test_spruce_shoots_harmless_needles_and_adds_roots_in_phase_two(self):
        boss = self.make("living_spruce")
        self.simulate(boss, 12)
        needles = [s for s in self.shots if s[1] == "needle"]
        self.assertGreater(len(needles), 8)
        self.assertTrue(all(s[2] == 0 for s in needles))           # сами иголки урона не наносят
        self.assertEqual(self.room.hazards, [])                    # корни — только во второй фазе
        boss.hp = boss.max_hp * 0.4
        self.simulate(boss, 25)
        self.assertEqual(boss.phase, 2)
        self.assertTrue(any(n[1] == "red" for n in self.room.notices) or self.room.notices)
        self.assertTrue(any(h.kind == "drop" for h in self.room.hazards))

    def test_landlord_throws_dogs_then_turns_on_tv_every_five_seconds(self):
        boss = self.make("landlord")
        self.simulate(boss, 8)
        dogs = [e for e in self.room.enemies if e.kind == "mutant_dog"]
        self.assertTrue(1 <= len(dogs) <= 4)
        self.assertFalse(boss.tv_on)
        self.assertEqual([s for s in self.shots if s[2] == 1 and s[1] == "shot"], [])   # до второй фазы телевизор молчит
        boss.hp = boss.max_hp * 0.4
        self.shots.clear()
        self.simulate(boss, 18)
        self.assertTrue(boss.tv_on)
        times = sorted({round(s[0], 1) for s in self.shots})
        bursts, last = [], None
        for t in times:
            if last is None or t - last > 0.5:
                bursts.append(t)
            last = t
        self.assertGreaterEqual(len(bursts), 2)
        gaps = [b - a for a, b in zip(bursts, bursts[1:])]
        self.assertTrue(all(abs(g - 5.0) < 0.3 for g in gaps), gaps)      # ровно каждые 5 секунд
        self.assertGreaterEqual(len([s for s in self.shots if round(s[0], 1) == bursts[0]]), 8)   # кластер

    def test_landlord_tv_causes_interference_before_shooting(self):
        boss = self.make("landlord")
        boss.hp = boss.max_hp * 0.4
        glitch_seen = False
        self.t = 0.0
        for _ in range(60 * 14):
            boss.update(1 / 60, self.room, self.player, self.shoot)
            glitch_seen = glitch_seen or boss.ui_glitch
            self.t += 1 / 60
        self.assertTrue(glitch_seen)

    def test_tank_keeps_driving_to_player_and_fires_grenade_every_five_seconds(self):
        boss = self.make("tank")
        self.player.pos = self.V(400, 210)
        start = boss.pos.distance_to(self.player.pos)
        launched = []
        self.t = 0.0
        prev = 0
        for _ in range(60 * 18):
            boss.update(1 / 60, self.room, self.player, self.shoot)
            if len(boss.shells) > prev or (boss.shells and boss.shells[-1]["t"] == 0.0):
                launched.append(round(self.t, 1))
            prev = len(boss.shells)
            for h in self.room.hazards:
                h.update(1 / 60)
            self.t += 1 / 60
        self.assertLess(boss.pos.distance_to(self.player.pos), start)      # едет к игроку
        self.assertGreaterEqual(len(launched), 3)
        gaps = [b - a for a, b in zip(launched, launched[1:])]
        self.assertTrue(all(abs(g - 5.0) < 0.3 for g in gaps), launched)
        self.assertTrue(any(h.kind == "blast" for h in self.room.hazards))

    def test_tank_fires_three_grenades_in_second_phase(self):
        boss = self.make("tank")
        boss.hp = boss.max_hp * 0.4
        self.simulate(boss, 3.0)
        self.assertEqual(boss.phase, 2)
        self.assertEqual(len(boss.shells), 3)

    def test_minibosses_resist_knockback(self):
        for kind in ("living_spruce", "landlord", "tank"):
            boss = self.make(kind)
            boss.take_damage(1, self.V(1, 0), 400)
            self.assertLess(boss.knock.length(), 100, kind)


@unittest.skipUnless(HAS_PYGAME, "pygame не установлен")
class MiniBossItemEffectTests(unittest.TestCase):
    def setUp(self):
        import pygame
        self.V = pygame.Vector2
        self.db = ItemDatabase.from_file()

    def _player(self, *items):
        from game.entities.player import Player
        p = Player(self.db)
        for item_id in items:
            p.inv.add(self.db.items[item_id])
        p.recompute()
        return p

    def test_vest_absorbs_forty_percent_on_average_and_adds_hearts(self):
        p = self._player("kevlar_vest")
        self.assertEqual(p.max_hp, 12)
        p.hp = 1000
        for _ in range(100):
            p.iframes = 0
            self.assertTrue(p.hurt(1))
        self.assertIn(1000 - p.hp, (59, 60))
        plain = self._player()
        plain.hp = 1000
        plain.hurt(2)
        self.assertEqual(plain.hp, 998)

    def test_old_remote_makes_shots_homing_and_steers_towards_nearest_enemy(self):
        from game.systems import combat
        p = self._player("old_remote")
        self.assertTrue(all(s.homing for s in combat.build_player_shots(p, self.V(1, 0))))
        self.assertFalse(any(s.homing for s in combat.build_player_shots(self._player(), self.V(1, 0))))
        shot = combat.build_player_shots(p, self.V(1, 0))[0]
        shot.pos, shot.vel = self.V(100, 100), self.V(200, 0)
        near, far = SimpleNamespace(pos=self.V(200, 160)), SimpleNamespace(pos=self.V(100, 900))
        for _ in range(30):
            combat.steer_homing(shot, [far, near], 1 / 60)
        self.assertGreater(shot.vel.y, 20)
        self.assertAlmostEqual(shot.vel.length(), 200, places=3)
        calm = combat.build_player_shots(p, self.V(1, 0))[0]
        calm.vel = self.V(200, 0)
        combat.steer_homing(calm, [far], 1 / 60)
        self.assertEqual(calm.vel.y, 0)

    def test_thorn_cannon_and_fury_combo(self):
        from game.systems import combat
        plain = combat.thorn_shot(self._player("thorn_cannon"), self.V(0, 0), self.V(100, 0))[0]
        fury = combat.thorn_shot(self._player("thorn_cannon", "smg"), self.V(0, 0), self.V(100, 0))[0]
        self.assertEqual(plain.kind, "thorn")
        self.assertFalse(plain.expire_explode)
        self.assertTrue(fury.expire_explode)
        self.assertGreater(fury.vel.length(), plain.vel.length() * 1.5)

    def test_rooms_with_miniboss_spawn_it_alone(self):
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        from game.entities.enemy import load_enemy_defs
        from game.world.room import Room
        data = SimpleNamespace(items=self.db, enemies=load_enemy_defs(), events=load_events())
        for zid, expected in (("forest", "living_spruce"), ("city", "tank")):
            d = Dungeon(3, 8, self.db.regular_ids(), mini_kind="miniboss")
            pos = next(q for q, sp in d.specs.items() if sp.kind == "miniboss")
            room = Room(d.specs[pos], ZONES[zid], 3, data, [], zid + ":")
            self.assertFalse(room.cleared)
            room.enter(1.0)
            self.assertEqual([e.kind for e in room.enemies], [expected])
        house = Dungeon(4, 4, ["broom"], house=True, mini_kind="miniboss")
        pos = next(q for q, sp in house.specs.items() if sp.kind == "miniboss")
        room = Room(house.specs[pos], ZONES["house"], 4, data, [], "h:")
        room.enter(1.0)
        self.assertEqual([e.kind for e in room.enemies], ["landlord"])


class HeavenConfigTests(unittest.TestCase):
    def test_heaven_zone_and_side_zones(self):
        from game.world.zones import SIDE_ZONES
        z = ZONES["heaven"]
        self.assertTrue(z["always_day"] and z["sky"] and z["passive_enemies"])
        self.assertEqual((z["boss"], z["miniboss"], z["boss_cutscene"]), ("god", "gate_keeper", "god"))
        self.assertTrue(z["final_boss"])
        self.assertEqual((z["music_combat"], z["music_boss"]), ("heaven_combat", "god_boss"))
        self.assertEqual(ZONES["hell"]["ends_run"], "evil")   # портал после Беса — злая концовка
        self.assertEqual(set(SIDE_ZONES), {"hell", "heaven"})
        self.assertIn("god_slain", TESTIMONIES)

    @unittest.skipUnless(HAS_PYGAME, "pygame не установлен")
    def test_music_tracks_are_registered_with_requested_files(self):
        from game.systems.audio import MUSIC_TRACKS, MUSIC_FALLBACK
        self.assertEqual(MUSIC_TRACKS["miniboss"], "mini-bosses.mp3")
        self.assertEqual(MUSIC_TRACKS["heaven_combat"], "Heaven.mp3")
        self.assertEqual(MUSIC_TRACKS["god_boss"], "God.mp3")
        for key in ("miniboss", "heaven_combat", "god_boss"):
            self.assertIn(MUSIC_FALLBACK[key], MUSIC_TRACKS)   # без файла играет запасной трек

    def test_heaven_is_always_day(self):
        from game.daycycle import effective_state
        for clock in (0, 100, 250, 400, 470):
            st = effective_state(ZONES["heaven"], clock, 480.0, "night")
            self.assertTrue(st.has_sun, clock)
            self.assertEqual(st.darkness, 0.0)
        night = effective_state(ZONES["forest"], 0, 480.0, "night")   # у остальных улиц ночь остаётся ночью
        self.assertGreater(night.darkness, 0.3)

    @unittest.skipUnless(HAS_PYGAME, "pygame не установлен")
    def test_endings_texts(self):
        from game.states import ENDINGS
        evil = " ".join(t for t, _ in ENDINGS["evil"]["pages"])
        self.assertIn("ЭТО ЕЩЁ НЕ КОНЕЦ!", evil)
        self.assertEqual(evil.count("ЭТО ЕЩЁ НЕ КОНЕЦ!"), 5)
        self.assertIn("НЕТ!", evil)
        self.assertFalse(ENDINGS["evil"]["credits"])
        true = " ".join(t for t, _ in ENDINGS["true"]["pages"])
        self.assertIn("«Баланс»", true)
        self.assertIn("Ад и рай снова существуют", true)
        self.assertTrue(ENDINGS["true"]["credits"])

    def test_heaven_layout_has_gate_keeper_before_boss(self):
        from game.world.dungeon import miniboss_host
        for seed in range(100):
            d = Dungeon(f"sky{seed}", 8, ["broom"], mini_kind="miniboss")
            boss = next(r for r in d.specs.values() if r.kind == "boss")
            host = miniboss_host(d.specs, boss)
            if host is not None:
                self.assertEqual(host.kind, "miniboss")


class SoulCharacterTests(unittest.TestCase):
    def setUp(self):
        from game.systems.characters import load_characters
        self.db = ItemDatabase.from_file()
        self.chars = load_characters(self.db)
        self.soul = self.chars["soul"]

    def test_soul_stats_match_design(self):
        stats = self.db.stats(self.soul["start_items"], self.soul["mods"])
        self.assertEqual(stats["max_hp"], 1)                                   # полсердца
        self.assertEqual(stats["speed"], BASE_STATS["speed"] * 2)             # скорость в 2 раза выше обычной
        self.assertEqual(stats["damage"], 7.0)                                 # урон 7
        self.assertEqual(self.soul["start_items"], ["balancer", "scream"])

    def test_soul_unlocks_with_true_ending_only(self):
        from game.systems.characters import is_unlocked, progress
        self.assertFalse(is_unlocked(self.soul, {"endings": ["good", "secret", "evil"]}))
        self.assertTrue(is_unlocked(self.soul, {"endings": ["true"]}))
        self.assertEqual(progress(self.soul, {"endings": []}), (0, 1))
        self.assertEqual(progress(self.soul, {"endings": ["true"]}), (1, 1))

    def test_soul_items(self):
        balancer, scream = self.db.items["balancer"], self.db.items["scream"]
        self.assertIn("balancer", balancer.flags)
        self.assertEqual(scream.active["type"], "scream")
        self.assertGreater(scream.active["cooldown"], 0)
        self.assertTrue(balancer.drop_only and scream.drop_only)               # только у Души

    def test_bad_unlock_condition_is_rejected(self):
        from game.systems.characters import load_characters
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "chars.json"
            data = json.loads((Path(__file__).resolve().parent.parent / "data" / "characters.json").read_text(encoding="utf-8"))
            data["characters"][-1]["unlock"] = {"nothing": 1}
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_characters(self.db, path)


class GeyserTests(unittest.TestCase):
    def test_charge_needs_three_seconds_and_resets_on_early_release(self):
        from game.systems.geyser import Charge
        c = Charge()
        for _ in range(29):
            c.hold(0.1)
        self.assertFalse(c.release())          # 2.9 с — мало
        for _ in range(31):
            c.hold(0.1)
        self.assertTrue(c.ready)
        self.assertTrue(c.release())
        self.assertEqual(c.value, 0.0)

    def test_range_is_25_blocks_and_scream_is_four_times_wider(self):
        from game.systems.geyser import Geyser, RANGE
        bal, scr = Geyser.balancer(), Geyser.scream()
        self.assertEqual(RANGE, 25 * 16)
        self.assertEqual(scr.width, bal.width * 4)
        self.assertGreater(scr.duration, bal.duration)
        self.assertGreater(scr.damage_mult, bal.damage_mult)
        self.assertGreater(scr.recoil, 0)
        self.assertEqual(bal.recoil, 0)

    def test_geyser_follows_cursor_and_hits_along_beam_only(self):
        from game.systems.geyser import Geyser
        g = Geyser.balancer()
        g.start((0, 0), (1, 0))
        self.assertTrue(g.hits((300, 3), 2))
        self.assertFalse(g.hits((300, 40), 2))             # в стороне от луча
        self.assertFalse(g.hits((500, 0), 2))              # дальше 25 блоков
        self.assertFalse(g.hits((-30, 0), 2))              # позади игрока
        for _ in range(30):                                # курсор ушёл вверх — луч поворачивается за ним
            g.update(1 / 60, (0, 0), (0, -1))
        self.assertLess(g.direction[1], -0.3)
        for _ in range(240):
            g.update(1 / 60, (0, 0), (0, -1))
            if not g.active:
                break
        self.assertFalse(g.active)

    def test_ticks_and_recoil(self):
        from game.systems.geyser import Geyser
        g = Geyser.scream()
        g.start((0, 0), (1, 0))
        ticks = sum(g.update(1 / 60, (0, 0), (1, 0)) for _ in range(60))
        self.assertTrue(9 <= ticks <= 11)                  # урон раз в 0.1 с
        rx, ry = g.recoil_vector()
        self.assertLess(rx, 0)                             # отдача — против направления луча
        self.assertEqual(Geyser.balancer().recoil_vector(), (0.0, 0.0))


@unittest.skipUnless(HAS_PYGAME, "pygame не установлен")
class HeavenBossTests(unittest.TestCase):
    FakeRoom = MiniBossBehaviorTests.FakeRoom

    def setUp(self):
        import pygame
        random.seed(11)
        self.V = pygame.Vector2
        self.room = self.FakeRoom()
        self.room.zone = ZONES["heaven"]
        self.room.request_spawn = lambda kind, n: self.room.spawn_requests.append((kind, n))
        self.player = SimpleNamespace(pos=self.V(380, 200))
        self.shots, self.t = [], 0.0

    def shoot(self, pos, direction, speed, dmg, radius=3, color=(0, 0, 0), kind="shot"):
        self.shots.append((self.t, dmg, self.V(pos), self.V(direction) * speed))

    def simulate(self, boss, seconds, dt=1 / 60):
        self.t = 0.0
        self.room.enemies = [boss]
        while self.t < seconds:
            boss.update(dt, self.room, self.player, self.shoot)
            for h in self.room.hazards:
                h.update(dt)
            self.t += dt

    def test_gate_keeper_heals_only_when_player_is_far(self):
        from game.entities.miniboss import create_miniboss, LEASH
        boss = create_miniboss("gate_keeper", self.V(240, 90))
        boss.spawn_t = 0
        boss.hp = boss.max_hp * 0.6
        self.player.pos = boss.pos + self.V(LEASH * 0.5, 0)       # рядом — не лечится
        before = boss.hp
        self.simulate(boss, 3)
        self.assertLessEqual(boss.hp, before)
        self.player.pos = self.V(440, 215)                        # далеко — лечится
        boss.pos = self.V(40, 50)
        boss.state, boss.timer = "walk", 99
        low = boss.hp
        self.simulate(boss, 4)
        self.assertGreater(boss.hp, low)
        self.assertTrue(any("восстанавливает" in n[0] for n in self.room.notices))

    def test_gate_keeper_summons_zone_enemies_and_uses_scales(self):
        from game.entities.miniboss import create_miniboss
        boss = create_miniboss("gate_keeper", self.V(240, 90))
        boss.spawn_t = 0
        self.player.pos = boss.pos + self.V(60, 0)
        self.simulate(boss, 30)
        kinds = {k for k, _ in self.room.spawn_requests}
        self.assertTrue(kinds)
        self.assertTrue(kinds <= {k for k, _ in ZONES["heaven"]["enemy_pool"]})
        self.assertTrue(any(h.kind == "blast" for h in self.room.hazards) or self.room.hazards == [])

    def test_god_has_ten_thousand_hp_and_hits_for_250(self):
        from game.entities.boss import create_boss
        god = create_boss("god", self.V(240, 90))
        self.assertEqual(god.max_hp, 10000)
        self.assertTrue(god.is_boss)
        self.assertEqual(god.contact, 250)
        god.spawn_t = 0
        self.simulate(god, 25)
        self.assertGreater(len(self.shots), 20)
        self.assertTrue(all(s[1] == 250 for s in self.shots))
        god.take_damage(100, self.V(1, 0), 500)
        self.assertEqual(god.knock.length(), 0)                    # Бога не отбросить
        self.assertEqual(god.hp, 9900)

    def test_god_phases_at_66_and_33_percent(self):
        from game.entities.boss import create_boss
        god = create_boss("god", self.V(240, 90))
        god.spawn_t = 0
        self.assertEqual(god._phase_for_hp(), 1)
        god.hp = 6500
        self.assertEqual(god._phase_for_hp(), 2)
        god.hp = 3200
        self.assertEqual(god._phase_for_hp(), 3)
        self.simulate(god, 40)
        self.assertEqual(god.phase, 3)
        self.assertTrue(any(h.damage == 250 for h in self.room.hazards) or self.shots)

    def test_god_uses_every_attack_eventually(self):
        from game.entities.boss import create_boss
        from game.entities.god import PHASE_ATTACKS
        god = create_boss("god", self.V(240, 90))
        god.spawn_t, god.hp = 0, 3000
        seen = set()
        self.t = 0.0
        self.room.enemies = [god]
        for _ in range(60 * 240):
            god.update(1 / 60, self.room, self.player, self.shoot)
            if god.state.startswith("wind_"):
                seen.add(god.state)
            for h in self.room.hazards:
                h.update(1 / 60)
            self.room.hazards = [h for h in self.room.hazards if not h.dead]
            self.t += 1 / 60
        state_of = {"gap_ring": "wind_gap"}
        self.assertEqual(seen, {state_of.get(a, "wind_" + a) for a in PHASE_ATTACKS[3]})


@unittest.skipUnless(HAS_PYGAME, "pygame не установлен")
class ShineFormTests(unittest.TestCase):
    def setUp(self):
        self.db = ItemDatabase.from_file()

    def test_player_becomes_shine_with_1000_hp_and_100_damage(self):
        from game.entities.player import Player
        p = Player(self.db)
        self.assertEqual((p.max_hp, p.stats["damage"]), (6, 3.0))
        p.set_form("shine")
        self.assertEqual((p.max_hp, p.hp, p.stats["damage"]), (1000, 1000, 100.0))
        p.iframes = 0
        self.assertTrue(p.hurt(250))                               # удар Бога
        self.assertEqual(p.hp, 750)
        p.set_form(None)
        self.assertEqual((p.max_hp, p.stats["damage"]), (6, 3.0))

    def test_soul_player_has_half_heart_and_double_speed(self):
        from game.entities.player import Player
        from game.systems.characters import load_characters
        chars = load_characters(self.db)
        p = Player(self.db, chars["soul"])
        p.inv.add(self.db.items["balancer"])
        p.recompute()
        self.assertEqual((p.max_hp, p.hp), (1, 1))
        self.assertEqual(p.stats["speed"], BASE_STATS["speed"] * 2)
        self.assertEqual(p.stats["damage"], 7.0)
        self.assertIn("balancer", p.flags)
        p.iframes = 0
        self.assertTrue(p.hurt(1))
        self.assertLessEqual(p.hp, 0)                              # любой удар смертелен


@unittest.skipUnless(HAS_PYGAME, "pygame не установлен")
class DormantEnemiesTests(unittest.TestCase):
    def test_dormant_enemy_does_nothing_until_touched(self):
        import pygame
        from game.entities.enemy import Enemy, load_enemy_defs
        data = load_enemy_defs()
        for kind in ("cherub", "cloudling", "halo_ring", "dove", "trumpeter", "stone_angel"):
            self.assertIn(kind, data)
            e = Enemy(kind, pygame.Vector2(200, 100), data[kind])
            e.spawn_t = 0
            start = e.pos.copy()
            for _ in range(120):
                e.idle(1 / 60)
            self.assertEqual(e.pos, start)
            self.assertFalse(e.provoked)
            e.take_damage(1, pygame.Vector2(1, 0), 0)
            self.assertTrue(e.provoked)

    def test_sky_combat_room_is_dormant_until_aggro(self):
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        from game.entities.enemy import load_enemy_defs
        from game.world.room import Room
        db = ItemDatabase.from_file()
        data = SimpleNamespace(items=db, enemies=load_enemy_defs(), events=load_events())
        d = Dungeon(5, 8, db.regular_ids(), mini_kind="miniboss")
        pos = next(q for q, sp in d.specs.items() if sp.kind == "combat")
        room = Room(d.specs[pos], ZONES["heaven"], 5, data, [], "heaven:")
        self.assertTrue(room.passive)
        room.enter(1.0)
        self.assertTrue(room.dormant)
        room.aggro = True
        self.assertFalse(room.dormant)
        forest = Room(d.specs[pos], ZONES["forest"], 5, data, [], "forest:")
        forest.enter(1.0)
        self.assertFalse(forest.dormant)                           # в других зонах враги нападают сразу

    def test_sky_background_builds_with_gold_doors(self):
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        from game.entities.enemy import load_enemy_defs
        from game.world.room import Room
        db = ItemDatabase.from_file()
        data = SimpleNamespace(items=db, enemies=load_enemy_defs(), events=load_events())
        d = Dungeon(6, 8, db.regular_ids(), mini_kind="miniboss")
        room = Room(d.specs[(0, 0)], ZONES["heaven"], 6, data, [], "heaven:")
        self.assertIsNotNone(room._build_bg())


if __name__ == "__main__":
    unittest.main()
