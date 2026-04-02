import math
import pygame

from core.screen import SM
from core.drawing import lerp_color
from core.particles import ParticleSystem
from .game import (
    BreakoutGame,
    BALL_RADIUS,
    PADDLE_H,
    PADDLE_Y_OFF,
    BRICK_ROW_COLS,
    BRK_ACCENT,
    BRK_BG,
    POWERUP_COLS,
    POWERUP_LABELS,
    PIERCE_DURATION,
)
from .ai import BreakoutAI

# ══════════════════════════════════════════════════════════════════
#  BREAKOUT APP
# ══════════════════════════════════════════════════════════════════

HUD_H = 52  # pixels reserved at top for score/lives/level


class BreakoutApp:
    """Breakout — rendering and game loop. Returns 'menu' or 'quit'."""

    def __init__(self, config=None):
        cfg = config or {}
        self.mode = cfg.get("mode", "classic")
        self.difficulty = cfg.get("difficulty", "medium")
        self.watch_ai = cfg.get("watch_ai", False)  # True → AI controls bottom too
        self._kb_speed = float(cfg.get("kb_speed", 600))
        self.screen = SM.screen
        self.clock = SM.clock
        if self.watch_ai:
            label = "Watch AI"
        elif self.mode == "vs_ai":
            label = "Paddle Battle"
        else:
            label = self.mode.capitalize()
        SM.set_title(f"Breakout  —  {label}  ({self.difficulty.capitalize()})")
        self.particles = ParticleSystem()
        self._kb_vel = 0.0
        self._using_kb = False
        self._fire_held = False
        self._overlay_t = 0.0
        self._scanline_surf = None
        # AI instances — top paddle always in vs_ai, bottom only in watch mode
        self._top_ai = BreakoutAI(self.difficulty) if self.mode == "vs_ai" else None
        self._bot_ai = BreakoutAI(self.difficulty) if self.watch_ai else None
        pygame.mouse.set_visible(not SM.fullscreen)
        self._build_layout()

    # ── layout ───────────────────────────────────────────────────

    def _build_layout(self):
        W, H = SM.screen.get_size()
        self.px = 0
        self.py = HUD_H
        self.pw = W
        self.ph = H - HUD_H
        self.game = BreakoutGame(
            self.pw, self.ph, mode=self.mode, difficulty=self.difficulty
        )
        self._overlay_t = 0.0
        self._scanline_surf = self._make_scanlines(W, H)
        self._build_fonts()
        # Re-seed AI timers after layout rebuild
        if self._top_ai:
            self._top_ai._react_timer = 0.0
        if self._bot_ai:
            self._bot_ai._react_timer = 0.0

    def _build_fonts(self):
        W, H = SM.screen.get_size()
        sc = min(W / 980, H / 700)
        fam = next(
            (
                c
                for c in ["segoeui", "helvetica", "dejavusans", "freesans"]
                if pygame.font.match_font(c)
            ),
            None,
        )

        def F(sz, bold=False):
            return (
                pygame.font.SysFont(fam, max(10, int(sz * sc)), bold=bold)
                if fam
                else pygame.font.Font(None, max(10, int(sz * sc)))
            )

        self.fnt_hud = F(20, bold=True)
        self.fnt_big = F(52, bold=True)
        self.fnt_mid = F(22, bold=True)
        self.fnt_hint = F(14)
        self.fnt_pu = F(11, bold=True)

    def _make_scanlines(self, W, H):
        s = pygame.Surface((W, H), pygame.SRCALPHA)
        for y in range(0, H, 2):
            pygame.draw.line(s, (0, 0, 0, 28), (0, y), (W, y))
        return s

    # ── run loop ─────────────────────────────────────────────────

    def run(self):
        while True:
            dt = min(self.clock.tick(60) / 1000.0, 0.05)
            self.screen = SM.screen
            W, H = self.screen.get_size()

            fire_pressed = False
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.mouse.set_visible(True)
                    return "quit"
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_F11:
                        SM.toggle_fs()
                        pygame.mouse.set_visible(not SM.fullscreen)
                        self._build_layout()
                        self._build_fonts()
                    elif event.key == pygame.K_ESCAPE:
                        pygame.mouse.set_visible(True)
                        return "menu"
                    elif event.key == pygame.K_r:
                        self._restart()
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        if self.game.level_complete:
                            self.game.next_level()
                            self._overlay_t = 0.0
                        elif self.game.game_over:
                            self._restart()
                    elif event.key in (pygame.K_LEFT, pygame.K_a):
                        self._using_kb = True
                        self._kb_vel = -self._kb_speed
                    elif event.key in (pygame.K_RIGHT, pygame.K_d):
                        self._using_kb = True
                        self._kb_vel = self._kb_speed
                    elif event.key in (
                        pygame.K_LCTRL,
                        pygame.K_RCTRL,
                        pygame.K_z,
                        pygame.K_LSHIFT,
                    ):
                        fire_pressed = True
                        self._fire_held = True
                    # DEBUG: number keys jump to a level
                    elif event.unicode.isdigit():
                        lvl = 10 if event.unicode == "0" else int(event.unicode)
                        self.game.level = lvl
                        self.game.game_over = False
                        self.game._reset_level(keep_score=True)
                        self._overlay_t = 0.0
                    # DEBUG: powerup keys — lowercase = player, uppercase = AI
                    elif event.unicode.isalpha() and event.unicode in "mwslp":
                        _pu_map = {
                            "m": "multi",
                            "w": "wide",
                            "s": "slow",
                            "l": "laser",
                            "p": "pierce",
                        }
                        self.game._apply_powerup(_pu_map[event.unicode], "player")
                    elif (
                        event.unicode.isalpha()
                        and event.unicode in "MWSLP"
                        and self.game.has_top_paddle
                    ):
                        _pu_map = {
                            "M": "multi",
                            "W": "wide",
                            "S": "slow",
                            "L": "laser",
                            "P": "pierce",
                        }
                        self.game._apply_powerup(_pu_map[event.unicode], "ai")

                if event.type == pygame.KEYUP:
                    if event.key in (
                        pygame.K_LEFT,
                        pygame.K_a,
                        pygame.K_RIGHT,
                        pygame.K_d,
                    ):
                        self._kb_vel = 0.0
                    if event.key in (
                        pygame.K_LCTRL,
                        pygame.K_RCTRL,
                        pygame.K_z,
                        pygame.K_LSHIFT,
                    ):
                        self._fire_held = False

                if event.type == pygame.MOUSEMOTION:
                    self._using_kb = False

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    fire_pressed = True

                if event.type == pygame.VIDEORESIZE and not SM.fullscreen:
                    SM.on_resize(event.w, event.h)
                    self._build_layout()
                    self._build_fonts()

            if self._top_ai:
                self._top_ai.tick(dt)
            if self._bot_ai:
                self._bot_ai.tick(dt)

            pw_eff = self.game._eff_paddle_w()
            if self._bot_ai:
                target_x = self._bot_ai.get_bottom_target(self.game, dt)
            elif self._using_kb:
                target_x = self.game.paddle_x + self._kb_vel * dt
            else:
                mx = pygame.mouse.get_pos()[0] - self.px
                target_x = mx - pw_eff * 0.5

            # Top paddle target (vs AI mode)
            top_target_x = None
            top_fire     = False
            if self._top_ai:
                top_target_x = self._top_ai.get_top_target(self.game, dt)
                top_fire     = self._top_ai.should_fire_laser(self.game, top=True)

            self.game.update(
                dt,
                target_x,
                top_target_x=top_target_x,
                fire=fire_pressed or self._fire_held,
                top_fire=top_fire,
            )

            # Particles for brick destruction
            self._sync_particles()

            if self.game.level_complete and self.watch_ai:
                self.game.next_level()
                self._overlay_t = 0.0
            if self.game.game_over or self.game.level_complete:
                self._overlay_t = min(1.0, self._overlay_t + dt * 3.0)

            self.particles.update(dt)
            self._draw(W, H)

        return "menu"

    def _restart(self):
        self._overlay_t = 0.0
        self._kb_vel = 0.0
        self.game = BreakoutGame(
            self.pw, self.ph, mode=self.mode, difficulty=self.difficulty
        )
        self.particles = ParticleSystem()
        if self._top_ai:
            self._top_ai._react_timer = 0.0
        if self._bot_ai:
            self._bot_ai._react_timer = 0.0

    def _sync_particles(self):
        """Emit particles for freshly destroyed bricks."""
        for b in self.game.bricks:
            if not b.alive and b.flash_t > 0.18:
                col = BRICK_ROW_COLS[b.row % len(BRICK_ROW_COLS)]
                self.particles.burst(
                    self.px + b.x + b.w // 2, self.py + b.y + b.h // 2, col, count=14
                )
                b.flash_t = 0.0  # prevent re-emit

    # ── drawing ──────────────────────────────────────────────────

    def _draw(self, W, H):
        surf = self.screen
        surf.fill(BRK_BG)

        # Grid lines
        for x in range(0, W, 36):
            pygame.draw.line(surf, (10, 13, 26), (x, 0), (x, H))
        for y in range(0, H, 36):
            pygame.draw.line(surf, (10, 13, 26), (0, y), (W, y))

        # Play area subtle separator
        pygame.draw.line(surf, (25, 35, 65), (0, self.py), (W, self.py), 1)

        self._draw_hud(surf, W)
        self._draw_bricks(surf)
        self._draw_powerups(surf)
        self._draw_laser_shots(surf)
        self._draw_balls(surf)
        self._draw_paddle(surf)
        if self.game.has_top_paddle:
            self._draw_top_paddle(surf)
        self.particles.draw(surf)

        if self._scanline_surf:
            surf.blit(self._scanline_surf, (0, 0))

        if self._overlay_t > 0.05:
            if self.game.level_complete:
                self._draw_level_complete(surf, W, H)
            elif self.game.game_over:
                self._draw_game_over(surf, W, H)

        pygame.display.flip()

    # ── HUD ──────────────────────────────────────────────────────

    def _draw_hud(self, surf, W):
        g = self.game
        hcy = (HUD_H - self.fnt_hud.get_height()) // 2
        cy = HUD_H // 2
        ball_r = 6
        stride = ball_r * 2 + 5

        if g.has_top_paddle:
            # ── Paddle Battle HUD ────────────────────────────────
            # Left side: player score → player lives (left-to-right)
            score_t = self.fnt_hud.render(f"{g.score:06d}", True, (0, 210, 255))
            surf.blit(score_t, (14, hcy))
            lx = 14 + score_t.get_width() + 12
            for i in range(g.lives):
                cx = lx + i * stride + ball_r
                gs = pygame.Surface((ball_r * 2 + 8, ball_r * 2 + 8), pygame.SRCALPHA)
                pygame.draw.circle(
                    gs, (0, 180, 255, 60), (ball_r + 4, ball_r + 4), ball_r + 3
                )
                surf.blit(gs, (cx - ball_r - 4, cy - ball_r - 4))
                pygame.draw.circle(surf, (0, 210, 255), (cx, cy), ball_r)
                pygame.draw.circle(
                    surf,
                    (160, 240, 255),
                    (cx - ball_r // 3, cy - ball_r // 3),
                    ball_r // 3,
                )

            # Right side: AI lives → AI score (right-to-left)
            ai_t = self.fnt_hud.render(f"{g.ai_score:06d}", True, (255, 100, 80))
            surf.blit(ai_t, (W - 14 - ai_t.get_width(), hcy))
            rx = W - 14 - ai_t.get_width() - 12
            for i in range(g.ai_lives):
                cx = rx - i * stride - ball_r
                gs = pygame.Surface((ball_r * 2 + 8, ball_r * 2 + 8), pygame.SRCALPHA)
                pygame.draw.circle(
                    gs, (255, 80, 40, 55), (ball_r + 4, ball_r + 4), ball_r + 3
                )
                surf.blit(gs, (cx - ball_r - 4, cy - ball_r - 4))
                pygame.draw.circle(surf, (255, 100, 80), (cx, cy), ball_r)
                pygame.draw.circle(
                    surf,
                    (255, 220, 200),
                    (cx - ball_r // 3, cy - ball_r // 3),
                    ball_r // 3,
                )

            # Centre: level label
            lvl_t = self.fnt_hud.render(f"LEVEL  {g.level}", True, (180, 180, 255))
            lvl_cx = W // 2
            lvl_hw = lvl_t.get_width() // 2
            surf.blit(lvl_t, (lvl_cx - lvl_hw, hcy))

            # Pills: player left of level, AI right of level
            pill_w, pill_h = 40, 18
            pill_gap = 6
            pill_y = (HUD_H - pill_h) // 2

            p_icons = []
            if g.wide_t > 0:
                p_icons.append(("wide", g.wide_t, 10.0))
            if g.slow_t > 0:
                p_icons.append(("slow", g.slow_t, 8.0))
            if g.laser_t > 0:
                p_icons.append(("laser", g.laser_t, 12.0))
            if g.pierce_t > 0:
                p_icons.append(("pierce", g.pierce_t, PIERCE_DURATION))
            if p_icons:
                total_w = len(p_icons) * (pill_w + pill_gap) - pill_gap
                ix = lvl_cx - lvl_hw - 16 - total_w
                for kind, t, max_t in p_icons:
                    self._draw_pill(surf, ix, pill_y, pill_w, pill_h, kind, t, max_t)
                    ix += pill_w + pill_gap

            ai_icons = []
            if g.top_wide_t  > 0: ai_icons.append(("wide",   g.top_wide_t,   10.0))
            if g.ai_slow_t   > 0: ai_icons.append(("slow",   g.ai_slow_t,     8.0))
            if g.ai_laser_t  > 0: ai_icons.append(("laser",  g.ai_laser_t,   12.0))
            if g.ai_pierce_t > 0: ai_icons.append(("pierce", g.ai_pierce_t, PIERCE_DURATION))
            if ai_icons:
                ix = lvl_cx + lvl_hw + 16
                for kind, t, max_t in ai_icons:
                    self._draw_pill(surf, ix, pill_y, pill_w, pill_h, kind, t, max_t)
                    ix += pill_w + pill_gap

        else:
            # ── Classic / Endless / Watch AI HUD ─────────────────
            score_t = self.fnt_hud.render(f"SCORE  {g.score:06d}", True, (0, 210, 255))
            surf.blit(score_t, (14, hcy))

            lvl_t = self.fnt_hud.render(f"LEVEL  {g.level}", True, (180, 180, 255))
            lvl_cx = W // 2
            lvl_hw = lvl_t.get_width() // 2
            surf.blit(lvl_t, (lvl_cx - lvl_hw, hcy))

            # Lives (right)
            lives_x = W - 14
            for i in range(g.lives):
                cx = lives_x - i * stride - ball_r
                gs = pygame.Surface((ball_r * 2 + 8, ball_r * 2 + 8), pygame.SRCALPHA)
                pygame.draw.circle(
                    gs, (0, 180, 255, 60), (ball_r + 4, ball_r + 4), ball_r + 3
                )
                surf.blit(gs, (cx - ball_r - 4, cy - ball_r - 4))
                pygame.draw.circle(surf, (0, 210, 255), (cx, cy), ball_r)
                pygame.draw.circle(
                    surf,
                    (160, 240, 255),
                    (cx - ball_r // 3, cy - ball_r // 3),
                    ball_r // 3,
                )

            # Powerup timers — right of level label
            pill_w, pill_h = 40, 18
            pill_gap = 6
            p_icons = []
            if g.wide_t > 0:
                p_icons.append(("wide", g.wide_t, 10.0))
            if g.slow_t > 0:
                p_icons.append(("slow", g.slow_t, 8.0))
            if g.laser_t > 0:
                p_icons.append(("laser", g.laser_t, 12.0))
            if g.pierce_t > 0:
                p_icons.append(("pierce", g.pierce_t, PIERCE_DURATION))
            if p_icons:
                ix = lvl_cx + lvl_hw + 20
                for kind, t, max_t in p_icons:
                    self._draw_pill(
                        surf, ix, (HUD_H - pill_h) // 2, pill_w, pill_h, kind, t, max_t
                    )
                    ix += pill_w + pill_gap

    def _draw_pill(self, surf, x, y, pw, ph, kind, t, max_t):
        col = POWERUP_COLS[kind]
        frac = t / max_t
        pill_r = pygame.Rect(x, y, pw, ph)
        pygame.draw.rect(
            surf, tuple(int(v * 0.3) for v in col), pill_r, border_radius=9
        )
        bar_r = pygame.Rect(x, y, int(pw * frac), ph)
        pygame.draw.rect(surf, col, bar_r, border_radius=9)
        lbl = self.fnt_pu.render(POWERUP_LABELS[kind], True, (255, 255, 255))
        surf.blit(
            lbl,
            (
                pill_r.centerx - lbl.get_width() // 2,
                pill_r.centery - lbl.get_height() // 2,
            ),
        )

    # ── bricks ───────────────────────────────────────────────────

    def _draw_bricks(self, surf):
        for b in self.game.bricks:
            if not b.alive:
                continue
            x = self.px + b.x
            y = self.py + b.y
            base_col = BRICK_ROW_COLS[b.row % len(BRICK_ROW_COLS)]

            # Darken multi-hit bricks slightly so HP still reads visually
            if b.hp < b.max_hp:
                fade = 1.0 - 0.25 * (b.max_hp - b.hp)
                base_col = tuple(int(v * fade) for v in base_col)

            if b.flash_t > 0:
                flash_frac = b.flash_t / 0.20
                draw_col = lerp_color(base_col, (255, 255, 255), flash_frac * 0.8)
            else:
                draw_col = base_col

            # Body
            pygame.draw.rect(
                surf, draw_col, (x + 1, y + 1, b.w - 2, b.h - 2), border_radius=3
            )

            # Rim highlight (top edge)
            hi = tuple(min(255, v + 70) for v in draw_col)
            pygame.draw.line(surf, hi, (x + 3, y + 2), (x + b.w - 4, y + 2))

            # Dark bottom edge
            shadow = tuple(max(0, v - 60) for v in draw_col)
            pygame.draw.line(
                surf, shadow, (x + 3, y + b.h - 2), (x + b.w - 4, y + b.h - 2)
            )

            # Powerup shimmer — stripe bouncing left to right
            if b.has_powerup:
                t = pygame.time.get_ticks() / 1000.0
                phase = (
                    math.sin(t * 2.2 + b.x * 0.05) + 1
                ) * 0.5  # 0..1, staggered per column
                sw = int(b.w * 0.35)
                sx = x + int((b.w - sw) * phase)
                sx = max(x, min(sx, x + b.w))
                clip_w = min(sw, x + b.w - sx)
                if clip_w > 0:
                    shimmer = pygame.Surface((clip_w, b.h - 2), pygame.SRCALPHA)
                    for si in range(clip_w):
                        edge = min(si, clip_w - 1 - si)
                        alpha = int(min(edge / max(sw * 0.3, 1), 1.0) * 80)
                        pygame.draw.line(
                            shimmer, (255, 255, 255, alpha), (si, 0), (si, b.h - 2)
                        )
                    surf.blit(shimmer, (sx, y + 1))

            # HP pip dots for multi-hit bricks
            if b.max_hp > 1:
                for pip in range(b.hp):
                    px_pip = x + b.w - 7 - pip * 7
                    py_pip = y + b.h // 2
                    pygame.draw.circle(surf, (255, 255, 255), (px_pip, py_pip), 2)

    # ── powerups ─────────────────────────────────────────────────

    def _draw_powerups(self, surf):
        for pu in self.game.powerups:
            col = POWERUP_COLS[pu.kind]
            lbl = POWERUP_LABELS[pu.kind]
            px = self.px + int(pu.x)
            py_ = self.py + int(pu.y)
            pw, ph = 28, 18
            r = pygame.Rect(px - pw // 2, py_ - ph // 2, pw, ph)
            # Glow
            gs = pygame.Surface((pw + 10, ph + 10), pygame.SRCALPHA)
            pygame.draw.rect(gs, (*col, 50), (0, 0, pw + 10, ph + 10), border_radius=10)
            surf.blit(gs, (r.x - 5, r.y - 5))
            # Pill
            pygame.draw.rect(
                surf, tuple(int(v * 0.25) for v in col), r, border_radius=9
            )
            pygame.draw.rect(surf, col, r, 2, border_radius=9)
            t = self.fnt_pu.render(lbl, True, (255, 255, 255))
            surf.blit(
                t, (r.centerx - t.get_width() // 2, r.centery - t.get_height() // 2)
            )

    # ── laser shots ──────────────────────────────────────────────

    def _draw_laser_shots(self, surf):
        for shot in self.game.laser_shots:
            sx = self.px + int(shot.x)
            sy = self.py + int(shot.y)
            col = (255, 160, 60) if shot.owner == "ai" else (255, 80, 80)
            hi = (255, 220, 160) if shot.owner == "ai" else (255, 180, 180)
            gs = pygame.Surface((6, 18), pygame.SRCALPHA)
            pygame.draw.rect(gs, (*col, 180), (0, 0, 6, 18), border_radius=3)
            surf.blit(gs, (sx - 3, sy - 9))
            pygame.draw.line(surf, hi, (sx, sy - 9), (sx, sy + 9), 2)

    # ── balls ─────────────────────────────────────────────────────

    def _draw_balls(self, surf):
        for ball in self.game.balls:
            is_ai = ball.owner == "ai"
            core_col = (255, 120, 90) if is_ai else (200, 240, 255)
            glow_col = (255, 60, 40) if is_ai else (0, 180, 255)
            trail_col = (255, 100, 60) if is_ai else (0, 200, 255)

            # Trail
            for ti, (tx, ty) in enumerate(ball.trail):
                frac = (ti + 1) / len(ball.trail)
                alpha = int(frac * 140)
                r = max(1, int(BALL_RADIUS * frac * 0.8))
                ts = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
                pygame.draw.circle(ts, (*trail_col, alpha), (r + 1, r + 1), r)
                surf.blit(ts, (self.px + int(tx) - r - 1, self.py + int(ty) - r - 1))

            # Glow
            bx = self.px + int(ball.x)
            by = self.py + int(ball.y)
            for gi in range(4, 0, -1):
                gr = BALL_RADIUS + gi * 3
                gs = pygame.Surface((gr * 2 + 2, gr * 2 + 2), pygame.SRCALPHA)
                pygame.draw.circle(gs, (*glow_col, 12 * gi), (gr + 1, gr + 1), gr)
                surf.blit(gs, (bx - gr - 1, by - gr - 1))

            # Core
            pygame.draw.circle(surf, core_col, (bx, by), BALL_RADIUS)
            pygame.draw.circle(
                surf,
                (255, 255, 255),
                (bx - BALL_RADIUS // 3, by - BALL_RADIUS // 3),
                BALL_RADIUS // 3,
            )

    # ── paddle ───────────────────────────────────────────────────

    def _draw_paddle(self, surf):
        px, py, pw, ph = self.game._paddle_rect()
        sx = self.px + int(px)
        sy = self.py + int(py)
        spw = int(pw)

        col_base = (0, 180, 255) if self.game.wide_t <= 0 else (80, 255, 140)
        col_hi = tuple(min(255, v + 70) for v in col_base)

        # Glow under paddle
        gs = pygame.Surface((spw + 20, int(ph) + 14), pygame.SRCALPHA)
        pygame.draw.rect(
            gs, (*col_base, 40), (0, 0, spw + 20, int(ph) + 14), border_radius=8
        )
        surf.blit(gs, (sx - 10, sy - 4))

        # Body
        pygame.draw.rect(surf, col_base, (sx, sy, spw, int(ph)), border_radius=5)
        # Highlight stripe
        pygame.draw.line(surf, col_hi, (sx + 4, sy + 2), (sx + spw - 4, sy + 2), 2)

        # Laser mode indicator
        if self.game.laser_t > 0:
            for lx in (sx + 4, sx + spw - 4):
                pygame.draw.line(surf, (255, 80, 80), (lx, sy), (lx, sy + int(ph)), 2)

    def _draw_top_paddle(self, surf):
        px, py, pw, ph = self.game._top_paddle_rect()
        sx = self.px + int(px)
        sy = self.py + int(py)
        spw = int(pw)
        col = (255, 200, 80) if self.game.top_wide_t > 0 else (255, 100, 80)
        col_hi = tuple(min(255, v + 70) for v in col)

        gs = pygame.Surface((spw + 20, int(ph) + 14), pygame.SRCALPHA)
        pygame.draw.rect(
            gs, (*col, 40), (0, 0, spw + 20, int(ph) + 14), border_radius=8
        )
        surf.blit(gs, (sx - 10, sy - 4))
        pygame.draw.rect(surf, col, (sx, sy, spw, int(ph)), border_radius=5)
        pygame.draw.line(
            surf,
            col_hi,
            (sx + 4, sy + int(ph) - 3),
            (sx + spw - 4, sy + int(ph) - 3),
            2,
        )

    # ── overlays ─────────────────────────────────────────────────

    def _draw_level_complete(self, surf, W, H):
        alpha = int(self._overlay_t * 160)
        dim = pygame.Surface((W, H), pygame.SRCALPHA)
        dim.fill((0, 0, 0, alpha))
        surf.blit(dim, (0, 0))

        if self._overlay_t < 0.5:
            return

        t1 = self.fnt_big.render("LEVEL CLEAR!", True, (0, 255, 180))
        t2 = self.fnt_mid.render(f"Score: {self.game.score}", True, (180, 220, 255))
        t3 = self.fnt_hint.render(
            "(Space / Enter) next level   ·   (Esc) menu", True, (80, 100, 150)
        )

        cx = W // 2
        surf.blit(t1, (cx - t1.get_width() // 2, H // 2 - 70))
        surf.blit(t2, (cx - t2.get_width() // 2, H // 2 - 10))
        surf.blit(t3, (cx - t3.get_width() // 2, H // 2 + 36))

    def _draw_game_over(self, surf, W, H):
        alpha = int(self._overlay_t * 180)
        dim = pygame.Surface((W, H), pygame.SRCALPHA)
        dim.fill((0, 0, 0, alpha))
        surf.blit(dim, (0, 0))

        if self._overlay_t < 0.5:
            return

        g = self.game
        if g.has_top_paddle:
            if g.player_won:
                msg, col = "YOU WIN!", (80, 255, 160)
            else:
                msg, col = "AI WINS!", (255, 100, 80)
            score_line = f"You: {g.score}   AI: {g.ai_score}"
        else:
            if g.player_won or (g.mode == "classic" and g.level > 10):
                msg, col = "YOU WIN!", (80, 255, 160)
            else:
                msg, col = "GAME OVER", (255, 80, 80)
            score_line = f"Final Score: {g.score}"

        t1 = self.fnt_big.render(msg, True, col)
        t2 = self.fnt_mid.render(score_line, True, (180, 220, 255))
        t3 = self.fnt_hint.render("(R) restart   ·   (Esc) menu", True, (80, 100, 150))

        cx = W // 2
        surf.blit(t1, (cx - t1.get_width() // 2, H // 2 - 70))
        surf.blit(t2, (cx - t2.get_width() // 2, H // 2 - 10))
        surf.blit(t3, (cx - t3.get_width() // 2, H // 2 + 36))
