"""Бестиарий: раздел главного меню со всеми боссами, мини-боссами, мобами и предметами.

Запись открывается победой (для мобов, боссов и мини-боссов) или находкой предмета. Закрытые записи показывают
тёмный силуэт и «???». Логика сборки записей (build_entries) не требует окна; BestiaryState — экран меню.
"""
import pygame

from .entities.miniboss import MINIBOSSES, create_miniboss
from .settings import GAME_W, GAME_H
from .systems.morality import TESTIMONIES
from .ui.text import draw_text, wrap
from .world.zones import ZONES, ZONE_ORDER

BOSS_PREFIX = "boss:"   # победы над боссами хранятся как «boss:<id>» (у моба и босса может быть один id, например Сосед)
BOSS_SPRITES = {"lumberjack": "lumberjack", "neighbor": "neighbor_boss", "mayor": "mayor", "chaos": "chaos",
                "shine": "shine", "imp": "imp", "god": "god"}
BEHAVIORS = {"chase": "Преследует тебя", "burst": "Стреляет очередями", "spin": "Вертится и стреляет кольцом",
             "dive": "Пикирует на тебя", "shoot": "Стреляет во врага залпами", "blink": "Появляется и исчезает"}
MINIBOSS_LORE = {
    "living_spruce": "Ёлка, в которой слишком долго жил лесной дух. Её иголки остаются в теле и колют при каждом шаге.",
    "landlord": "Он требует плату за жильё, которого никто не снимал. Собаки у него на довольствии, телевизор — на связи.",
    "tank": "Забытый городской танк. Едет в твою сторону уже много лет и не собирается сворачивать.",
    "gate_keeper": "Каменный ангел с весами у небесных врат. Пока ты далеко, он залечивает любые раны.",
}
CATEGORIES = ("Боссы", "Мини-боссы", "Мобы", "Предметы")


def found_kinds(save_data):
    """Что игрок уже победил: список defeated плюс боссы из старых сохранений (по счётчику boss_kills)."""
    found = set(save_data.get("defeated", []))
    for boss_id, count in save_data.get("boss_kills", {}).items():
        if count > 0:
            found.add(BOSS_PREFIX + boss_id)
    return found


def _zone_of_enemy(kind):
    for zid in ZONE_ORDER:
        if any(k == kind for k, _ in ZONES[zid].get("enemy_pool", ())):
            return ZONES[zid]["name"]
    return "—"


def _boss_stats(kind, hp, contact):
    return [("Здоровье", f"{int(hp)}"), ("Урон при касании", f"{contact}")]


def build_entries(items_db, enemy_defs, save_data, boss_factory=None):
    """Список (название категории, [записи]). Запись: id, name, sprite/icon, found, zone, stats, desc."""
    from .entities.boss import create_boss
    boss_factory = boss_factory or (lambda kind: create_boss(kind, pygame.Vector2(0, 0)))
    found = found_kinds(save_data)
    seen_items = set(save_data.get("seen_items", []))
    bosses, minis, mobs, items = [], [], [], []
    for zid in ZONE_ORDER:
        zone = ZONES[zid]
        kind = zone.get("boss")
        if kind:
            boss = boss_factory(kind)
            lore = TESTIMONIES.get(zone.get("boss_testimony"), ("", ""))[1]
            bosses.append({"id": BOSS_PREFIX + kind, "name": boss.name, "sprite": BOSS_SPRITES[kind], "icon": None,
                           "found": (BOSS_PREFIX + kind) in found, "zone": zone["name"],
                           "stats": _boss_stats(kind, boss.max_hp, boss.contact), "desc": lore})
    mini_zone = {}
    for zid in ZONE_ORDER:
        for key in ("miniboss", "house_miniboss"):
            if ZONES[zid].get(key):
                mini_zone.setdefault(ZONES[zid][key], ZONES[zid]["name"])
    for kind in MINIBOSSES:
        mb = create_miniboss(kind, pygame.Vector2(0, 0))
        drop = MINIBOSSES[kind].drop_item
        stats = _boss_stats(kind, mb.max_hp, mb.contact)
        if drop and drop in items_db.items:
            stats.append(("Награда", items_db.items[drop].name))
        minis.append({"id": kind, "name": mb.name, "sprite": mb.sprite, "icon": None, "found": kind in found,
                      "zone": mini_zone.get(kind, "—"), "stats": stats, "desc": MINIBOSS_LORE.get(kind, "")})
    for kind, data in enemy_defs.items():
        stats = [("Здоровье", f"{data['hp']}"), ("Урон при касании", f"{data['contact']}")]
        mobs.append({"id": kind, "name": data["name"], "sprite": data["sprite"], "icon": None, "found": kind in found,
                     "zone": _zone_of_enemy(kind), "stats": stats, "desc": BEHAVIORS.get(data["behavior"], "")})
    names = {i: d.name for i, d in items_db.items.items()}
    for item_id, item in items_db.items.items():
        got = item_id in seen_items
        desc = item.desc
        combos = []
        for c in items_db.combos:
            if item_id in c["needs"]:
                partner = next(n for n in c["needs"] if n != item_id)
                combos.append(f"{item.name} + {names[partner] if partner in seen_items else '???'}")
        if got and combos:
            desc += "  Комбо: " + "; ".join(combos)
        items.append({"id": item_id, "name": item.name, "sprite": None, "icon": item_id, "found": got, "zone": "",
                      "stats": [], "desc": desc})
    return list(zip(CATEGORIES, (bosses, minis, mobs, items)))


def totals(categories):
    """(открыто, всего) по всему бестиарию."""
    entries = [e for _, group in categories for e in group]
    return sum(1 for e in entries if e["found"]), len(entries)


class BestiaryState:
    """Экран бестиария. ←/→ (A/D) — вкладка, ↑/↓ (W/S) — запись, колесо мыши и клики работают, Esc — назад."""
    ROW_H, ROWS, LIST_X, LIST_Y = 17, 12, 8, 54

    def __init__(self, game):
        self.game = game
        self.categories = build_entries(game.data.items, game.data.enemies, game.save.data)
        self.tab, self.sel, self.scroll = 0, [0] * len(self.categories), [0] * len(self.categories)
        self._img_cache = {}

    @property
    def entries(self):
        return self.categories[self.tab][1]

    def _move(self, d):
        n = len(self.entries)
        if n:
            self.sel[self.tab] = (self.sel[self.tab] + d) % n
            self._keep_visible()

    def _keep_visible(self):
        s = self.sel[self.tab]
        if s < self.scroll[self.tab]:
            self.scroll[self.tab] = s
        elif s >= self.scroll[self.tab] + self.ROWS:
            self.scroll[self.tab] = s - self.ROWS + 1

    def _switch(self, d):
        self.tab = (self.tab + d) % len(self.categories)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                self.game.go_menu()
            elif event.key in (pygame.K_LEFT, pygame.K_a):
                self._switch(-1)
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                self._switch(1)
            elif event.key in (pygame.K_UP, pygame.K_w):
                self._move(-1)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self._move(1)
        elif event.type == pygame.MOUSEWHEEL:
            self._move(-event.y)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = getattr(event, "pos_game", pygame.Vector2(event.pos))
            for i in range(len(self.categories)):
                if self._tab_rect(i).collidepoint(pos.x, pos.y):
                    self.tab = i
                    return
            row = int((pos.y - self.LIST_Y) // self.ROW_H)
            if self.LIST_X <= pos.x <= 178 and 0 <= row < self.ROWS:
                idx = self.scroll[self.tab] + row
                if idx < len(self.entries):
                    self.sel[self.tab] = idx

    def update(self, dt):
        pass

    def _tab_rect(self, i):
        w = (GAME_W - 16) // len(self.categories)
        return pygame.Rect(8 + i * w, 22, w - 3, 18)

    def _picture(self, entry, box):
        """Картинка записи, подогнанная под квадрат box; у закрытой записи — тёмный силуэт."""
        key = (entry["id"], entry["found"], box)
        img = self._img_cache.get(key)
        if img is None:
            sprites = self.game.sprites
            src = sprites.icon(entry["icon"]) if entry["icon"] else sprites.get(entry["sprite"])
            k = min(box / src.get_width(), box / src.get_height())
            k = int(k) if k >= 1 else k
            size = (max(1, int(src.get_width() * k)), max(1, int(src.get_height() * k)))
            img = pygame.transform.scale(src, size)
            if not entry["found"]:
                img = img.copy()
                img.fill((46, 38, 70, 255), special_flags=pygame.BLEND_RGBA_MIN)
            self._img_cache[key] = img
        return img

    def draw(self, surf):
        surf.fill((18, 12, 32))
        done, total = totals(self.categories)
        draw_text(surf, "БЕСТИАРИЙ", (8, 5), "gold", 14)
        draw_text(surf, f"Открыто: {done}/{total}", (GAME_W - 8, 7), "grey", 10, "topright")
        for i, (name, group) in enumerate(self.categories):
            r = self._tab_rect(i)
            sel = i == self.tab
            pygame.draw.rect(surf, (60, 44, 96) if sel else (30, 22, 50), r)
            pygame.draw.rect(surf, (255, 215, 90) if sel else (70, 56, 100), r, 1)
            draw_text(surf, f"{name} {sum(1 for e in group if e['found'])}/{len(group)}", r.center,
                      "gold" if sel else "grey", 9, "center")
        group = self.entries
        pygame.draw.rect(surf, (26, 18, 44), (self.LIST_X - 2, self.LIST_Y - 3, 176, self.ROWS * self.ROW_H + 4))
        top = self.scroll[self.tab]
        for row, entry in enumerate(group[top:top + self.ROWS]):
            idx = top + row
            y = self.LIST_Y + row * self.ROW_H
            sel = idx == self.sel[self.tab]
            if sel:
                pygame.draw.rect(surf, (72, 54, 116), (self.LIST_X - 1, y - 1, 174, self.ROW_H - 1))
            icon = self._picture(entry, 14)
            surf.blit(icon, icon.get_rect(center=(self.LIST_X + 9, y + 7)))
            draw_text(surf, entry["name"] if entry["found"] else "???", (self.LIST_X + 22, y + 1),
                      "white" if entry["found"] else "grey", 10)
        if len(group) > self.ROWS:   # полоса прокрутки
            h = self.ROWS * self.ROW_H
            bar = max(10, int(h * self.ROWS / len(group)))
            y = self.LIST_Y + int((h - bar) * top / max(1, len(group) - self.ROWS))
            pygame.draw.rect(surf, (90, 74, 130), (self.LIST_X + 171, y, 3, bar))
        if group:
            self._draw_detail(surf, group[self.sel[self.tab]])
        draw_text(surf, "←/→ вкладка   ↑/↓ запись   Esc назад", (GAME_W // 2, GAME_H - 5), "grey", 9, "midbottom")

    def _draw_detail(self, surf, entry):
        x0, y0, w = 192, 46, GAME_W - 200
        pygame.draw.rect(surf, (26, 18, 44), (x0 - 4, y0 - 4, w + 8, GAME_H - 70))
        pygame.draw.rect(surf, (70, 56, 100), (x0 - 4, y0 - 4, w + 8, GAME_H - 70), 1)
        box = pygame.Rect(x0, y0, 92, 84)
        pygame.draw.rect(surf, (14, 10, 26), box)
        img = self._picture(entry, 80)
        surf.blit(img, img.get_rect(center=box.center))
        if not entry["found"]:
            draw_text(surf, "???", (x0 + 100, y0 + 2), "grey", 16)
            hint = "Предмет ещё не найден. Найди его, чтобы открыть запись." if entry["icon"] else \
                   "Ты ещё не побеждал это существо. Победи его, чтобы открыть запись."
            for i, line in enumerate(wrap(hint, w - 104, 10)):
                draw_text(surf, line, (x0 + 100, y0 + 26 + i * 12), "grey", 10)
            return
        draw_text(surf, entry["name"], (x0 + 100, y0 + 2), "gold", 14)
        y = y0 + 22
        if entry["zone"]:
            draw_text(surf, f"Локация: {entry['zone']}", (x0 + 100, y), "blue", 10)
            y += 14
        for label, value in entry["stats"]:
            draw_text(surf, f"{label}: {value}", (x0 + 100, y), "white", 10)
            y += 13
        y = max(y + 4, y0 + 92)
        for line in wrap(entry["desc"], w, 10)[:9]:
            draw_text(surf, line, (x0, y), "white", 10)
            y += 12
