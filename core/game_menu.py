import pygame
from .screen import SM
from .drawing import lerp_color

# ══════════════════════════════════════════════════════════════════
#  GAME MENU  —  reusable pre-game menu
# ══════════════════════════════════════════════════════════════════

class GameMenu:
    """
    Generic pre-game menu. Configure with a title, subtitle, and list of
    MenuItem dicts:  {'label': str, 'sub': str, 'key': str, 'enabled': bool}

    run() returns the index of the chosen item, or 'back' / 'quit'.
    """

    class MenuItem:
        def __init__(self, label, sub='', key='', enabled=True):
            self.label   = label
            self.sub     = sub
            self.key     = key
            self.enabled = enabled
            self.hover_t = 0.0

        def update(self, dt, hovered):
            speed = 8.0
            target = 1.0 if (hovered and self.enabled) else 0.0
            self.hover_t += (target - self.hover_t) * min(1.0, dt * speed)

    def __init__(self, title, subtitle, items, accent=(120, 100, 255), footer_widgets=None):
        """
        items: list of dicts with keys: label, sub, key, enabled
        footer_widgets: optional list of widgets with handle_event(e), update(mp), draw(surf, font)
        """
        self.title           = title
        self.subtitle        = subtitle
        self.accent          = accent
        self.items           = [self.MenuItem(**i) for i in items]
        self.selected        = next((i for i,it in enumerate(self.items) if it.enabled), 0)
        self._time           = 0.0
        self._footer_widgets = footer_widgets or []
        self._build_fonts()

    def _build_fonts(self):
        sc  = min(SM.win_w / 980, SM.win_h / 700)
        fam = next((c for c in ['segoeui','helvetica','dejavusans','freesans']
                    if pygame.font.match_font(c)), None)
        def F(sz, bold=False):
            return (pygame.font.SysFont(fam, max(10, int(sz*sc)), bold=bold) if fam
                    else pygame.font.Font(None, max(10, int(sz*sc))))
        self.fnt_title = F(40, bold=True)
        self.fnt_sub   = F(16)
        self.fnt_label = F(22, bold=True)
        self.fnt_item  = F(14)
        self.fnt_key   = F(13)

    def run(self):
        """
        Event loop. Returns int index of chosen item, 'back', or 'quit'.
        """
        clock = SM.clock
        while True:
            dt = clock.tick(60) / 1000.0
            self._time += dt
            W, H = SM.screen.get_size()
            mp = pygame.mouse.get_pos()

            # Build item rects for hit-testing
            item_rects = self._item_rects(W, H)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return 'quit'
                if event.type == pygame.VIDEORESIZE and not SM.fullscreen:
                    SM.on_resize(event.w, event.h)
                    self._build_fonts()

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_F11:
                        SM.toggle_fs()
                        self._build_fonts()
                    elif event.key == pygame.K_ESCAPE:
                        return 'back'
                    elif event.key in (pygame.K_UP, pygame.K_w):
                        self._move_selection(-1)
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        self._move_selection(1)
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        if self.items[self.selected].enabled:
                            return self.selected

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for i, r in enumerate(item_rects):
                        if r.collidepoint(mp) and self.items[i].enabled:
                            if self.selected == i:
                                return i
                            self.selected = i

                for w in self._footer_widgets:
                    w.handle_event(event)

            # Update hover animations
            for i, (item, r) in enumerate(zip(self.items, item_rects)):
                item.update(dt, r.collidepoint(mp) or i == self.selected)

            for w in self._footer_widgets:
                w.update(mp)

            self._draw(W, H, item_rects)

    def _move_selection(self, direction):
        n = len(self.items)
        idx = self.selected
        for _ in range(n):
            idx = (idx + direction) % n
            if self.items[idx].enabled:
                self.selected = idx
                return

    def _item_rects(self, W, H):
        """Calculate item card rects centred on screen."""
        item_h = max(70, int(H * 0.12))
        item_w = min(420, int(W * 0.52))
        gap    = max(10, int(H * 0.015))
        total  = len(self.items) * (item_h + gap) - gap
        # Push items below title area
        top    = H // 2 - total // 2 + int(H * 0.06)
        x      = W // 2 - item_w // 2
        rects  = []
        for i in range(len(self.items)):
            rects.append(pygame.Rect(x, top + i * (item_h + gap), item_w, item_h))
        return rects

    def _draw(self, W, H, item_rects):
        surf = SM.screen
        surf.fill((8, 10, 18))

        # Grid background
        for x in range(0, W, 40): pygame.draw.line(surf, (13,16,28),(x,0),(x,H))
        for y in range(0, H, 40): pygame.draw.line(surf, (13,16,28),(0,y),(W,y))

        # Accent glow behind title
        glow = pygame.Surface((W, 160), pygame.SRCALPHA)
        for i in range(80):
            a = max(0, 18 - i // 4)
            pygame.draw.line(glow, (*self.accent, a), (0, i), (W, i))
        surf.blit(glow, (0, 0))

        # Title
        t = self.fnt_title.render(self.title, True, (230, 235, 255))
        surf.blit(t, (W//2 - t.get_width()//2, int(H * 0.07)))

        # Underline
        uw = t.get_width() + 24
        ux = W//2 - uw//2
        uy = int(H * 0.07) + t.get_height() + 5
        pygame.draw.line(surf, self.accent, (ux, uy), (ux + uw, uy), 2)

        # Subtitle
        s = self.fnt_sub.render(self.subtitle, True, (70, 80, 115))
        surf.blit(s, (W//2 - s.get_width()//2, uy + 10))

        # Menu items
        for i, (item, rect) in enumerate(zip(self.items, item_rects)):
            t_val = item.hover_t
            selected = (i == self.selected)

            # Card background
            if not item.enabled:
                bg = (14, 16, 26)
            elif selected:
                bg = lerp_color((22, 28, 48), (32, 38, 68), t_val)
            else:
                bg = lerp_color((16, 20, 35), (24, 30, 52), t_val)
            pygame.draw.rect(surf, bg, rect, border_radius=14)

            # Accent left bar
            if item.enabled:
                bar_col = lerp_color(
                    (40, 44, 70),
                    self.accent if selected else (80, 90, 140),
                    t_val)
                pygame.draw.rect(surf, bar_col,
                    (rect.x, rect.y + 8, 4, rect.h - 16), border_radius=2)

            # Border
            if selected and item.enabled:
                bc = (*lerp_color((50,55,90), self.accent, t_val), int(180 * t_val + 60))
                bs = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
                pygame.draw.rect(bs, bc, (0,0,rect.w,rect.h), 2, border_radius=14)
                surf.blit(bs, rect.topleft)
            else:
                pygame.draw.rect(surf, (25, 30, 50), rect, 1, border_radius=14)

            # Label
            lbl_col = (60, 68, 95) if not item.enabled else \
                      lerp_color((150, 158, 185), (240, 245, 255), t_val)
            lbl = self.fnt_label.render(item.label, True, lbl_col)
            surf.blit(lbl, (rect.x + 22, rect.centery - lbl.get_height()//2 -
                           (self.fnt_item.get_height()//2 if item.sub else 0)))

            # Sub-label
            if item.sub:
                sub_col = (45, 52, 75) if not item.enabled else (80, 92, 125)
                sub = self.fnt_item.render(item.sub, True, sub_col)
                surf.blit(sub, (rect.x + 22, rect.centery + lbl.get_height()//2 -
                               self.fnt_item.get_height()//2 + 2))

            # Key badge (right side)
            if item.key and item.enabled:
                badge_col = lerp_color((28, 34, 55),
                    lerp_color((40,46,75), self.accent, 0.4), t_val)
                bw2 = max(50, self.fnt_key.size(item.key)[0] + 20)
                br = pygame.Rect(rect.right - bw2 - 14,
                                 rect.centery - 14, bw2, 28)
                pygame.draw.rect(surf, badge_col, br, border_radius=7)
                kt = self.fnt_key.render(item.key, True,
                    lerp_color((90,100,140),(210,220,255), t_val))
                surf.blit(kt, (br.centerx - kt.get_width()//2,
                               br.centery - kt.get_height()//2))

        # Footer widgets (e.g. sliders) — positioned just above the hint line
        for w in self._footer_widgets:
            w.reposition(W // 2 - 160, H - 78, 320, 20)
            w.draw(surf, self.fnt_item)

        # Bottom hint
        hint = self.fnt_item.render(
            "↑↓ navigate   ·   Enter select   ·   Esc back   ·   F11 fullscreen",
            True, (42, 50, 75))
        surf.blit(hint, (W//2 - hint.get_width()//2, H - 30))

        pygame.display.flip()
