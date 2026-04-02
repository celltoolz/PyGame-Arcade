import pygame as pg
from .settings import DOOM_DIR


class Sound:
    def __init__(self, game):
        self.game = game
        pg.mixer.init()
        path = DOOM_DIR / 'resources/sound'
        self.shotgun    = pg.mixer.Sound(str(path / 'shotgun.wav'))
        self.npc_pain   = pg.mixer.Sound(str(path / 'npc_pain.wav'))
        self.npc_death  = pg.mixer.Sound(str(path / 'npc_death.wav'))
        self.npc_shot   = pg.mixer.Sound(str(path / 'npc_attack.wav'))
        self.npc_shot.set_volume(0.2)
        self.player_pain = pg.mixer.Sound(str(path / 'player_pain.wav'))
        pg.mixer.music.load(str(path / 'theme.mp3'))
        pg.mixer.music.set_volume(0.3)
