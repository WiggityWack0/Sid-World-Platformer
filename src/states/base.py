"""Game state base class."""


class State:
    name = "state"

    def __init__(self, game):
        self.game = game

    def on_enter(self, **kwargs):
        pass

    def on_exit(self):
        pass

    def handle_event(self, event):
        pass

    def update(self):
        pass

    def draw(self, surf):
        pass
