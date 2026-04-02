import pygame

from core.screen import SM

# ══════════════════════════════════════════════════════════════════
#  DOOM  —  import wrapper around doom/ package
# ══════════════════════════════════════════════════════════════════


class DoomApp:
    """
    Launches the Doom raycaster from the doom/ package.
    doom/ sits alongside arcade.py so Python finds it automatically —
    no sys.path manipulation or os.chdir needed.
    """

    def run(self):
        result = "menu"
        try:
            import os
            import doom.main as doom_main
            import doom.settings as doom_settings

            # ── Patched Game subclass ──────────────────────────────
            class DoomArcadeGame(doom_main.Game):
                """
                Skips pg.init() (already done by the arcade) and
                replaces sys.exit() with a clean return value.
                """

                def __init__(self):
                    pygame.mouse.set_visible(False)
                    self._fullscreen = bool(
                        pygame.display.get_surface().get_flags() & pygame.FULLSCREEN
                    )
                    flags = pygame.FULLSCREEN if self._fullscreen else 0
                    if not self._fullscreen:
                        sw, sh = pygame.display.get_desktop_sizes()[0]
                        cx = (sw - doom_settings.WIDTH)  // 2
                        cy = (sh - doom_settings.HEIGHT) // 2
                        os.environ["SDL_VIDEO_WINDOW_POS"] = f"{cx},{cy}"
                    self.screen = pygame.display.set_mode(doom_settings.RES, flags)
                    if not self._fullscreen:
                        from pygame._sdl2 import Window
                        Window.from_display_module().position = (cx, cy)
                    pygame.event.set_grab(True)
                    self.clock = pygame.time.Clock()
                    self.delta_time = 1
                    self.global_trigger = False
                    self.global_event = pygame.USEREVENT + 0
                    pygame.time.set_timer(self.global_event, 40)
                    self._exit_result = None
                    self.new_game()

                def check_events(self):
                    self.global_trigger = False
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            self._exit_result = "quit"
                            return
                        if event.type == pygame.KEYDOWN:
                            if event.key == pygame.K_ESCAPE:
                                self._exit_result = "menu"
                                return
                            if event.key in (pygame.K_F11, pygame.K_f):
                                self._fullscreen = not self._fullscreen
                                SM.fullscreen = self._fullscreen
                                flags = pygame.FULLSCREEN if self._fullscreen else 0
                                self.screen = pygame.display.set_mode(
                                    doom_settings.RES, flags
                                )
                                self.object_renderer.screen = self.screen
                        if event.type == self.global_event:
                            self.global_trigger = True
                        self.player.single_fire_event(event)

                def run_arcade(self):
                    pygame.event.clear()
                    while self._exit_result is None:
                        self.check_events()
                        if self._exit_result is not None:
                            break
                        self.update()
                        self.draw()
                    return self._exit_result

            SM.set_title("DOOM")
            game = DoomArcadeGame()
            result = game.run_arcade()

        except Exception as e:
            self._error_screen(str(e))

        finally:
            try:
                pygame.time.set_timer(game.global_event, 0)
            except Exception:
                pass
            pygame.mixer.music.stop()
            pygame.event.set_grab(False)
            pygame.mouse.set_visible(True)
            flags = pygame.FULLSCREEN if SM.fullscreen else 0
            SM.screen = pygame.display.set_mode((SM.win_w, SM.win_h), flags)
            SM.set_title("Arcade  —  Select a Game")

        return result

    def _error_screen(self, msg):
        surf = SM.screen
        fam = next(
            (
                c
                for c in ["segoeui", "helvetica", "freesans"]
                if pygame.font.match_font(c)
            ),
            None,
        )
        fnt = pygame.font.SysFont(fam, 20) if fam else pygame.font.Font(None, 20)
        surf.fill((10, 5, 5))
        W, H = surf.get_size()
        for text, col, dy in [
            ("Could not launch Doom:", (220, 80, 80), -50),
            (str(msg)[:80], (180, 180, 180), -15),
            ("Press any key to return.", (120, 120, 120), 30),
        ]:
            t = fnt.render(text, True, col)
            surf.blit(t, (W // 2 - t.get_width() // 2, H // 2 + dy))
        pygame.display.flip()
        waiting = True
        while waiting:
            for event in pygame.event.get():
                if event.type in (pygame.QUIT, pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                    waiting = False
