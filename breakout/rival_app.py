import math
import pygame

from core.screen import SM
from core.drawing import lerp_color
from core.particles import ParticleSystem
from .game import (
    BreakoutGame,
    BALL_RADIUS,
    BRICK_ROW_COLS,
    BRK_BG,
    POWERUP_COLS,
    POWERUP_LABELS,
    PIERCE_DURATION,
)
from .ai import BreakoutAI

# ══════════════════════════════════════════════════════════════════
#  RIVAL CHALLENGE — split-screen breakout, player vs AI
# ══════════════════════════════════════════════════════════════════

HUD_H = 52
DIVIDER = 6  # px wide centre divider


class RivalApp:
    """
    Split-screen Breakout. Left = player, Right = AI.
    Standard top-wall physics — no top paddle.
    Returns 'menu' or 'quit'.
    """

    def __init__(self, config=None):
        cfg = config or {}
        self.difficulty = cfg.get("difficulty", "medium")
        self._kb_speed = float(cfg.get("kb_speed", 600))
        self.screen = SM.screen
        self.clock = SM.clock
        SM.set_title(f"Breakout  —  Rival Challenge  ({self.difficulty.capitalize()})")
        self._kb_vel = 0.0
        self._using_kb = False
        self._fire_held = False
        self._overlay_t = 0.0
        self._scanline_surf = None
        self._ai = BreakoutAI(self.difficulty)
        self._winner = None  # None / 'player' / 'ai' / 'draw'
        self.p_particles = ParticleSystem()
        self.a_particles = ParticleSystem()
        pygame.mouse.set_visible(not SM.fullscreen)
        self._build_layout()

    # ── layout ───────────────────────────────────────────────────

    def _build_layout(self):
        W, H = SM.screen.get_size()
        self.W, self.H = W, H
        half_w = (W - DIVIDER) // 2
        play_h = H - HUD_H
        self.left_ox = 0  # x origin of left play area on screen
        self.right_ox = half_w + DIVIDER
        self.py = HUD_H
        self.pw = half_w
        self.ph = play_h

        self.pgame = BreakoutGame(
            half_w, play_h, mode="classic", difficulty=self.difficulty
        )
        self.agame = BreakoutGame(
            half_w, play_h, mode="classic", difficulty=self.difficulty
        )
        self._winner = None
        self._overlay_t = 0.0
        self._ai._react_timer = 0.0
        self._scanline_surf = self._make_scanlines(W, H)
        self._build_fonts()

    def _build_fonts(self):
        W, H = self.W, self.H
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
        self.fnt_big = F(46, bold=True)
        self.fnt_mid = F(20, bold=True)
        self.fnt_hint = F(13)
        self.fnt_pu = F(11, bold=True)

    def _make_scanlines(self, W, H):
        s = pygame.Surface((W, H), pygame.SRCALPHA)
        for y in range(0, H, 2):
            pygame.draw.line(s, (0, 0, 0, 24), (0, y), (W, y))
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
                    elif event.key == pygame.K_ESCAPE:
                        pygame.mouse.set_visible(True)
                        return "menu"
                    elif event.key == pygame.K_r:
                        self._restart()
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        if self._winner:
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
                    # DEBUG: number keys jump both boards to a level
                    elif event.unicode.isdigit():
                        lvl = 10 if event.unicode == "0" else int(event.unicode)
                        for g in (self.pgame, self.agame):
                            g.level = lvl
                            g.game_over = False
                            g._reset_level(keep_score=True)
                        self._winner = None
                        self._overlay_t = 0.0
                    # DEBUG: powerup keys — lowercase = player board, uppercase = AI board
                    elif event.unicode.isalpha() and event.unicode in "mwslp":
                        _pu_map = {
                            "m": "multi",
                            "w": "wide",
                            "s": "slow",
                            "l": "laser",
                            "p": "pierce",
                        }
                        self.pgame._apply_powerup(_pu_map[event.unicode], "player")
                    elif event.unicode.isalpha() and event.unicode in "MWSLP":
                        _pu_map = {
                            "M": "multi",
                            "W": "wide",
                            "S": "slow",
                            "L": "laser",
                            "P": "pierce",
                        }
                        self.agame._apply_powerup(_pu_map[event.unicode], "player")

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

            if not self._winner:
                self._update(dt, fire_pressed)
                self._check_winner()

            self._sync_particles()
            self.p_particles.update(dt)
            self.a_particles.update(dt)

            if self._winner:
                self._overlay_t = min(1.0, self._overlay_t + dt * 3.0)

            self._draw()

        return "menu"

    # ── update ───────────────────────────────────────────────────

    def _update(self, dt, fire_pressed):
        pw_eff = self.pgame._eff_paddle_w()
        if self._using_kb:
            target_x = self.pgame.paddle_x + self._kb_vel * dt
        else:
            mx = pygame.mouse.get_pos()[0] - self.left_ox
            target_x = mx - pw_eff * 0.5
        self.pgame.update(dt, target_x, fire=fire_pressed or self._fire_held)
        if self.pgame.level_complete:
            self.pgame.next_level()

        # AI bottom paddle on right side — always runs, auto-advance levels
        self._ai.tick(dt)
        ai_target = self._ai.get_bottom_target(self.agame, dt)
        ai_fire = self._ai.should_fire_laser(self.agame)
        self.agame.update(dt, ai_target, fire=ai_fire)
        if self.agame.level_complete:
            self.agame.next_level()

    def _check_winner(self):
        p_done = self.pgame.game_over or (
            self.pgame.level_complete and self.pgame.level > 10
        )
        a_done = self.agame.game_over or (
            self.agame.level_complete and self.agame.level > 10
        )

        if p_done and a_done:
            if self.pgame.score >= self.agame.score:
                self._winner = "player"
            else:
                self._winner = "ai"
        elif p_done:
            self._winner = "ai"
        elif a_done:
            self._winner = "player"

        # Also handle: player completes all 10 levels first
        if self.pgame.level > 10 and not self.agame.level > 10:
            self._winner = "player"
        elif self.agame.level > 10 and not self.pgame.level > 10:
            self._winner = "ai"

    def _restart(self):
        self._overlay_t = 0.0
        self._kb_vel = 0.0
        self._winner = None
        self._ai._react_timer = 0.0
        self.pgame = BreakoutGame(
            self.pw, self.ph, mode="classic", difficulty=self.difficulty
        )
        self.agame = BreakoutGame(
            self.pw, self.ph, mode="classic", difficulty=self.difficulty
        )
        self.p_particles = ParticleSystem()
        self.a_particles = ParticleSystem()

    # ── draw ─────────────────────────────────────────────────────

    def _sync_particles(self):
        for b in self.pgame.bricks:
            if not b.alive and b.flash_t > 0.18:
                col = BRICK_ROW_COLS[b.row % len(BRICK_ROW_COLS)]
                self.p_particles.burst(
                    self.left_ox + b.x + b.w // 2,
                    self.py + b.y + b.h // 2,
                    col,
                    count=14,
                )
                b.flash_t = 0.0
        for b in self.agame.bricks:
            if not b.alive and b.flash_t > 0.18:
                col = BRICK_ROW_COLS[b.row % len(BRICK_ROW_COLS)]
                self.a_particles.burst(
                    self.right_ox + b.x + b.w // 2,
                    self.py + b.y + b.h // 2,
                    col,
                    count=14,
                )
                b.flash_t = 0.0

    def _draw(self):
        surf = self.screen
        W, H = surf.get_size()
        surf.fill(BRK_BG)

        # Grid lines
        for x in range(0, W, 36):
            pygame.draw.line(surf, (10, 13, 26), (x, 0), (x, H))
        for y in range(0, H, 36):
            pygame.draw.line(surf, (10, 13, 26), (0, y), (W, y))

        # Centre divider — starts below the HUD
        dx = self.left_ox + self.pw
        pygame.draw.rect(surf, (14, 18, 38), (dx, self.py, DIVIDER, H - self.py))
        for i in range(self.py, H, 18):
            pygame.draw.rect(
                surf, (30, 40, 75), (dx + 2, i, DIVIDER - 4, 10), border_radius=2
            )

        # HUD separator line
        pygame.draw.line(surf, (25, 35, 65), (0, self.py), (W, self.py), 1)

        self._draw_hud(surf, W)
        self._draw_side(surf, self.pgame, self.left_ox, player=True)
        self._draw_side(surf, self.agame, self.right_ox, player=False)
        self.p_particles.draw(surf)
        self.a_particles.draw(surf)

        if self._scanline_surf:
            surf.blit(self._scanline_surf, (0, 0))

        if self._overlay_t > 0.05 and self._winner:
            self._draw_overlay(surf, W, H)

        pygame.display.flip()

    # ── HUD ──────────────────────────────────────────────────────

    def _draw_hud(self, surf, W):
        hcy = (HUD_H - self.fnt_hud.get_height()) // 2
        cy = HUD_H // 2
        ball_r = 6
        stride = ball_r * 2 + 5
        p, a = self.pgame, self.agame

        # Left: player score → player lives
        score_t = self.fnt_hud.render(f"{p.score:06d}", True, (0, 210, 255))
        surf.blit(score_t, (14, hcy))
        lx = 14 + score_t.get_width() + 12
        for i in range(p.lives):
            cx = lx + i * stride + ball_r
            gs = pygame.Surface((ball_r * 2 + 8, ball_r * 2 + 8), pygame.SRCALPHA)
            pygame.draw.circle(
                gs, (0, 180, 255, 60), (ball_r + 4, ball_r + 4), ball_r + 3
            )
            surf.blit(gs, (cx - ball_r - 4, cy - ball_r - 4))
            pygame.draw.circle(surf, (0, 210, 255), (cx, cy), ball_r)
            pygame.draw.circle(
                surf, (160, 240, 255), (cx - ball_r // 3, cy - ball_r // 3), ball_r // 3
            )

        # Right: AI lives → AI score
        ai_t = self.fnt_hud.render(f"{a.score:06d}", True, (255, 100, 80))
        surf.blit(ai_t, (W - 14 - ai_t.get_width(), hcy))
        rx = W - 14 - ai_t.get_width() - 12
        for i in range(a.lives):
            cx = rx - i * stride - ball_r
            gs = pygame.Surface((ball_r * 2 + 8, ball_r * 2 + 8), pygame.SRCALPHA)
            pygame.draw.circle(
                gs, (255, 80, 40, 55), (ball_r + 4, ball_r + 4), ball_r + 3
            )
            surf.blit(gs, (cx - ball_r - 4, cy - ball_r - 4))
            pygame.draw.circle(surf, (255, 100, 80), (cx, cy), ball_r)
            pygame.draw.circle(
                surf, (255, 220, 200), (cx - ball_r // 3, cy - ball_r // 3), ball_r // 3
            )

        # Centre: "RIVAL CHALLENGE" with level indicators and powerup pills flanking it
        rc_t = self.fnt_hud.render("RIVAL CHALLENGE", True, (80, 90, 140))
        plvl_t = self.fnt_mid.render(f"LV {p.level}", True, (0, 180, 220))
        alvl_t = self.fnt_mid.render(f"LV {a.level}", True, (220, 80, 60))
        cx = W // 2
        rc_x = cx - rc_t.get_width() // 2
        surf.blit(rc_t, (rc_x, hcy))

        # Level indicators
        plvl_x = rc_x - plvl_t.get_width() - 16
        alvl_x = rc_x + rc_t.get_width() + 16
        surf.blit(plvl_t, (plvl_x, cy - plvl_t.get_height() // 2))
        surf.blit(alvl_t, (alvl_x, cy - alvl_t.get_height() // 2))

        # Player pills — between player LV and "RIVAL CHALLENGE", right-aligned to LV
        pill_w, pill_h, pill_gap = 36, 16, 5
        pill_y = cy - pill_h // 2
        p_icons = []
        if p.wide_t > 0:
            p_icons.append(("wide", p.wide_t, 10.0))
        if p.slow_t > 0:
            p_icons.append(("slow", p.slow_t, 8.0))
        if p.laser_t > 0:
            p_icons.append(("laser", p.laser_t, 12.0))
        if p.pierce_t > 0:
            p_icons.append(("pierce", p.pierce_t, PIERCE_DURATION))
        if p_icons:
            total_w = len(p_icons) * (pill_w + pill_gap) - pill_gap
            ix = plvl_x - total_w - 10
            for kind, t, max_t in p_icons:
                self._draw_pill(surf, ix, pill_y, pill_w, pill_h, kind, t, max_t)
                ix += pill_w + pill_gap

        # AI pills — between "RIVAL CHALLENGE" and AI LV, left-aligned to LV
        a_icons = []
        if a.wide_t > 0:
            a_icons.append(("wide", a.wide_t, 10.0))
        if a.slow_t > 0:
            a_icons.append(("slow", a.slow_t, 8.0))
        if a.laser_t > 0:
            a_icons.append(("laser", a.laser_t, 12.0))
        if a.pierce_t > 0:
            a_icons.append(("pierce", a.pierce_t, PIERCE_DURATION))
        if a_icons:
            ix = alvl_x + alvl_t.get_width() + 10
            for kind, t, max_t in a_icons:
                self._draw_pill(surf, ix, pill_y, pill_w, pill_h, kind, t, max_t)
                ix += pill_w + pill_gap

    # ── single side draw ─────────────────────────────────────────

    def _draw_side(self, surf, game, ox, player):
        py = self.py
        self._draw_bricks(surf, game, ox, py)
        self._draw_powerups(surf, game, ox, py)
        self._draw_laser_shots(surf, game, ox, py)
        self._draw_balls(surf, game, ox, py, ai_side=not player)
        self._draw_paddle(surf, game, ox, py, player)

    def _draw_bricks(self, surf, game, ox, oy):
        for b in game.bricks:
            if not b.alive:
                continue
            x = ox + b.x
            y = oy + b.y
            base_col = BRICK_ROW_COLS[b.row % len(BRICK_ROW_COLS)]

            if b.hp < b.max_hp:
                fade = 1.0 - 0.25 * (b.max_hp - b.hp)
                base_col = tuple(int(v * fade) for v in base_col)

            if b.flash_t > 0:
                draw_col = lerp_color(
                    base_col, (255, 255, 255), (b.flash_t / 0.20) * 0.8
                )
            else:
                draw_col = base_col

            pygame.draw.rect(
                surf, draw_col, (x + 1, y + 1, b.w - 2, b.h - 2), border_radius=3
            )
            hi = tuple(min(255, v + 70) for v in draw_col)
            pygame.draw.line(surf, hi, (x + 3, y + 2), (x + b.w - 4, y + 2))
            shadow = tuple(max(0, v - 60) for v in draw_col)
            pygame.draw.line(
                surf, shadow, (x + 3, y + b.h - 2), (x + b.w - 4, y + b.h - 2)
            )

            # Shimmer on powerup bricks
            if b.has_powerup:
                t = pygame.time.get_ticks() / 1000.0
                phase = (math.sin(t * 2.2 + b.x * 0.05) + 1) * 0.5
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

            if b.max_hp > 1:
                for pip in range(b.hp):
                    pygame.draw.circle(
                        surf,
                        (255, 255, 255),
                        (int(x + b.w - 7 - pip * 7), int(y + b.h // 2)),
                        2,
                    )

    def _draw_powerups(self, surf, game, ox, oy):
        for pu in game.powerups:
            col = POWERUP_COLS[pu.kind]
            lbl = POWERUP_LABELS[pu.kind]
            px = ox + int(pu.x)
            py_ = oy + int(pu.y)
            pw, ph = 28, 18
            r = pygame.Rect(px - pw // 2, py_ - ph // 2, pw, ph)
            gs = pygame.Surface((pw + 10, ph + 10), pygame.SRCALPHA)
            pygame.draw.rect(gs, (*col, 50), (0, 0, pw + 10, ph + 10), border_radius=10)
            surf.blit(gs, (r.x - 5, r.y - 5))
            pygame.draw.rect(
                surf, tuple(int(v * 0.25) for v in col), r, border_radius=9
            )
            pygame.draw.rect(surf, col, r, 2, border_radius=9)
            t = self.fnt_pu.render(lbl, True, (255, 255, 255))
            surf.blit(
                t, (r.centerx - t.get_width() // 2, r.centery - t.get_height() // 2)
            )

    def _draw_laser_shots(self, surf, game, ox, oy):
        for shot in game.laser_shots:
            sx = ox + int(shot.x)
            sy = oy + int(shot.y)
            gs = pygame.Surface((6, 18), pygame.SRCALPHA)
            pygame.draw.rect(gs, (255, 80, 80, 180), (0, 0, 6, 18), border_radius=3)
            surf.blit(gs, (sx - 3, sy - 9))
            pygame.draw.line(surf, (255, 180, 180), (sx, sy - 9), (sx, sy + 9), 2)

    def _draw_balls(self, surf, game, ox, oy, ai_side=False):
        for ball in game.balls:
            core_col = (255, 120, 90) if ai_side else (200, 240, 255)
            glow_col = (255, 60, 40) if ai_side else (0, 180, 255)
            trail_col = (255, 100, 60) if ai_side else (0, 200, 255)

            for ti, (tx, ty) in enumerate(ball.trail):
                frac = (ti + 1) / max(1, len(ball.trail))
                alpha = int(frac * 130)
                r = max(1, int(BALL_RADIUS * frac * 0.8))
                ts = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
                pygame.draw.circle(ts, (*trail_col, alpha), (r + 1, r + 1), r)
                surf.blit(ts, (ox + int(tx) - r - 1, oy + int(ty) - r - 1))

            bx = ox + int(ball.x)
            by = oy + int(ball.y)
            for gi in range(4, 0, -1):
                gr = BALL_RADIUS + gi * 3
                gs = pygame.Surface((gr * 2 + 2, gr * 2 + 2), pygame.SRCALPHA)
                pygame.draw.circle(gs, (*glow_col, 12 * gi), (gr + 1, gr + 1), gr)
                surf.blit(gs, (bx - gr - 1, by - gr - 1))
            pygame.draw.circle(surf, core_col, (bx, by), BALL_RADIUS)
            pygame.draw.circle(
                surf,
                (255, 255, 255),
                (bx - BALL_RADIUS // 3, by - BALL_RADIUS // 3),
                BALL_RADIUS // 3,
            )

    def _draw_paddle(self, surf, game, ox, oy, player):
        px, py, pw, ph = game._paddle_rect()
        sx = ox + int(px)
        sy = oy + int(py)
        spw = int(pw)

        if player:
            col = (0, 180, 255) if game.wide_t <= 0 else (80, 255, 140)
        else:
            col = (255, 100, 80) if game.wide_t <= 0 else (255, 200, 80)
        col_hi = tuple(min(255, v + 70) for v in col)

        gs = pygame.Surface((spw + 20, int(ph) + 14), pygame.SRCALPHA)
        pygame.draw.rect(
            gs, (*col, 40), (0, 0, spw + 20, int(ph) + 14), border_radius=8
        )
        surf.blit(gs, (sx - 10, sy - 4))
        pygame.draw.rect(surf, col, (sx, sy, spw, int(ph)), border_radius=5)
        pygame.draw.line(surf, col_hi, (sx + 4, sy + 2), (sx + spw - 4, sy + 2), 2)

        if game.laser_t > 0:
            for lx in (sx + 4, sx + spw - 4):
                pygame.draw.line(surf, (255, 80, 80), (lx, sy), (lx, sy + int(ph)), 2)

    def _draw_pill(self, surf, x, y, pw, ph, kind, t, max_t):
        col = POWERUP_COLS[kind]
        frac = t / max_t
        r = pygame.Rect(x, y, pw, ph)
        pygame.draw.rect(surf, tuple(int(v * 0.3) for v in col), r, border_radius=8)
        pygame.draw.rect(
            surf, col, pygame.Rect(x, y, int(pw * frac), ph), border_radius=8
        )
        lbl = self.fnt_pu.render(POWERUP_LABELS[kind], True, (255, 255, 255))
        surf.blit(
            lbl, (r.centerx - lbl.get_width() // 2, r.centery - lbl.get_height() // 2)
        )

    # ── overlay ──────────────────────────────────────────────────

    def _draw_overlay(self, surf, W, H):
        alpha = int(self._overlay_t * 170)
        dim = pygame.Surface((W, H), pygame.SRCALPHA)
        dim.fill((0, 0, 0, alpha))
        surf.blit(dim, (0, 0))

        if self._overlay_t < 0.5:
            return

        if self._winner == "player":
            msg, col = "YOU WIN!", (80, 255, 160)
        elif self._winner == "ai":
            msg, col = "AI WINS!", (255, 100, 80)
        else:
            msg, col = "DRAW!", (180, 180, 255)

        t1 = self.fnt_big.render(msg, True, col)
        t2 = self.fnt_mid.render(
            f"You: {self.pgame.score}   AI: {self.agame.score}", True, (180, 220, 255)
        )
        t3 = self.fnt_hint.render(
            "(Space / R) play again   ·   (Esc) menu", True, (80, 100, 150)
        )

        cx = W // 2
        surf.blit(t1, (cx - t1.get_width() // 2, H // 2 - 65))
        surf.blit(t2, (cx - t2.get_width() // 2, H // 2 - 5))
        surf.blit(t3, (cx - t3.get_width() // 2, H // 2 + 34))
