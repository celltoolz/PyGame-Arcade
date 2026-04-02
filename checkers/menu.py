import pygame

from core.screen import SM
from core.drawing import lerp_color
from core.widgets import ToggleSwitch
from core.game_menu import GameMenu
from .game import (CK_LIGHT, CK_DARK, CK_BORDER, CK_BLACK_COL, CK_RED_COL,
                   CK_BLACK_RIM, CK_RED_RIM, CK_CROWN, CK_RED, CK_BLACK,
                   CK_RED_K, _ck_is_black, _ck_is_king)
from .app import CheckersApp

# ── Checkers box art ──────────────────────────────────────────────

def _art_checkers(surf, rect):
    surf.fill((40, 25, 10))
    size = 8
    cell = min(rect.w, rect.h) // size
    ox   = (rect.w - cell*size) // 2
    oy   = (rect.h - cell*size) // 2
    for r in range(size):
        for c in range(size):
            col = CK_LIGHT if (r+c)%2==0 else CK_DARK
            pygame.draw.rect(surf, col, (ox+c*cell, oy+r*cell, cell, cell))
    pieces = [
        (0,1,CK_RED),(0,3,CK_RED),(0,5,CK_RED),(0,7,CK_RED),
        (1,0,CK_RED),(1,2,CK_RED),(1,6,CK_RED),
        (2,1,CK_RED),(2,5,CK_RED),
        (3,4,CK_RED_K),
        (4,3,CK_BLACK),
        (5,0,CK_BLACK),(5,2,CK_BLACK),(5,6,CK_BLACK),
        (6,1,CK_BLACK),(6,3,CK_BLACK),(6,5,CK_BLACK),(6,7,CK_BLACK),
        (7,0,CK_BLACK),(7,4,CK_BLACK),(7,6,CK_BLACK),
    ]
    radius = cell//2 - 2
    for r, c, p in pieces:
        cx  = ox + c*cell + cell//2
        cy  = oy + r*cell + cell//2
        mc  = CK_BLACK_COL if _ck_is_black(p) else CK_RED_COL
        rim = CK_BLACK_RIM  if _ck_is_black(p) else CK_RED_RIM
        pygame.draw.circle(surf, mc,  (cx, cy), radius)
        pygame.draw.circle(surf, rim, (cx, cy), radius, 2)
        if _ck_is_king(p):
            pygame.draw.circle(surf, CK_CROWN, (cx, cy), radius//2, 2)
    pygame.draw.rect(surf, CK_BORDER, (ox, oy, cell*size, cell*size), 2)
    glow = pygame.Surface((rect.w, 28), pygame.SRCALPHA)
    for i in range(28):
        pygame.draw.line(glow, (180,120,50,max(0,50-i*3)), (0,i), (rect.w,i))
    surf.blit(glow, (0, 0))


# ══════════════════════════════════════════════════════════════════
#  CHECKERS MENU
# ══════════════════════════════════════════════════════════════════

class CheckersMenu:
    MODE_ITEMS = [
        {'label': 'vs Human', 'sub': 'Local two-player',
         'key': 'Enter', 'enabled': True},
        {'label': 'vs AI',    'sub': 'Challenge the computer',
         'key': 'Enter', 'enabled': True},
    ]
    DIFFICULTY_ITEMS = [
        {'label': 'Easy',   'sub': 'Makes mistakes — good for beginners',
         'key': 'Enter', 'enabled': True},
        {'label': 'Medium', 'sub': 'Solid play — a real challenge',
         'key': 'Enter', 'enabled': True},
        {'label': 'Hard',   'sub': 'Deep search — very tough',
         'key': 'Enter', 'enabled': True},
    ]
    DIFFICULTY_KEYS = ['easy', 'medium', 'hard']

    def _settings_screen(self, config):
        """
        Show a settings screen with a Force Jump toggle.
        Returns updated config, 'back', or 'quit'.
        """
        force_jump = config.get('force_jump', True)
        clock = SM.clock

        # Build fonts
        fam = next((c for c in ['segoeui','helvetica','freesans']
                    if pygame.font.match_font(c)), None)
        def F(sz, bold=False):
            return pygame.font.SysFont(fam, sz, bold=bold) if fam \
                   else pygame.font.Font(None, sz)

        fnt_title = F(36, bold=True)
        fnt_sub   = F(16)
        fnt_label = F(18, bold=True)
        fnt_hint  = F(13)
        fnt_btn   = F(16, bold=True)

        # Toggle and Play button — sized/positioned in the loop
        toggle = ToggleSwitch(0, 0, 160, 44, value=force_jump,
                              label="Force Jump",
                              on_color=(60, 160, 60),
                              off_color=(60, 60, 75))
        ACCENT = (180, 100, 40)

        while True:
            dt = clock.tick(60) / 1000.0
            W, H = SM.screen.get_size()
            mp   = pygame.mouse.get_pos()

            # Layout
            cx = W // 2
            title_y  = int(H * 0.10)
            toggle_y = int(H * 0.42)
            toggle_x = cx - 80
            btn_y    = int(H * 0.62)
            btn_w, btn_h = 180, 48
            btn_x    = cx - btn_w // 2

            toggle.reposition(toggle_x, toggle_y, 160, 44)
            toggle.update(mp, dt)

            # Play button rect
            play_rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)
            play_hover = play_rect.collidepoint(mp)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return 'quit'
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_F11:
                        SM.toggle_fs()
                    elif event.key == pygame.K_ESCAPE:
                        return 'back'
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        config['force_jump'] = toggle.value
                        return config
                if toggle.handle_event(event):
                    force_jump = toggle.value
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if play_rect.collidepoint(event.pos):
                        config['force_jump'] = toggle.value
                        return config
                if event.type == pygame.VIDEORESIZE and not SM.fullscreen:
                    SM.on_resize(event.w, event.h)

            # Draw
            surf = SM.screen
            surf.fill((8, 10, 18))
            for x in range(0, W, 40):
                pygame.draw.line(surf, (13,16,28),(x,0),(x,H))
            for y in range(0, H, 40):
                pygame.draw.line(surf, (13,16,28),(0,y),(W,y))

            # Accent glow
            glow = pygame.Surface((W, 160), pygame.SRCALPHA)
            for i in range(80):
                a = max(0, 18 - i//4)
                pygame.draw.line(glow, (*ACCENT, a), (0,i),(W,i))
            surf.blit(glow, (0,0))

            # Title
            t = fnt_title.render("CHECKERS", True, (230,235,255))
            surf.blit(t, (cx - t.get_width()//2, title_y))
            uw = t.get_width() + 24
            ux = cx - uw//2
            uy = title_y + t.get_height() + 5
            pygame.draw.line(surf, ACCENT, (ux,uy),(ux+uw,uy), 2)
            sub = fnt_sub.render("Game settings", True, (70,80,115))
            surf.blit(sub, (cx - sub.get_width()//2, uy+10))

            # Settings card
            card_w, card_h = 320, 180
            card_x = cx - card_w//2
            card_y = int(H * 0.30)
            pygame.draw.rect(surf, (18,22,40),
                (card_x, card_y, card_w, card_h), border_radius=16)
            pygame.draw.rect(surf, (40,50,80),
                (card_x, card_y, card_w, card_h), 1, border_radius=16)

            # Force Jump label + description
            lbl = fnt_label.render("Force Jump", True, (220,225,245))
            surf.blit(lbl, (card_x+24, card_y+22))
            desc_col = (80, 95, 130)
            desc = fnt_hint.render(
                "On: captures are mandatory (standard rules)" if toggle.value
                else "Off: capturing is optional — casual play",
                True, desc_col)
            surf.blit(desc, (card_x+24, card_y+50))

            # Toggle centred in card
            toggle.reposition(card_x + card_w//2 - 80, card_y + 95, 160, 44)
            toggle.draw(surf, fnt_label)

            # Play button
            play_col = lerp_color((30,40,65), ACCENT, 0.7 if play_hover else 0.4)
            pygame.draw.rect(surf, play_col, play_rect, border_radius=12)
            pygame.draw.rect(surf, ACCENT, play_rect, 2, border_radius=12)
            pt = fnt_btn.render("Play", True, (240,245,255))
            surf.blit(pt, (play_rect.centerx - pt.get_width()//2,
                           play_rect.centery - pt.get_height()//2))

            # Hint
            hint = fnt_hint.render(
                "Enter / click Play   ·   Esc back   ·   F11 fullscreen",
                True, (42,50,75))
            surf.blit(hint, (cx - hint.get_width()//2, H - 30))

            pygame.display.flip()

    def run(self):
        mode_menu = GameMenu(
            title="CHECKERS", subtitle="Select a game mode",
            items=self.MODE_ITEMS, accent=(180, 100, 40))
        while True:
            result = mode_menu.run()
            if result in ('quit', 'back'): return result

            config = {'opponent': 'human' if result == 0 else 'ai',
                      'force_jump': True}

            if result == 1:
                diff_menu = GameMenu(
                    title="vs AI", subtitle="Select difficulty",
                    items=self.DIFFICULTY_ITEMS, accent=(180, 100, 40))
                diff_result = diff_menu.run()
                if diff_result == 'quit': return 'quit'
                if diff_result == 'back': continue
                config['difficulty'] = self.DIFFICULTY_KEYS[diff_result]

            # Settings screen with Force Jump toggle
            settings_result = self._settings_screen(config)
            if settings_result == 'quit': return 'quit'
            if settings_result == 'back': continue

            game_result = CheckersApp(settings_result).run()
            if game_result == 'quit': return 'quit'
            SM.set_title("Checkers")
