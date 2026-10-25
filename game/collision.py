"""Коллизии круг/прямоугольник и круг/круг."""
import math


def circles_overlap(p1, r1, p2, r2):
    dx, dy = p1.x - p2.x, p1.y - p2.y
    rr = r1 + r2
    return dx * dx + dy * dy < rr * rr


def circle_rect_overlap(pos, r, rect):
    cx = max(rect.left, min(pos.x, rect.right))
    cy = max(rect.top, min(pos.y, rect.bottom))
    dx, dy = pos.x - cx, pos.y - cy
    return dx * dx + dy * dy < r * r


def push_out_of_rect(pos, r, rect):
    """Выталкивает круг из прямоугольника. True, если позиция изменилась."""
    cx = max(rect.left, min(pos.x, rect.right))
    cy = max(rect.top, min(pos.y, rect.bottom))
    dx, dy = pos.x - cx, pos.y - cy
    d2 = dx * dx + dy * dy
    if d2 >= r * r:
        return False
    if d2 > 0:
        d = math.sqrt(d2)
        k = (r - d) / d
        pos.x += dx * k
        pos.y += dy * k
    else:  # центр внутри прямоугольника — выход по кратчайшей оси
        gaps = {"l": pos.x - rect.left, "r": rect.right - pos.x,
                "t": pos.y - rect.top, "b": rect.bottom - pos.y}
        side = min(gaps, key=gaps.get)
        if side == "l":
            pos.x = rect.left - r
        elif side == "r":
            pos.x = rect.right + r
        elif side == "t":
            pos.y = rect.top - r
        else:
            pos.y = rect.bottom + r
    return True
