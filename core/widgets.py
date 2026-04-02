import pygame
from .colors import BTN_BG, BTN_HOVER, BTN_BORDER, TEXT_MAIN, TEXT_DIM
from .drawing import draw_rounded_rect, lerp_color

# ──────────────────────────────────────────────
#  BUTTON
# ──────────────────────────────────────────────
class Button:
    def __init__(self, label, x, y, w, h, font, radius=10, bg=None, hover_bg=None):
        self.label    = label
        self.rect     = pygame.Rect(x,y,w,h)
        self.font     = font
        self.radius   = radius
        self.hovered  = False
        self.bg       = bg       if bg       is not None else BTN_BG
        self.hover_bg = hover_bg if hover_bg is not None else BTN_HOVER

    def reposition(self, x, y, w, h):
        self.rect = pygame.Rect(x,y,w,h)

    def draw(self, surf, dimmed=False):
        bg = (28,32,45) if dimmed else (self.hover_bg if self.hovered else self.bg)
        draw_rounded_rect(surf, bg, self.rect, self.radius, 1, BTN_BORDER)
        col = TEXT_DIM if dimmed else TEXT_MAIN
        txt = self.font.render(self.label, True, col)
        surf.blit(txt, txt.get_rect(center=self.rect.center))

    def update(self, pos):
        self.hovered = self.rect.collidepoint(pos)

    def clicked(self, event):
        return (event.type==pygame.MOUSEBUTTONDOWN
                and event.button==1
                and self.rect.collidepoint(event.pos))


class ToggleSwitch:
    """
    An On/Off toggle switch widget.
    Click anywhere on it to flip the state.
    """
    def __init__(self, x, y, w, h, value=True, label="",
                 on_color=(60, 180, 60), off_color=(60, 60, 60)):
        self.rect      = pygame.Rect(x, y, w, h)
        self.value     = value
        self.label     = label
        self.on_color  = on_color
        self.off_color = off_color
        self._anim     = 1.0 if value else 0.0   # 0.0=off, 1.0=on (animated)
        self.hovered   = False

    def reposition(self, x, y, w, h):
        self.rect = pygame.Rect(x, y, w, h)

    def toggle(self):
        self.value = not self.value

    def update(self, pos, dt=0.016):
        self.hovered = self.rect.collidepoint(pos)
        target = 1.0 if self.value else 0.0
        self._anim += (target - self._anim) * min(1.0, dt * 12)

    def handle_event(self, event):
        if (event.type == pygame.MOUSEBUTTONDOWN
                and event.button == 1
                and self.rect.collidepoint(event.pos)):
            self.toggle()
            return True
        return False

    def draw(self, surf, font):
        r   = self.rect
        h   = r.h
        w   = r.w
        t   = self._anim

        # Optional label above
        if self.label:
            lbl = font.render(self.label, True, (200, 210, 240))
            surf.blit(lbl, (r.x, r.y - lbl.get_height() - 6))

        # Track background — interpolate between off/on colours
        track_col = tuple(int(self.off_color[i] + (self.on_color[i] - self.off_color[i]) * t)
                          for i in range(3))
        pygame.draw.rect(surf, (20, 20, 30), r, border_radius=h//2)   # shadow
        track_r = pygame.Rect(r.x, r.y, w, h)
        pygame.draw.rect(surf, track_col, track_r, border_radius=h//2)

        # Slight border
        bs = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(bs, (255,255,255,40), (0,0,w,h), 2, border_radius=h//2)
        surf.blit(bs, r.topleft)

        # Knob
        pad    = 3
        knob_d = h - pad*2
        knob_x = int(r.x + pad + t * (w - knob_d - pad*2))
        knob_y = r.y + pad
        # Knob shadow
        ks = pygame.Surface((knob_d+4, knob_d+4), pygame.SRCALPHA)
        pygame.draw.circle(ks, (0,0,0,60), (knob_d//2+2, knob_d//2+4), knob_d//2)
        surf.blit(ks, (knob_x-2, knob_y-2))
        # Knob body
        knob_col = (240, 240, 240) if self.value else (160, 160, 160)
        pygame.draw.circle(surf, knob_col,
                           (knob_x + knob_d//2, knob_y + knob_d//2), knob_d//2)
        # Knob highlight
        pygame.draw.circle(surf, (255,255,255),
                           (knob_x + knob_d//2 - knob_d//6,
                            knob_y + knob_d//2 - knob_d//6),
                           knob_d//6)

        # "Off" / "On" text inside the track
        fnt_sm = pygame.font.SysFont(None, max(12, h - 6))
        off_t  = fnt_sm.render("Off", True, (200,200,200) if not self.value else (100,100,100))
        on_t   = fnt_sm.render("On",  True, (255,255,255) if self.value     else (100,100,100))
        # Off label on the right, On label on the left
        surf.blit(on_t,  (r.x + w//4 - on_t.get_width()//2,
                          r.centery - on_t.get_height()//2))
        surf.blit(off_t, (r.x + 3*w//4 - off_t.get_width()//2,
                          r.centery - off_t.get_height()//2))


# ──────────────────────────────────────────────
#  SLIDER
# ──────────────────────────────────────────────
class Slider:
    """
    Horizontal slider widget.
    Call layout(W, H) each frame to reposition before drawing.
    """
    def __init__(self, min_val, max_val, value, label='', accent=(0, 210, 255)):
        self.min_val = float(min_val)
        self.max_val = float(max_val)
        self.value   = float(value)
        self.label   = label
        self.accent  = accent
        self.rect    = pygame.Rect(0, 0, 200, 20)
        self._drag   = False
        self.hovered = False

    def reposition(self, x, y, w, h):
        self.rect = pygame.Rect(x, y, w, h)

    def layout(self):
        """Override or call reposition() to place the slider each frame."""
        pass

    @property
    def _frac(self):
        return (self.value - self.min_val) / max(1, self.max_val - self.min_val)

    def _knob_cx(self):
        r   = self.rect
        pad = r.h // 2
        return int(r.x + pad + self._frac * (r.w - pad * 2))

    def _set_from_mouse(self, mx):
        r    = self.rect
        pad  = r.h // 2
        frac = (mx - r.x - pad) / max(1, r.w - pad * 2)
        frac = max(0.0, min(1.0, frac))
        self.value = self.min_val + frac * (self.max_val - self.min_val)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self._drag = True
                self._set_from_mouse(event.pos[0])
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._drag = False
        if event.type == pygame.MOUSEMOTION and self._drag:
            self._set_from_mouse(event.pos[0])

    def update(self, mp):
        self.hovered = self.rect.collidepoint(mp) or self._drag

    def draw(self, surf, font):
        r        = self.rect
        knob_r   = r.h // 2
        track_y  = r.centery
        track_l  = r.x + knob_r
        track_r  = r.x + r.w - knob_r
        knob_cx  = self._knob_cx()

        # Label + current value
        if self.label:
            val_txt = font.render(
                f"{self.label}:  {int(round(self.value))}",
                True, (140, 155, 195))
            surf.blit(val_txt, (r.centerx - val_txt.get_width() // 2,
                                r.y - val_txt.get_height() - 8))

        # Track background
        pygame.draw.line(surf, (28, 34, 55), (track_l, track_y), (track_r, track_y), 4)

        # Filled portion
        if knob_cx > track_l:
            pygame.draw.line(surf, self.accent, (track_l, track_y), (knob_cx, track_y), 4)

        # Knob glow
        gs = pygame.Surface((knob_r * 2 + 10, knob_r * 2 + 10), pygame.SRCALPHA)
        pygame.draw.circle(gs, (*self.accent, 45),
                           (knob_r + 5, knob_r + 5), knob_r + 3)
        surf.blit(gs, (knob_cx - knob_r - 5, track_y - knob_r - 5))

        # Knob body
        knob_col = (240, 245, 255) if self.hovered else (190, 205, 230)
        pygame.draw.circle(surf, knob_col, (knob_cx, track_y), knob_r)
        pygame.draw.circle(surf, (255, 255, 255),
                           (knob_cx - knob_r // 3, track_y - knob_r // 3),
                           max(1, knob_r // 3))
