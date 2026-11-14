"""Мини-растеризатор для пиксель-арта в стиле Rebirth/Repentance+.

Не зависит от pygame (pygame нужен только в to_surface), поэтому спрайты можно строить и проверять отдельно.
Рисунок: тёмный контур в 1 пиксель, три тона на форму (основной, тень в фиолетово-коричневую сторону, блик),
крупные головы и глаза, мягкая тень под персонажем.
"""
import math

OUT = (26, 13, 18)          # контур: почти чёрный тёплый коричневый
SHADOW_TINT = (66, 20, 54)  # в этот цвет уводим тени (тёплый бордово-фиолетовый, как в Rebirth)
LIGHT_TINT = (255, 244, 222)


def mix(a, b, t):
    return (int(a[0] + (b[0] - a[0]) * t), int(a[1] + (b[1] - a[1]) * t), int(a[2] + (b[2] - a[2]) * t))


def dark(c, t=0.34):
    return mix(c, SHADOW_TINT, t)


def light(c, t=0.42):
    return mix(c, LIGHT_TINT, t)


def ell_set(cx, cy, rx, ry):
    out = set()
    rx, ry = max(rx, 0.5), max(ry, 0.5)
    for y in range(int(math.floor(cy - ry)), int(math.ceil(cy + ry)) + 1):
        for x in range(int(math.floor(cx - rx)), int(math.ceil(cx + rx)) + 1):
            dx, dy = (x + 0.5 - cx) / rx, (y + 0.5 - cy) / ry
            if dx * dx + dy * dy <= 1.0:
                out.add((x, y))
    return out


def ring_set(cx, cy, rx0, ry0, rx1, ry1):
    inner = ell_set(cx, cy, rx0, ry0)
    return {p for p in ell_set(cx, cy, rx1, ry1) if p not in inner}


def rect_set(x, y, w, h):
    return {(i, j) for j in range(int(y), int(y + h)) for i in range(int(x), int(x + w))}


def poly_set(pts):
    out = set()
    n = len(pts)
    if n < 3:
        return out
    ys = [p[1] for p in pts]
    for y in range(int(math.floor(min(ys))), int(math.ceil(max(ys))) + 1):
        sy = y + 0.5
        xs = []
        for i in range(n):
            (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % n]
            if (y0 <= sy < y1) or (y1 <= sy < y0):
                xs.append(x0 + (sy - y0) * (x1 - x0) / (y1 - y0))
        xs.sort()
        for k in range(0, len(xs) - 1, 2):
            for x in range(int(math.floor(xs[k] + 0.5)), int(math.floor(xs[k + 1] + 0.5))):
                out.add((x, y))
    return out


def line_set(x0, y0, x1, y1, w=1):
    out = set()
    x0, y0, x1, y1 = int(round(x0)), int(round(y0)), int(round(x1)), int(round(y1))
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
    err = dx + dy
    while True:
        for i in range(w):
            for j in range(w):
                out.add((x0 + i - (w - 1) // 2, y0 + j - (w - 1) // 2))
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy
    return out


class Canvas:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.p = [[None] * w for _ in range(h)]

    # --- пиксели ---
    def px(self, x, y, c):
        x, y = int(x), int(y)
        if c is None or not (0 <= x < self.w and 0 <= y < self.h):
            return
        if len(c) == 4 and c[3] < 255:
            o = self.p[y][x]
            if o is None:
                self.p[y][x] = c
            else:
                a = c[3] / 255.0
                self.p[y][x] = (int(o[0] + (c[0] - o[0]) * a), int(o[1] + (c[1] - o[1]) * a),
                                int(o[2] + (c[2] - o[2]) * a), max(o[3], c[3]))
        else:
            self.p[y][x] = (c[0], c[1], c[2], 255)

    def get(self, x, y):
        return self.p[y][x] if 0 <= x < self.w and 0 <= y < self.h else None

    def flat(self, S, col):
        for x, y in S:
            self.px(x, y, col)

    # --- заливка с тенью и бликом ---
    def paint(self, S, base, shade=True, hi=True, rim=True, strength=1.0, hi_col=None):
        if not S:
            return
        xs = [p[0] for p in S]
        ys = [p[1] for p in S]
        x0, x1, y0, y1 = min(xs), max(xs) + 1, min(ys), max(ys) + 1
        cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
        rx, ry = max(1.0, (x1 - x0) / 2.0), max(1.0, (y1 - y0) / 2.0)
        dk, lt = dark(base, 0.34 * strength), (hi_col or light(base))
        small = (x1 - x0) * (y1 - y0) < 20
        for (x, y) in S:
            col = base
            if shade and not small:
                u, v = (x + 0.5 - cx) / rx, (y + 0.5 - cy) / ry
                s = -0.62 * u - 0.78 * v          # свет сверху-слева
                if s < -0.46:
                    col = dk
                elif hi and s > 0.78 and u * u + v * v < 0.95:
                    col = lt
                if rim and (x, y + 1) not in S and col == base:
                    col = dk
            self.px(x, y, col)

    # --- примитивы ---
    def E(self, cx, cy, rx, ry, col, **kw):
        self.paint(ell_set(cx, cy, rx, ry), col, **kw)

    def R(self, x, y, w, h, col, **kw):
        self.paint(rect_set(x, y, w, h), col, **kw)

    def P(self, pts, col, **kw):
        self.paint(poly_set(pts), col, **kw)

    def L(self, x0, y0, x1, y1, col, w=1):
        self.flat(line_set(x0, y0, x1, y1, w), col)

    def dot(self, x, y, col):
        self.px(x, y, col)

    def shadow(self, cx, cy, rx, ry, alpha=84):
        self.flat(ell_set(cx, cy, rx, ry), (12, 4, 16, alpha))

    def blit(self, other, ox, oy):
        for y in range(other.h):
            for x in range(other.w):
                q = other.p[y][x]
                if q:
                    self.px(x + ox, y + oy, q)

    def copy(self):
        c = Canvas(self.w, self.h)
        c.p = [row[:] for row in self.p]
        return c

    def flipped(self):
        c = Canvas(self.w, self.h)
        c.p = [row[::-1] for row in self.p]
        return c

    # --- глаза ---
    def eye(self, cx, cy, rx=2.5, ry=3.0, look=(0, 0), iris=(20, 10, 16), white=(250, 246, 240), shine=True):
        self.E(cx, cy, rx, ry, white, shade=False)
        px_, py_ = cx + look[0], cy + look[1]
        self.E(px_, py_ + 0.5, max(1.0, rx * 0.62), max(1.0, ry * 0.62), iris, shade=False)
        if shine:
            self.px(int(px_ - 0.5), int(py_ - 0.5), (255, 255, 255))

    # --- контур ---
    def outlined(self, col=OUT, diag=False):
        out = Canvas(self.w + 2, self.h + 2)
        for y in range(self.h):
            for x in range(self.w):
                out.p[y + 1][x + 1] = self.p[y][x]

        def solid(x, y):
            q = out.get(x, y)
            return q is not None and q[3] >= 200

        nb = ((1, 0), (-1, 0), (0, 1), (0, -1)) + (((1, 1), (-1, 1), (1, -1), (-1, -1)) if diag else ())
        mark = []
        for y in range(out.h):
            for x in range(out.w):
                if not solid(x, y) and any(solid(x + dx, y + dy) for dx, dy in nb):
                    mark.append((x, y))
        for x, y in mark:
            out.p[y][x] = (col[0], col[1], col[2], 255)
        return out

    # --- вывод ---
    def to_surface(self):
        import pygame
        buf = bytearray(self.w * self.h * 4)
        i = 0
        for row in self.p:
            for q in row:
                if q:
                    buf[i:i + 4] = bytes(q)
                i += 4
        return pygame.image.frombuffer(bytes(buf), (self.w, self.h), "RGBA").copy()

    def to_pil(self):
        from PIL import Image
        im = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))
        for y in range(self.h):
            for x in range(self.w):
                if self.p[y][x]:
                    im.putpixel((x, y), self.p[y][x])
        return im


def preview(rows, path, scale=6, bg=(70, 62, 78), pad=6):
    """rows — список списков Canvas (или одиночных); сохраняет лист для проверки глазами."""
    from PIL import Image
    rows = [r if isinstance(r, (list, tuple)) else [r] for r in rows]
    W = max(sum(c.w for c in r) + pad * (len(r) + 1) for r in rows)
    H = sum(max(c.h for c in r) + pad for r in rows) + pad
    sheet = Image.new("RGBA", (W, H), bg + (255,))
    y = pad
    for r in rows:
        x = pad
        for c in r:
            sheet.alpha_composite(c.to_pil(), (x, y))
            x += c.w + pad
        y += max(c.h for c in r) + pad
    sheet = sheet.resize((W * scale, H * scale), Image.NEAREST)
    sheet.save(path)
