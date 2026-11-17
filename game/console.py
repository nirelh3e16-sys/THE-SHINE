"""Консоль разработчика: открывается во время забега по F4 + 3.

Все возможности тест-меню (F4 + T) есть и здесь, плюс команды для предметов и телепорта.
Главное отличие: консоль НЕ включает тест-режим — забег продолжает засчитываться (прогресс, бестиарий, концовки).
Команды вводятся по-английски (help — список). Разбор и выполнение команд не зависят от pygame (execute()),
поэтому их можно проверять тестами; pygame нужен только для обработки клавиш и отрисовки.
"""
from . import i18n
from .systems.items import RARITY_NAMES, THEME_NAMES
from .world.zones import ZONES, ZONE_ORDER

ROOM_KINDS = ("start", "shop", "treasure", "event", "boss", "miniboss")
ZONE_ALIASES = {"arena": "shine", "gates": "shine", "gate": "shine", "imp": "hell", "god": "heaven", "sky": "heaven",
                "wood": "forest", "town": "city", "suburb": "suburbs"}
MAX_INPUT = 120
MAX_LINES = 400
HELP = {
    "help": ("help [command]", "List commands or show help for one."),
    "clear": ("clear", "Clear the console."),
    "close": ("close", "Close the console (also Esc or F4 + 3)."),
    "god": ("god [on|off]", "Toggle invulnerability."),
    "damage": ("damage <value>|reset", "Set your damage (e.g. damage 10)."),
    "maxhp": ("maxhp <value>|<hearts>h", "Set max health: 12 = 6 hearts, or 6h."),
    "hp": ("hp <value>|full", "Set current health (2 = one heart)."),
    "reset": ("reset", "Reset the damage / max health overrides."),
    "coins": ("coins <n> | coins set <n>", "Add (or set) coins."),
    "heal": ("heal", "Restore full health."),
    "card": ("card", "Open a three-card item choice."),
    "teleport": ("teleport <place>", "Go to a location (forest, suburbs, city, center, shine, hell, heaven) "
                                      "or a room of this location (boss, miniboss, start, shop, treasure, event)."),
    "tp": ("tp <place>", "Alias of teleport."),
    "locations": ("locations", "List teleport targets."),
    "give": ("give <id|number> [...]", "Give items by id or number (see: items)."),
    "remove": ("remove <id|number>", "Take an item away."),
    "items": ("items [text]", "List all items with ids and numbers; the filter matches id, theme or rarity."),
    "inv": ("inv", "List the items you carry."),
    "combos": ("combos", "List item combinations (including hidden synergies)."),
    "killall": ("killall", "Kill every enemy in the room."),
}


def _num(text):
    try:
        return float(text)
    except ValueError:
        return None


class DevConsole:
    VISIBLE = 14

    def __init__(self, play):
        self.play = play
        self.lines = []          # [(text, color)]
        self.input = ""
        self.history = []
        self.hist_i = None
        self.scroll = 0
        self.print("THE SHINE console. Type help for commands. Esc closes.", "gold")
        self.commands = {
            "help": self.c_help, "clear": self.c_clear, "close": self.c_close, "exit": self.c_close, "god": self.c_god,
            "damage": self.c_damage, "maxhp": self.c_maxhp, "hp": self.c_hp, "reset": self.c_reset, "coins": self.c_coins,
            "heal": self.c_heal, "card": self.c_card, "teleport": self.c_teleport, "tp": self.c_teleport,
            "locations": self.c_locations, "give": self.c_give, "remove": self.c_remove, "items": self.c_items,
            "inv": self.c_inv, "combos": self.c_combos, "killall": self.c_killall,
        }

    # ------------------------------------------------------------------ вывод
    def print(self, text, color="white"):
        self.lines.append((str(text), color))
        del self.lines[:-MAX_LINES]
        self.scroll = 0

    def close(self):
        if self.play.console is self:
            self.play.toggle_console()

    # ------------------------------------------------------------------ выполнение
    def execute(self, line):
        """Выполнить строку команды. Ошибки печатаются в консоль, исключения наружу не выходят."""
        line = line.strip()
        if not line:
            return
        self.print("> " + line, "grey")
        name, *args = line.split()
        fn = self.commands.get(name.lower())
        if fn is None:
            self.print(f"Unknown command '{name}'. Type help.", "red")
            return
        try:
            fn(args)
        except (KeyError, ValueError, IndexError, TypeError, StopIteration) as exc:
            self.print(f"Error: {exc}", "red")

    # --- общие ---
    def c_help(self, args):
        if args:
            key = args[0].lower()
            if key in HELP:
                self.print(HELP[key][0], "gold")
                self.print(HELP[key][1])
            else:
                self.print(f"No help for '{args[0]}'.", "red")
            return
        for name in HELP:
            self.print(f"{HELP[name][0]:<30} {HELP[name][1]}"[:110], "white")

    def c_clear(self, args):
        self.lines.clear()

    def c_close(self, args):
        self.close()

    # --- характеристики (то же, что в тест-меню, но без пометки «тест-забег») ---
    def c_god(self, args):
        p = self.play.player
        p.god = (args[0].lower() in ("on", "1", "true")) if args else not p.god
        self.print(f"God mode: {'ON' if p.god else 'off'}", "green" if p.god else "white")

    def c_damage(self, args):
        p = self.play.player
        if not args:
            self.print(f"Damage: {p.stats['damage']:.1f}")
            return
        if args[0].lower() == "reset":
            p.debug_damage = None
        else:
            value = _num(args[0])
            if value is None or value <= 0:
                raise ValueError("damage needs a positive number")
            p.debug_damage = max(0.5, round(value, 1))
        p.recompute()
        self.print(f"Damage: {p.stats['damage']:.1f}", "green")

    def c_maxhp(self, args):
        p = self.play.player
        if not args:
            self.print(f"Max health: {p.max_hp} ({p.max_hp / 2:g} hearts)")
            return
        raw = args[0].lower()
        value = _num(raw[:-1]) * 2 if raw.endswith("h") and _num(raw[:-1]) is not None else _num(raw)
        if value is None:
            raise ValueError("maxhp needs a number, e.g. 12 or 6h")
        p.debug_max_hp = max(2, min(200, int(value)))
        p.recompute()
        self.print(f"Max health: {p.max_hp} ({p.max_hp / 2:g} hearts)", "green")

    def c_hp(self, args):
        p = self.play.player
        if not args:
            self.print(f"Health: {p.hp}/{p.max_hp}")
            return
        value = p.max_hp if args[0].lower() == "full" else _num(args[0])
        if value is None:
            raise ValueError("hp needs a number or 'full'")
        p.hp = max(1, min(p.max_hp, int(value)))
        self.print(f"Health: {p.hp}/{p.max_hp}", "green")

    def c_reset(self, args):
        p = self.play.player
        p.debug_damage = p.debug_max_hp = None
        p.recompute()
        self.print("Damage and max health overrides cleared.", "green")

    def c_coins(self, args):
        p = self.play.player
        if not args:
            self.print(f"Coins: {p.coins}")
            return
        if args[0].lower() == "set":
            value = _num(args[1])
            if value is None:
                raise ValueError("coins set <n>")
            p.coins = max(0, int(value))
        else:
            value = _num(args[0])
            if value is None:
                raise ValueError("coins <n>")
            self.play.add_coins(int(value))
        self.print(f"Coins: {p.coins}", "gold")

    def c_heal(self, args):
        p = self.play.player
        p.hp = p.max_hp
        self.print(f"Health: {p.hp}/{p.max_hp}", "green")

    def c_card(self, args):
        self.play.console = None
        import pygame
        pygame.key.set_repeat(0)
        self.play.open_cards()

    def c_killall(self, args):
        n = 0
        for e in self.play.room.enemies:
            if not e.dead:
                e.hp, e.dead = 0, True
                n += 1
        self.print(f"Killed {n} enemies.", "green")

    # --- телепорт ---
    def zone_targets(self):
        return {zid: ZONES[zid]["name"] for zid in ZONE_ORDER}

    def resolve_zone(self, token):
        token = ZONE_ALIASES.get(token.lower(), token.lower())
        for zid, name in self.zone_targets().items():
            if token in (zid, name.lower(), i18n.tr(name).lower()):
                return zid
        return None

    def c_locations(self, args):
        for zid, name in self.zone_targets().items():
            suffix = " (starts the fight)" if ZONES[zid].get("arena") else ""
            self.print(f"{zid:<9} {i18n.tr(name)}{suffix}")
        self.print("Rooms of the current location: " + ", ".join(ROOM_KINDS), "grey")

    def c_teleport(self, args):
        if not args:
            self.print("teleport <place>. Try: locations", "red")
            return
        play, token = self.play, args[0].lower()
        zid = self.resolve_zone(token)
        if zid is not None:
            play.console = None
            self._release()
            play.debug_goto_zone(ZONE_ORDER.index(zid), mark=False)
            return
        if token in ("boss", "miniboss") or token in ROOM_KINDS:
            if token == "boss":
                ok = True
                self._leave()
                play.debug_goto_boss(mark=False)
            elif token == "miniboss":
                self._leave()
                play.debug_goto_miniboss(mark=False)
                ok = True
            else:
                self._leave()
                ok = play.goto_room_kind(token)
            if not ok:
                play.console = self
                self.print(f"No '{token}' room in this location.", "red")
            return
        raise ValueError(f"unknown place '{args[0]}' (try: locations)")

    def _release(self):
        import pygame
        pygame.key.set_repeat(0)

    def _leave(self):
        """Закрыть консоль перед переходом, чтобы игрок увидел новую комнату."""
        self.play.console = None
        self._release()

    # --- предметы ---
    @property
    def db(self):
        return self.play.db

    def _describe(self, item):
        rarity = RARITY_NAMES.get(item.rarity)
        theme = THEME_NAMES.get(item.theme)
        tag = f" [{i18n.tr(rarity)}, {i18n.tr(theme)}]" if rarity and theme else ""
        kind = " (active)" if item.active else ""
        return f"{item.num:>3} {item.id:<22} {item.name}{kind}{tag}"

    def c_items(self, args):
        text = " ".join(args).lower()
        shown = 0
        for item in sorted(self.db.items.values(), key=lambda d: d.num):
            hay = " ".join(filter(None, (item.id, item.theme, item.rarity, item.name.lower(), i18n.tr(item.name).lower())))
            if text and text not in hay:
                continue
            self.print(self._describe(item), "white")
            shown += 1
        self.print(f"{shown} item(s). Use: give <id|number>", "grey")

    def c_inv(self, args):
        owned = self.play.player.inv.items
        for item_id in owned:
            self.print(self._describe(self.db.items[item_id]))
        self.print(f"{len(owned)} item(s) carried.", "grey")

    def c_combos(self, args):
        for c in self.db.combos:
            names = " + ".join(self.db.items[n].id for n in c["needs"])
            hidden = " (hidden)" if c.get("hidden") else ""
            self.print(f"{c['name']}{hidden}: {names}")

    def c_give(self, args):
        if not args:
            raise ValueError("give <id|number>  (see: items)")
        for token in args:
            item_id = self.db.resolve(token)
            if item_id is None:
                self.print(f"Unknown item '{token}'.", "red")
                continue
            item = self.db.items[item_id]
            if item_id in self.play.player.inv.items:
                self.print(f"Already have {item.id}.", "grey")
                continue
            self.play.give_item(item_id)
            self.print(f"Given: {item.id} ({item.name})", "green")

    def c_remove(self, args):
        if not args:
            raise ValueError("remove <id|number>")
        p = self.play.player
        item_id = self.db.resolve(args[0])
        if item_id is None or item_id not in p.inv.items:
            self.print(f"You do not have '{args[0]}'.", "red")
            return
        p.inv.items.remove(item_id)
        if p.inv.active_id == item_id:
            p.inv.active_id = None
            p.inv.active_cd = 0.0
        p.recompute()
        self.print(f"Removed: {item_id}", "green")

    # ------------------------------------------------------------------ ввод
    def complete(self):
        """Tab: дополнить команду или последний аргумент (id предмета, место телепорта)."""
        parts = self.input.split(" ")
        word = parts[-1].lower()
        if len(parts) == 1:
            pool = sorted(set(self.commands))
        elif parts[0].lower() in ("give", "remove", "items"):
            pool = sorted(self.db.items)
        elif parts[0].lower() in ("teleport", "tp"):
            pool = sorted(list(self.zone_targets()) + list(ROOM_KINDS))
        else:
            return
        matches = [m for m in pool if m.startswith(word)]
        if not matches:
            return
        common = matches[0]
        for m in matches[1:]:
            while not m.startswith(common):
                common = common[:-1]
        if len(matches) > 1 and common == word:
            self.print("  ".join(matches[:16]) + (" ..." if len(matches) > 16 else ""), "grey")
        parts[-1] = common + (" " if len(matches) == 1 else "")
        self.input = " ".join(parts)[:MAX_INPUT]

    def handle_event(self, event):
        import pygame
        if event.type == pygame.MOUSEWHEEL:
            self.scroll = max(0, self.scroll + event.y * 2)
            return
        if event.type != pygame.KEYDOWN:
            return
        k = event.key
        if k == pygame.K_ESCAPE:
            self.close()
        elif k in (pygame.K_RETURN, pygame.K_KP_ENTER):
            line, self.input, self.hist_i = self.input, "", None
            if line.strip():
                self.history.append(line)
            self.execute(line)
        elif k == pygame.K_BACKSPACE:
            self.input = self.input[:-1]
        elif k == pygame.K_TAB:
            self.complete()
        elif k == pygame.K_UP and self.history:
            self.hist_i = len(self.history) - 1 if self.hist_i is None else max(0, self.hist_i - 1)
            self.input = self.history[self.hist_i]
        elif k == pygame.K_DOWN and self.hist_i is not None:
            self.hist_i += 1
            if self.hist_i >= len(self.history):
                self.hist_i, self.input = None, ""
            else:
                self.input = self.history[self.hist_i]
        elif k == pygame.K_PAGEUP:
            self.scroll += self.VISIBLE - 2
        elif k == pygame.K_PAGEDOWN:
            self.scroll = max(0, self.scroll - (self.VISIBLE - 2))
        elif event.unicode and event.unicode.isprintable() and len(self.input) < MAX_INPUT:
            self.input += event.unicode

    # ------------------------------------------------------------------ отрисовка
    def draw(self, surf):
        import pygame
        from .settings import GAME_W
        from .ui.text import draw_text, wrap
        height = 20 + self.VISIBLE * 11 + 14
        veil = pygame.Surface((GAME_W, height), pygame.SRCALPHA)
        veil.fill((6, 6, 16, 225))
        surf.blit(veil, (0, 0))
        pygame.draw.line(surf, (255, 215, 90), (0, height), (GAME_W, height), 1)
        rows = []
        for text, color in self.lines:
            for i, part in enumerate(wrap(text, GAME_W - 16, 9) or [""]):
                rows.append((("  " if i else "") + part, color))
        self.scroll = min(self.scroll, max(0, len(rows) - self.VISIBLE))
        end = len(rows) - self.scroll
        y = 4
        for text, color in rows[max(0, end - self.VISIBLE):end]:
            draw_text(surf, text, (8, y), color, 9)
            y += 11
        if self.scroll:
            draw_text(surf, f"^ {self.scroll}", (GAME_W - 8, 4), "grey", 9, "topright")
        cursor = "_" if pygame.time.get_ticks() // 450 % 2 else " "
        draw_text(surf, "> " + self.input + cursor, (8, height - 13), "gold", 10)
