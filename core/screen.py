import os
import pygame
from .constants import MIN_W, MIN_H

# ──────────────────────────────────────────────
#  SCREEN MANAGER  —  single source of truth
#  for the pygame display and fullscreen state
# ──────────────────────────────────────────────
class ScreenManager:
    """Owns pygame.display so fullscreen state is shared across all games."""
    def __init__(self):
        self.fullscreen = False
        self.win_w      = 980
        self.win_h      = 700
        self.screen     = None
        self.clock      = pygame.time.Clock()

    def init(self):
        self.screen = pygame.display.set_mode(
            (self.win_w, self.win_h), pygame.RESIZABLE)
        return self.screen

    def center(self):
        """Center the window on the primary monitor."""
        try:
            sw, sh = pygame.display.get_desktop_sizes()[0]
            cx = (sw - self.win_w) // 2
            cy = (sh - self.win_h) // 2
            from pygame._sdl2 import Window
            Window.from_display_module().position = (cx, cy)
        except Exception:
            pass

    def set_title(self, title):
        """Set the window caption. Each game calls this on launch."""
        pygame.display.set_caption(title)

    def toggle_fs(self):
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            os.environ['SDL_VIDEO_CENTERED'] = '1'
            self.screen = pygame.display.set_mode(
                (MIN_W, MIN_H), pygame.RESIZABLE)
            os.environ.pop('SDL_VIDEO_CENTERED', None)
            self.win_w, self.win_h = MIN_W, MIN_H
        info = pygame.display.Info()
        self.win_w, self.win_h = info.current_w, info.current_h
        return self.screen

    def on_resize(self, w, h):
        if not self.fullscreen:
            self.win_w = max(MIN_W, w)
            self.win_h = max(MIN_H, h)
            self.screen = pygame.display.set_mode(
                (self.win_w, self.win_h), pygame.RESIZABLE)
        return self.screen

# Global singleton — created once, shared by all classes
SM = ScreenManager()
