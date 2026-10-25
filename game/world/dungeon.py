"""Чистая генерация раскладки комнат (без pygame, легко тестируется)."""
import random
from dataclasses import dataclass, field

DIRS = {"N": (0, -1), "S": (0, 1), "E": (1, 0), "W": (-1, 0)}
OPP = {"N": "S", "S": "N", "E": "W", "W": "E"}


@dataclass
class RoomSpec:
    pos: tuple
    kind: str = "combat"
    doors: dict = field(default_factory=dict)  # направление -> позиция соседа
    depth: int = 0


def _connect(a, direction, b):
    a.doors[direction] = b.pos
    b.doors[OPP[direction]] = a.pos


def generate_layout(n_rooms, rng, extra_kinds=(), house=False):
    """Дерево комнат: все комнаты связаны дверями, выход всегда существует.

    extra_kinds — дополнительные особые комнаты (например "house") вместо обычных боевых.
    house=True — режим мини-данжа дома: 3+ комнаты, вместо босса — комната с наградой.
    """
    n_rooms = max(3 if house else 5, n_rooms)
    rooms = {(0, 0): RoomSpec((0, 0), "start", depth=0)}
    order = [(0, 0)]
    attempts = 0
    while len(rooms) < n_rooms and attempts < 5000:
        attempts += 1
        base = rng.choice(order)
        d = rng.choice(sorted(DIRS))
        dx, dy = DIRS[d]
        new_pos = (base[0] + dx, base[1] + dy)
        if new_pos in rooms:
            continue
        neighbours = sum(1 for ax, ay in DIRS.values() if (new_pos[0] + ax, new_pos[1] + ay) in rooms)
        if neighbours > 1 and rng.random() < 0.85:
            continue
        spec = RoomSpec(new_pos, "combat", depth=rooms[base].depth + 1)
        rooms[new_pos] = spec
        _connect(rooms[base], d, spec)
        order.append(new_pos)
    _assign_kinds(rooms, rng)
    if house:
        remap = {"boss": "treasure", "shop": "combat", "treasure": "combat", "event": "combat"}
        for spec in rooms.values():
            spec.kind = remap.get(spec.kind, spec.kind)
    for kind in extra_kinds:
        combat = sorted((r for r in rooms.values() if r.kind == "combat"), key=lambda r: r.pos)
        if combat:
            rng.choice(combat).kind = kind
    return rooms


def _assign_kinds(rooms, rng):
    start = rooms[(0, 0)]
    cand = [r for r in rooms.values() if r is not start]
    leaves = sorted((r for r in cand if len(r.doors) == 1), key=lambda r: (-r.depth, r.pos))
    inner = sorted((r for r in cand if len(r.doors) > 1), key=lambda r: r.pos)
    boss = leaves[0] if leaves else max(cand, key=lambda r: (r.depth, r.pos))
    boss.kind = "boss"
    slots = [r for r in leaves if r is not boss]
    rng.shuffle(slots)
    rng.shuffle(inner)
    slots += inner
    slots = [r for r in slots if r is not boss]
    wanted = ["treasure", "shop", "event"]
    if len(rooms) >= 8:
        wanted.append("event")
    for kind in wanted:
        if slots:
            slots.pop(0).kind = kind


def reachable(rooms, start=(0, 0)):
    seen = {start}
    stack = [start]
    while stack:
        cur = stack.pop()
        for nxt in rooms[cur].doors.values():
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    return seen


def validate_layout(rooms, require_boss=True):
    """Возвращает список проблем (пустой список — раскладка корректна)."""
    problems = []
    if (0, 0) not in rooms:
        return ["нет стартовой комнаты"]
    if reachable(rooms) != set(rooms):
        problems.append("есть недостижимые комнаты")
    for pos, spec in rooms.items():
        for d, other in spec.doors.items():
            back = rooms.get(other)
            if back is None or back.doors.get(OPP[d]) != pos:
                problems.append(f"несимметричная дверь {pos}->{other}")
    kinds = [r.kind for r in rooms.values()]
    if require_boss and kinds.count("boss") != 1:
        problems.append("должна быть ровно одна комната босса")
    if kinds.count("start") != 1:
        problems.append("должна быть ровно одна стартовая комната")
    return problems


class Dungeon:
    """Раскладка зоны + раздача уникальных предметов + данные для миникарты."""

    def __init__(self, seed, n_rooms, item_ids, extra_kinds=(), house=False, arena=False):
        rng = random.Random(seed)
        if arena:  # финал: одна комната босса без дверей
            self.specs = {(0, 0): RoomSpec((0, 0), "boss", {}, 0)}
        else:
            self.specs = generate_layout(n_rooms, rng, extra_kinds, house)
        pool = list(item_ids)
        rng.shuffle(pool)
        self._item_pool = pool
        self.item_for_room = {}
        for pos in sorted(self.specs):
            spec = self.specs[pos]
            need = {"treasure": 1, "shop": 3, "boss": 1}.get(spec.kind, 0)
            self.item_for_room[pos] = [self._item_pool.pop() for _ in range(need) if self._item_pool]
        combat = [p for p, s in sorted(self.specs.items()) if s.kind == "combat"]
        self.false_mark = rng.choice(combat) if combat else None
        self.visited = {(0, 0)}
        self.pos = (0, 0)

    def spec(self, pos=None):
        return self.specs[pos or self.pos]

    def known_rooms(self):
        """Посещённые комнаты и их соседи за дверями."""
        known = set(self.visited)
        for p in self.visited:
            known.update(self.specs[p].doors.values())
        return known

    def map_kind(self, pos, compass):
        """Какой тип комнаты показать на карте."""
        spec = self.specs[pos]
        if pos in self.visited:
            return spec.kind
        if compass:
            if pos == self.false_mark:
                return "treasure"
            if spec.kind in ("treasure", "shop", "boss", "event", "house"):
                return spec.kind
        return "unknown"
