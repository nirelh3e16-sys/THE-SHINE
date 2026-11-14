"""HUD: здоровье, монеты, предметы, миникарта, босс, уведомления.

Элементы закреплены за углами экрана; правило финального босса может повернуть раскладку
(play.hud_layout сдвигает каждый элемент на другой угол).
Углы: 0 — правый нижний, 1 — левый верхний, 2 — левый нижний, 3 — правый верхний.
"""
import pygame

from .text import draw_text
from ..settings import GAME_W, GAME_H

KIND_COLORS = {"start": (200, 200, 200), "combat": (110, 110, 130), "treasure": (255, 215, 70),
               "shop": (90, 200, 255), "event": (200, 120, 255), "boss": (230, 60, 70),
               "house": (255, 170, 90), "miniboss": (240, 140, 60), "unknown": (60, 55, 75)}

# базовые углы элементов: здоровье+монеты, активный предмет, ряд предметов, миникарта
BASE_CORNER = {"vitals": 0, "active": 1, "items": 2, "map": 3}


def corner_of(element, layout):
    return (BASE_CORNER[element] + layout) % 4


def _is_right(corner):
    return corner in (0, 3)


def _is_bottom(corner):
    return corner in (0, 2)


class Notifications:
    def __init__(self):
        self.items = []  # [text, color, time]

    def push(self, text, color="white", t=3.0):
        self.items.append([text, color, t])
        self.items = self.items[-4:]

    def update(self, dt):
        for n in self.items:
            n[2] -= dt
        self.items = [n for n in self.items if n[2] > 0]

    def draw(self, surf):
        y = GAME_H - 46
        for text, color, t in reversed(self.items):
            draw_text(surf, text, (GAME_W // 2, y), color, 11, "midbottom")
            y -= 12


def draw_hud(surf, play, sprites):
    p = play.player
    layout = play.hud_layout
    glitch = play.ui_glitch()  # фаза 3 Хаоса: часть интерфейса пропадает (здоровье и активный предмет остаются)
    _draw_vitals(surf, p, sprites, corner_of("vitals", layout), show_coins=not glitch)
    if not glitch:
        draw_text(surf, play.zone["name"], (GAME_W // 2, 4), "white", 11, "midtop")
    label = play.room.modifier_label()
    if label:
        blink = int(pygame.time.get_ticks() / 150) % 2 or play.room.reshuffle_t is None
        draw_text(surf, label, (GAME_W // 2, 17), "gold" if blink else "red", 10, "midtop")
    if play.inverted_t > 0:
        draw_text(surf, f"УПРАВЛЕНИЕ ИНВЕРТИРОВАНО {play.inverted_t:.0f}", (GAME_W // 2, 29), "red", 10, "midtop")
    if not glitch:
        _draw_items(surf, p, sprites, corner_of("items", layout))
    _draw_active(surf, play, sprites, corner_of("active", layout))
    if not glitch:
        draw_minimap(surf, play, corner_of("map", layout))
    boss = play.boss() or play.miniboss()   # у мини-босса такая же полоска здоровья
    if boss is not None and boss.spawn_t <= 0:
        w = 220
        x, y = (GAME_W - w) // 2, 244
        if glitch:
            x += int(pygame.time.get_ticks() / 70) % 5 - 2
        pygame.draw.rect(surf, (26, 13, 18), (x - 2, y - 2, w + 4, 11))
        pygame.draw.rect(surf, (74, 22, 34), (x, y, w, 7))
        fill_w = int(w * max(0, boss.hp) / boss.max_hp)
        pygame.draw.rect(surf, (214, 50, 70), (x, y, fill_w, 7))
        if fill_w > 2:
            pygame.draw.rect(surf, (255, 128, 140), (x, y, fill_w, 2))
            pygame.draw.rect(surf, (140, 28, 48), (x, y + 6, fill_w, 1))
        draw_text(surf, boss.name.upper(), (GAME_W // 2, y - 1), "white", 9, "midbottom")
    play.notes.draw(surf)


def _draw_vitals(surf, p, sprites, corner, show_coins):
    big = p.max_hp > 40   # Шайн (1000 здоровья): сердец не нарисовать — вместо них полоска
    hearts = 0 if big else (p.max_hp + 1) // 2
    per_row = 8
    rows = 1 if big else (hearts + per_row - 1) // per_row
    right, bottom = _is_right(corner), _is_bottom(corner)
    if big:
        w = 84
        x = GAME_W - 6 - w if right else 6
        y = (GAME_H - 14) if bottom else 4
        pygame.draw.rect(surf, (26, 13, 18), (x - 2, y - 2, w + 4, 12))
        pygame.draw.rect(surf, (60, 24, 76), (x, y, w, 8))
        pygame.draw.rect(surf, (200, 70, 230), (x, y, int(w * max(0, p.hp) / p.max_hp), 8))
        pygame.draw.rect(surf, (236, 160, 255), (x, y, int(w * max(0, p.hp) / p.max_hp), 2))
        draw_text(surf, f"ШАЙН {max(0, p.hp)}/{p.max_hp}", (x + w // 2, y - 1), "white", 8, "midtop")
    for i in range(hearts):
        hp_here = p.hp - i * 2
        name = "heart_full" if hp_here >= 2 else "heart_half" if hp_here == 1 else "heart_empty"
        row, col = divmod(i, per_row)
        in_row = min(per_row, hearts - row * per_row)
        x = GAME_W - 6 - (in_row - col) * 10 + 1 if right else 6 + col * 10
        y = (GAME_H - 14 - (rows - 1 - row) * 10) if bottom else 4 + row * 10
        surf.blit(sprites.get(name), (x, y))
    if not show_coins:
        return
    coin_y = (GAME_H - 14 - rows * 10 - 2) if bottom else 4 + rows * 10 + 2
    if right:
        coins = draw_text(surf, str(p.coins), (GAME_W - 6, coin_y), "gold", 10, "topright")
        surf.blit(sprites.get("coin"), (coins.left - 10, coin_y + 3))
    else:
        surf.blit(sprites.get("coin"), (6, coin_y + 3))
        draw_text(surf, str(p.coins), (16, coin_y), "gold", 10, "topleft")


def _draw_items(surf, p, sprites, corner):
    ids = p.inv.items[-10:]
    y = GAME_H - 28 if _is_bottom(corner) else 6
    for i, item_id in enumerate(ids):
        x = GAME_W - 6 - (len(ids) - i) * 14 if _is_right(corner) else 6 + i * 14
        surf.blit(sprites.icon(item_id), (x, y))


def _draw_active(surf, play, sprites, corner):
    p = play.player
    x = GAME_W - 28 if _is_right(corner) else 6
    y = GAME_H - 28 if _is_bottom(corner) else 6
    box = pygame.Rect(x, y, 22, 22)
    pygame.draw.rect(surf, (26, 13, 18), box.inflate(2, 2))
    pygame.draw.rect(surf, (56, 38, 62), box)
    pygame.draw.rect(surf, (150, 120, 170), box, 1)
    pygame.draw.line(surf, (200, 180, 220), (box.x + 1, box.y + 1), (box.right - 2, box.y + 1))
    if not p.inv.active_id:
        return
    surf.blit(sprites.icon(p.inv.active_id), (box.x + 4, box.y + 4))
    if p.inv.kills_left > 0:   # предмет заряжается убийствами (Аптечка): показываем, сколько осталось
        veil = pygame.Surface((22, 22), pygame.SRCALPHA)
        veil.fill((0, 0, 0, 150))
        surf.blit(veil, box.topleft)
        draw_text(surf, str(p.inv.kills_left), box.center, "gold", 12, "center")
    elif p.inv.active_cd > 0:
        h = int(22 * min(1, p.inv.active_cd / play.active_cooldown))
        veil = pygame.Surface((22, h), pygame.SRCALPHA)
        veil.fill((0, 0, 0, 150))
        surf.blit(veil, box.topleft)
    else:
        pos = (box.centerx, box.top - 1) if _is_bottom(corner) else (box.centerx, box.bottom + 1)
        draw_text(surf, "Q", pos, "green", 9, "midbottom" if _is_bottom(corner) else "midtop")


def draw_minimap(surf, play, corner=3):
    d = play.dungeon
    compass = "compass" in play.player.flags
    ox = GAME_W - 40 if _is_right(corner) else 40
    oy = GAME_H - 44 if _is_bottom(corner) else 24
    known = d.known_rooms()
    show = set(known)
    if compass:
        show |= {pos for pos, s in d.specs.items() if s.kind in ("treasure", "shop", "boss", "event", "house", "miniboss")}
        if d.false_mark:
            show.add(d.false_mark)
    for pos in show:
        kind = d.map_kind(pos, compass)
        r = pygame.Rect(ox + pos[0] * 8, oy + pos[1] * 6, 7, 5)
        pygame.draw.rect(surf, KIND_COLORS.get(kind, KIND_COLORS["unknown"]), r)
        if pos == d.pos:
            pygame.draw.rect(surf, (255, 255, 255), r.inflate(2, 2), 1)
