"""Состояния вне забега: меню, настройки, вступление, смерть, победа."""
import math
import random

import pygame

from .ui.menus import Menu
from .settings import PUBLISHER
from .systems.characters import progress as char_progress
from .world.zones import ZONES
from .ui.text import draw_text, wrap
from .settings import GAME_W, GAME_H

INTRO_LINES = (
    ("THE SHINE", "Ты не подходишь ни для рая, ни для ада."),
    ("THE SHINE", "Слишком плох для одного и слишком мелок для другого. Какая досада."),
    ("THE SHINE", "В центре города сидит Хаос. Забери его — и, возможно, я открою тебе врата рая."),
    ("THE SHINE", "Возможно."),
    ("THE SHINE", "Не опаздывай."),
)


def draw_shine(surf, cx, cy, t):
    """THE SHINE в сцене: огромный летающий глаз с крыльями, множеством глаз на них и нимбом."""
    for i in range(6):
        for side in (-1, 1):
            flap = math.sin(t * 1.6 + i * 0.5) * 5
            ang = math.radians(-50 + i * 18 + flap * side)
            length = 130 - i * 8
            tip = (cx + side * math.cos(ang) * length, cy + math.sin(ang) * length * 0.7)
            root = (cx + side * 22, cy)
            mid = ((root[0] + tip[0]) / 2, (root[1] + tip[1]) / 2 - 10)
            pts = [root, mid, tip, (mid[0], mid[1] + 20)]
            pygame.draw.polygon(surf, (255, 248, 225 - i * 12), pts)
            pygame.draw.polygon(surf, (150, 100, 40), pts, 1)
            pygame.draw.circle(surf, (255, 255, 255), (int(mid[0]), int(mid[1] + 5)), 4)       # мелкие глаза на крыльях
            pygame.draw.circle(surf, (210, 30, 70), (int(mid[0] + math.sin(t + i)), int(mid[1] + 5)), 2)
    pygame.draw.circle(surf, (255, 255, 255), (cx, cy), 36)
    pygame.draw.circle(surf, (150, 100, 40), (cx, cy), 36, 3)
    look = pygame.Vector2(math.sin(t * 0.8), math.cos(t * 0.6)) * 6
    pygame.draw.circle(surf, (80, 150, 255), (int(cx + look.x), int(cy + look.y)), 20)
    pygame.draw.circle(surf, (20, 10, 30), (int(cx + look.x * 1.4), int(cy + look.y * 1.4)), 10)
    pygame.draw.circle(surf, (255, 255, 255), (int(cx + look.x * 1.4) - 4, int(cy + look.y * 1.4) - 4), 3)
    pygame.draw.ellipse(surf, (255, 215, 90), (cx - 44, cy - 66 + math.sin(t * 2) * 3, 88, 22), 4)   # нимб


ENEMY_SPRITE_OF_BOSS = {"lumberjack": "lumberjack", "neighbor": "neighbor_boss", "mayor": "mayor",
                        "chaos": "chaos", "shine": "shine"}


class MenuState:
    """Главное меню: название и кнопки в правом нижнем углу, фон — случайная локация."""

    def __init__(self, game):
        self.game = game
        self.t = 0.0
        self.backdrop = self._make_backdrop()
        self._build()

    def _make_backdrop(self):
        from .world.dungeon import RoomSpec
        from .world.room import Room
        from .world.zones import ZONES
        rng = random.Random()
        zone_id = rng.choice(("forest", "suburbs", "city", "center", "shine"))
        zone = ZONES[zone_id]
        spec = RoomSpec((0, 0), "start", {"N": (0, -1), "S": (0, 1), "E": (1, 0), "W": (-1, 0)}, 0)
        room = Room(spec, zone, rng.random(), self.game.data, [], "menu:")
        if zone_id == "shine" and rng.random() < 0.5:
            room.set_theme(zone["judgment_theme"])
        surf = pygame.Surface((GAME_W, GAME_H))
        off = pygame.Vector2()
        room.draw_floor(surf, off)
        room.draw_obstacles(surf, off, self.game.sprites)
        sprites = self.game.sprites
        # декорации: пара обитателей локации, её босс и сам герой
        for kind in [rng.choice([k for k, _ in zone["enemy_pool"]]) for _ in range(3)] if zone["enemy_pool"] else []:
            img = sprites.get(self.game.data.enemies[kind]["sprite"], rng.random() < 0.5)
            surf.blit(img, img.get_rect(center=(rng.randint(60, 300), rng.randint(70, 220))))
        boss = sprites.get(ENEMY_SPRITE_OF_BOSS[zone["boss"]])
        surf.blit(boss, boss.get_rect(center=(130, 150)))
        hero = sprites.get("player")
        surf.blit(hero, hero.get_rect(midbottom=(70, 200)))
        # затемнение к правому нижнему углу, чтобы читались название и кнопки
        shade = pygame.Surface((GAME_W, GAME_H), pygame.SRCALPHA)
        for x in range(0, GAME_W, 4):
            alpha = int(max(0, (x - 140) / (GAME_W - 140)) ** 1.4 * 210)
            pygame.draw.rect(shade, (12, 6, 26, alpha), (x, 0, 4, GAME_H))
        for y in range(0, GAME_H, 4):
            alpha = int(max(0, (y - 90) / (GAME_H - 90)) * 120)
            pygame.draw.rect(shade, (12, 6, 26, alpha), (0, y, GAME_W, 4), 0)
        surf.blit(shade, (0, 0))
        return surf

    def _build(self):
        entries = []
        if self.game.save.data.get("current_run"):
            entries.append(("Продолжить", self.game.continue_run))
        entries += [("Новая игра", self.game.new_game), ("Настройки", self.game.go_settings), ("Выход", self.game.quit)]
        self.menu = Menu("THE SHINE", entries, corner=True)

    def handle_event(self, event):
        self.menu.handle_event(event)

    def update(self, dt):
        self.t += dt

    def draw(self, surf):
        surf.blit(self.backdrop, (0, 0))
        self.menu.draw(surf)
        data = self.game.save.data
        draw_text(surf, PUBLISHER, (8, GAME_H - 20), "gold", 11)
        draw_text(surf, f"Забегов: {data['runs']}   Побед: {data['wins']}   Концовки: {len(set(data['endings']))}/3",
                  (8, GAME_H - 8), "grey", 9, "bottomleft")


class SettingsState:
    def __init__(self, game):
        self.game = game
        self.menu = None
        self._build()

    def _build(self):
        g = self.game
        sel = self.menu.selected if self.menu else 0
        self.menu = Menu("НАСТРОЙКИ", [
            (f"Громкость: {int(g.audio.volume * 100)}%", self.volume),
            (f"Тряска экрана: {'вкл' if g.effects.shake_enabled else 'выкл'}", self.shake),
            ("Края экрана: " + ("размытие" if g.display.fill_mode == "blur" else "растянуть"), self.fill),
            ("Полный экран (F11)", g.display.toggle_fullscreen),
            ("Назад", g.go_menu),
        ])
        self.menu.selected = sel

    def volume(self):
        v = self.game.audio.volume + 0.2
        self.game.audio.set_volume(0.0 if v > 1.01 else v)
        self.game.save.data["settings"]["volume"] = self.game.audio.volume
        self.game.audio.play("pickup")
        self._build()

    def fill(self):
        d = self.game.display
        d.fill_mode = "stretch" if d.fill_mode == "blur" else "blur"
        self.game.save.data["settings"]["fill"] = d.fill_mode
        self._build()

    def shake(self):
        self.game.effects.shake_enabled = not self.game.effects.shake_enabled
        self.game.save.data["settings"]["screen_shake"] = self.game.effects.shake_enabled
        self._build()

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.game.go_menu()
        else:
            self.menu.handle_event(event)

    def update(self, dt):
        pass

    def draw(self, surf):
        surf.fill((24, 16, 40))
        self.menu.draw(surf)


class IntroState:
    """Спальня -> занавески -> взрыв -> THE SHINE -> начало забега."""

    ROOM = pygame.Rect(70, 50, 340, 190)

    def __init__(self, game):
        self.game = game
        self.stage = "bedroom"
        self.t = 0.0
        self.idle = 0.0
        self.pos = pygame.Vector2(240, 190)
        self.curtains = False
        self.line = 0

    def window_dist(self):
        return self.pos.distance_to(pygame.Vector2(240, 66))

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                self.game.start_new_run()  # пропуск вступления
            elif self.stage == "bedroom" and event.key == pygame.K_e and self.window_dist() < 40:
                self.curtains, self.stage, self.t = True, "view", 0.0
            elif self.stage == "talk" and event.key in (pygame.K_e, pygame.K_SPACE):
                self._next_line()
        elif event.type == pygame.MOUSEBUTTONDOWN and self.stage == "talk":
            self._next_line()

    def _next_line(self):
        self.line += 1
        self.game.audio.play("story")
        if self.line >= len(INTRO_LINES):
            self.game.start_new_run()

    def update(self, dt):
        self.t += dt
        fx = self.game.effects
        fx.update(dt)
        if self.stage == "bedroom":
            self.idle += dt
            keys = pygame.key.get_pressed()
            d = pygame.Vector2(keys[pygame.K_d] - keys[pygame.K_a], keys[pygame.K_s] - keys[pygame.K_w])
            if d.length_squared():
                self.pos += d.normalize() * 90 * dt
            self.pos.x = max(self.ROOM.left + 8, min(self.ROOM.right - 8, self.pos.x))
            self.pos.y = max(self.ROOM.top + 20, min(self.ROOM.bottom - 8, self.pos.y))
            if self.idle > 40:  # страховка: вступление не должно зависнуть
                self.curtains, self.stage, self.t = True, "view", 0.0
        elif self.stage == "view" and self.t > 2.5:
            self.stage, self.t = "blast", 0.0
            self.game.audio.play("nuke")
            fx.flash((255, 255, 255), 2.5)
        elif self.stage == "blast":
            fx.shake(4, 0.1)
            self.pos.y = min(self.ROOM.bottom - 8, self.pos.y + 25 * dt)
            if self.t > 3.0:
                self.stage, self.t = "talk", 0.0
                self.game.audio.play("boss")

    def draw(self, surf):
        if self.stage == "talk":
            surf.fill((10, 6, 20))
            draw_shine(surf, GAME_W // 2, 95, self.t)
            speaker, text = INTRO_LINES[min(self.line, len(INTRO_LINES) - 1)]
            box = pygame.Rect(30, 180, GAME_W - 60, 74)
            pygame.draw.rect(surf, (24, 16, 40), box)
            pygame.draw.rect(surf, (255, 215, 90), box, 1)
            draw_text(surf, speaker, (box.x + 8, box.y + 5), "gold", 12)
            for i, line in enumerate(wrap(text, box.width - 16)):
                draw_text(surf, line, (box.x + 8, box.y + 22 + i * 13))
            draw_text(surf, "[E] дальше", (box.right - 8, box.bottom - 5), "grey", 10, "bottomright")
            return
        surf.fill((40, 30, 50))
        r = self.ROOM
        pygame.draw.rect(surf, (176, 130, 90), r)
        for x in range(r.left, r.right, 20):
            pygame.draw.line(surf, (150, 108, 72), (x, r.top), (x, r.bottom))
        pygame.draw.rect(surf, (110, 160, 210), (r.left + 14, r.top + 22, 70, 44))      # кровать
        pygame.draw.rect(surf, (255, 250, 240), (r.left + 14, r.top + 22, 18, 44))
        pygame.draw.rect(surf, (34, 24, 48), (r.left + 14, r.top + 22, 70, 44), 1)
        win = pygame.Rect(210, r.top - 6, 60, 36)
        if self.curtains:
            pygame.draw.rect(surf, (120, 200, 255), win)
            for i in range(3):
                pygame.draw.rect(surf, (220, 200, 170), (win.x + 4 + i * 19, win.bottom - 14, 14, 14))
            pygame.draw.rect(surf, (200, 80, 70), (win.x, win.y, 10, win.h))
            pygame.draw.rect(surf, (200, 80, 70), (win.right - 10, win.y, 10, win.h))
        else:
            pygame.draw.rect(surf, (200, 80, 70), win)
            pygame.draw.line(surf, (150, 40, 40), (win.centerx, win.y), (win.centerx, win.bottom), 2)
        pygame.draw.rect(surf, (34, 24, 48), win, 2)
        sprites = self.game.sprites
        img = sprites.get("player")
        surf.blit(img, img.get_rect(midbottom=(int(self.pos.x), int(self.pos.y))))
        if self.stage == "bedroom":
            draw_text(surf, "Ранее весеннее утро. Подойди к окну.", (GAME_W // 2, 12), "white", 11, "midtop")
            if self.window_dist() < 40:
                draw_text(surf, "[E] открыть занавески", (GAME_W // 2, 28), "gold", 11, "midtop")
            draw_text(surf, "WASD — движение   Enter — пропустить", (GAME_W // 2, GAME_H - 6), "grey", 9, "midbottom")
        elif self.stage == "view":
            draw_text(surf, "Гамбургер, штат Киш. Тихое утро.", (GAME_W // 2, 12), "white", 11, "midtop")
        if self.stage == "blast":
            veil = pygame.Surface((GAME_W, GAME_H), pygame.SRCALPHA)
            veil.fill((0, 0, 0, int(255 * max(0, min(1, (self.t - 1.8) / 1.2)))))
            surf.blit(veil, (0, 0))
        self.game.effects.draw_flash(surf)


class EndScreen:
    """Экран смерти или победы."""

    def __init__(self, game, play, won):
        self.game, self.play, self.won = game, play, won
        self.verdict = play.morality.verdict()
        self.t = 0.0
        self.menu = Menu("", [("Новый забег", game.new_game), ("В меню", game.go_menu)])

    def handle_event(self, event):
        self.menu.handle_event(event)

    def update(self, dt):
        self.t += dt

    def draw(self, surf):
        surf.fill((14, 8, 24) if not self.won else (40, 30, 70))
        title = f"{self.play.zone['boss_name']} ПОВЕРЖЕН" if self.won else "ТЫ УМЕР"
        draw_text(surf, title, (GAME_W // 2, 30), "gold" if self.won else "red", 24, "midtop")
        p = self.play
        draw_text(surf, f"Комнат пройдено: {p.rooms_cleared}   Предметов: {len(p.player.inv.items)}   Монет: {p.player.coins}",
                  (GAME_W // 2, 70), "white", 11, "midtop")
        draw_text(surf, f"THE SHINE: «{self.verdict}»", (GAME_W // 2, 95), "gold", 12, "midtop")
        if self.won:
            for i, line in enumerate(wrap("Хаос повержен, но это ещё не конец. Предательство и финальный бой с THE SHINE пока не добавлены в эту версию.", 360)):
                draw_text(surf, line, (GAME_W // 2, 120 + i * 13), "grey", 10, "midtop")
        else:
            draw_text(surf, "«Ожидаемо».", (GAME_W // 2, 120), "grey", 11, "midtop")
        for i, tid in enumerate(p.morality.run_testimonies[:4]):
            from .systems.morality import TESTIMONIES
            draw_text(surf, "• " + TESTIMONIES[tid][0], (150, 150 + i * 12), "white", 10)
        for i, (label, _) in enumerate(self.menu.entries):
            sel = i == self.menu.selected
            draw_text(surf, ("> " if sel else "  ") + label, (GAME_W // 2, 215 + i * 16), "gold" if sel else "white", 13, "center")


# --- концовки и титры ---
# страница: (текст, секунд показа); пустой текст — пауза
ENDINGS = {
    "good": {
        "title": "GOOD ENDING", "color": "gold", "credits": True,
        "pages": [("Врата рая медленно открываются.", 3.0), ("Ты всё ещё не заслужил это.", 4.0), ("", 2.5),
                  ("Но, наверное, никто не заслуживает.", 4.5)],
        "after": "Ты проходишь через врата.",
    },
    "bad": {
        "title": "BAD ENDING", "color": "red", "credits": False,
        "pages": [("Свет гаснет. Врата так и не открылись.", 3.0), ("", 1.5), ("Ну... правила есть правила.", 4.5)],
        "after": "Испытание начнётся снова.",
    },
    "secret": {
        "title": "SECRET ENDING", "color": "blue", "credits": True,
        "pages": [("Его силуэт дрожит. Крылья осыпаются.", 3.5), ("Подожди. Я помню этот двор. Гамбургер, штат Киш.", 4.0),
                  ("Я тоже открыл занавески. Весной. Утром.", 4.0), ("Меня тоже отправили за Хаосом. Я тоже победил.", 4.0),
                  ("И остался. Кто-то же должен был держать врата.", 4.5), ("", 2.0),
                  ("Теперь ты знаешь, как это работает.", 4.0), ("Ты разбиваешь нимб. Врата закрываются. Никто не входит.", 5.0)],
        "after": "Утром кто-то открыл занавески.",
    },
}


class EndingState:
    """Показывает страницы концовки; E / Enter / клик пролистывают."""

    def __init__(self, game, play, kind):
        self.game, self.kind = game, kind
        self.data = ENDINGS[kind]
        self.pages = list(self.data["pages"]) + [("@title", 5.0)]
        self.idx, self.t = 0, 0.0
        self.rooms_cleared = play.rooms_cleared

    def _next(self):
        self.idx += 1
        self.t = 0.0
        if self.idx >= len(self.pages):
            if self.data["credits"]:
                self.game.go_credits()
            else:
                self.game.go_menu()

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_e, pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE):
            self._next()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._next()

    def update(self, dt):
        self.t += dt
        if self.idx < len(self.pages) and self.t >= self.pages[self.idx][1]:
            self._next()

    def draw(self, surf):
        bg = {"good": (16, 12, 34), "bad": (24, 6, 10), "secret": (8, 12, 30)}[self.kind]
        surf.fill(bg)
        if self.idx >= len(self.pages):
            return
        text, hold = self.pages[self.idx]
        fade = min(1.0, self.t / 0.6, max(0.0, (hold - self.t) / 0.6))
        if self.kind == "good":  # врата светлеют к концу
            glow = min(1.0, (self.idx + self.t / max(hold, 0.1)) / len(self.pages))
            pygame.draw.rect(surf, (int(60 + 190 * glow), int(50 + 190 * glow), int(80 + 120 * glow)), (210, 70, 60, 120), border_radius=30)
        if text == "@title":
            draw_text(surf, self.data["title"], (GAME_W // 2, 100), self.data["color"], 26, "center")
            draw_text(surf, self.data["after"], (GAME_W // 2, 135), "grey", 12, "center")
            draw_text(surf, f"Комнат пройдено: {self.rooms_cleared}", (GAME_W // 2, 160), "grey", 10, "center")
            return
        if not text:
            return
        shade = int(255 * fade)
        for i, line in enumerate(wrap(text, 380, 14)):
            col = (shade, shade, shade) if self.kind != "good" else (shade, int(shade * 0.92), int(shade * 0.7))
            draw_text(surf, line, (GAME_W // 2, GAME_H - 80 + i * 17), col, 14, "center")


CREDITS_LINES = (
    "THE SHINE", "", "Издатель", "FreeDom Studio", "", "Музыка", "FreeDom Studio", "",
    "Игра создана на Python и Pygame", "", "Программирование", "совместно с Claude (Anthropic)", "",
    "Особая благодарность", "Лесник, Сосед, Мэр, Хаос", "и всем, кто так и не заслужил", "", "", "Спасибо за игру", "",
)


class CreditsState:
    """Титры. Esc / Enter — пропустить."""

    def __init__(self, game):
        self.game = game
        self.y = float(GAME_H)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_RETURN):
            self.game.go_menu()

    def update(self, dt):
        self.y -= 26 * dt
        if self.y + len(CREDITS_LINES) * 20 < 0:
            self.game.go_menu()

    def draw(self, surf):
        surf.fill((10, 6, 20))
        for i, line in enumerate(CREDITS_LINES):
            big = i == 0
            draw_text(surf, line, (GAME_W // 2, int(self.y + i * 20)), "gold" if big else "white", 20 if big else 12, "center")


class CharacterSelectState:
    """Выбор персонажа: открытые доступны, закрытые показывают условие открытия."""

    def __init__(self, game):
        self.game = game
        self.ids = list(game.characters)
        self.unlocked = set(game.unlocked_chars())
        self.sel = max(0, self.ids.index(game.selected_char)) if game.selected_char in self.ids else 0

    # --- вспомогательное ---
    def _row_rect(self, i):
        return pygame.Rect(14, 44 + i * 36, 200, 32)

    def _stats(self, char):
        st = self.game.data.items.stats(char["start_items"], char["mods"])
        speed = st["speed"] / 105.0
        label = "медленный" if speed < 0.9 else "быстрый" if speed > 1.1 else "обычный"
        return int(round(st["max_hp"])) / 2, label

    def _confirm(self):
        cid = self.ids[self.sel]
        if cid in self.unlocked:
            self.game.begin_run(cid)

    # --- события ---
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.game.go_menu()
            elif event.key in (pygame.K_UP, pygame.K_w, pygame.K_LEFT, pygame.K_a):
                self.sel = (self.sel - 1) % len(self.ids)
            elif event.key in (pygame.K_DOWN, pygame.K_s, pygame.K_RIGHT, pygame.K_d):
                self.sel = (self.sel + 1) % len(self.ids)
            elif event.key in (pygame.K_RETURN, pygame.K_e, pygame.K_SPACE):
                self._confirm()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and hasattr(event, "pos_game"):
            for i in range(len(self.ids)):
                if self._row_rect(i).collidepoint(event.pos_game):
                    if i == self.sel:
                        self._confirm()
                    self.sel = i
                    break

    def update(self, dt):
        pass

    # --- отрисовка ---
    def draw(self, surf):
        g = self.game
        surf.fill((18, 12, 32))
        draw_text(surf, "ВЫБОР ПЕРСОНАЖА", (GAME_W // 2, 8), "gold", 16, "midtop")
        for i, cid in enumerate(self.ids):
            char = g.characters[cid]
            rect = self._row_rect(i)
            locked = cid not in self.unlocked
            sel = i == self.sel
            pygame.draw.rect(surf, (40, 28, 66) if sel else (26, 18, 44), rect, border_radius=4)
            pygame.draw.rect(surf, (255, 215, 90) if sel else (80, 64, 110), rect, 1, border_radius=4)
            icon = g.sprites.get("player_" + cid)
            icon = g.sprites.white("player_" + cid) if locked else icon
            if locked:
                icon = icon.copy()
                icon.fill((60, 50, 90, 255), special_flags=pygame.BLEND_RGBA_MIN)
            scale = min(1.0, 26 / max(icon.get_width(), icon.get_height()))
            icon = pygame.transform.scale(icon, (max(1, int(icon.get_width() * scale)), max(1, int(icon.get_height() * scale))))
            surf.blit(icon, icon.get_rect(center=(rect.x + 18, rect.centery)))
            draw_text(surf, "???" if locked else char["name"], (rect.x + 40, rect.centery), "grey" if locked else ("gold" if sel else "white"), 12, "midleft")
        # правая панель — подробности выбранного
        cid = self.ids[self.sel]
        char = g.characters[cid]
        locked = cid not in self.unlocked
        panel = pygame.Rect(232, 44, GAME_W - 246, 212)
        pygame.draw.rect(surf, (26, 18, 44), panel, border_radius=4)
        pygame.draw.rect(surf, (110, 90, 150), panel, 1, border_radius=4)
        big = g.sprites.get("player_" + cid)
        if locked:
            big = g.sprites.white("player_" + cid).copy()
            big.fill((60, 50, 90, 255), special_flags=pygame.BLEND_RGBA_MIN)
        big = pygame.transform.scale(big, (big.get_width() * 3, big.get_height() * 3))
        surf.blit(big, big.get_rect(center=(panel.x + 44, panel.y + 52)))
        if locked:
            kills, need = char_progress(char, g.save.data)
            boss = ZONES[[z for z in ZONES if ZONES[z].get("boss") == char["unlock"]["boss"]][0]]["boss_name"].title()
            draw_text(surf, "ЗАКРЫТО", (panel.x + 96, panel.y + 14), "red", 13)
            for i, line in enumerate(wrap(f"Победи босса «{boss}» {need} раз.", panel.width - 108, 11)):
                draw_text(surf, line, (panel.x + 96, panel.y + 34 + i * 13), "white", 11)
            draw_text(surf, f"Прогресс: {min(kills, need)}/{need}", (panel.x + 96, panel.y + 66), "gold", 11)
            return
        hearts, speed = self._stats(char)
        draw_text(surf, char["name"], (panel.x + 96, panel.y + 12), "gold", 14)
        draw_text(surf, f"Сердца: {hearts:g}   Скорость: {speed}", (panel.x + 96, panel.y + 32), "white", 10)
        traits = []
        if "ghost" in char["traits"]:
            traits.append("проходит сквозь блоки")
        if "gravity_immune" in char["traits"]:
            traits.append("гравитация не действует")
        if char["scale"] > 1.0:
            traits.append("большой")
        if traits:
            draw_text(surf, ", ".join(traits).capitalize(), (panel.x + 96, panel.y + 46), "green", 10)
        for i, line in enumerate(wrap(char["desc"], panel.width - 16, 10)):
            draw_text(surf, line, (panel.x + 8, panel.y + 96 + i * 12), "grey", 10)
        draw_text(surf, "Стартовые предметы:" if char["start_items"] else "Стартовых предметов нет", (panel.x + 8, panel.y + 148), "gold", 10)
        for i, item_id in enumerate(char["start_items"]):
            surf.blit(g.sprites.icon(item_id), (panel.x + 8, panel.y + 164 + i * 16))
            draw_text(surf, g.data.items.items[item_id].name, (panel.x + 28, panel.y + 164 + i * 16), "white", 10)
        draw_text(surf, "Enter — начать, Esc — назад", (GAME_W // 2, GAME_H - 6), "grey", 9, "midbottom")
