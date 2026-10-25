"""Инвентарь забега: предметы и активный предмет."""


class Inventory:
    def __init__(self):
        self.items = []
        self.active_id = None
        self.active_cd = 0.0

    def has(self, item_id):
        return item_id in self.items

    def add(self, item_def):
        if item_def.id in self.items:
            return False
        self.items.append(item_def.id)
        if item_def.active:
            self.active_id = item_def.id
            self.active_cd = 0.0
        return True

    def tick(self, dt):
        if self.active_cd > 0:
            self.active_cd = max(0.0, self.active_cd - dt)

    def can_use_active(self):
        return self.active_id is not None and self.active_cd <= 0

    def start_cooldown(self, cooldown):
        self.active_cd = cooldown
