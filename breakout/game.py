import math
import random

# ══════════════════════════════════════════════════════════════════
#  BREAKOUT CONSTANTS
# ══════════════════════════════════════════════════════════════════

BRK_COLS      = 12
BRK_ROWS_BASE = 5      # rows on level 1; +1 per level, capped at 12
BRK_H         = 22
BRK_GAP       = 3
BRK_TOP_PAD   = 18     # vertical padding at top of play area

BALL_RADIUS   = 7

PADDLE_H         = 12
PADDLE_Y_OFF     = 48   # paddle top distance from play area bottom
TOP_PADDLE_Y_OFF = 6    # top paddle top distance from play area top

DIFFICULTY = {
    'easy':   {'speed': 210, 'paddle': 0.15},
    'medium': {'speed': 285, 'paddle': 0.10},
    'hard':   {'speed': 360, 'paddle': 0.07},
}

POWERUP_TYPES      = ['multi', 'wide', 'slow', 'laser', 'pierce']
POWERUP_CHANCE     = 0.20
POWERUP_FALL_SPEED = 120

WIDE_DURATION   = 10.0
SLOW_DURATION   = 8.0
LASER_DURATION  = 12.0
PIERCE_DURATION = 10.0
LASER_SPEED     = 700
LASER_COOLDOWN  = 0.30

# Brick colours by row (cycles if more rows than entries)
BRICK_ROW_COLS = [
    (220,  40,  40),   # red
    (220, 120,  30),   # orange
    (210, 190,  30),   # yellow
    ( 60, 190,  60),   # green
    ( 40, 120, 220),   # blue
    (120,  50, 210),   # purple
    ( 30, 200, 210),   # cyan
    (200,  50, 140),   # pink
]

BRK_BG     = (6,  8, 18)
BRK_ACCENT = (0, 210, 255)

# Powerup label colours
POWERUP_COLS = {
    'multi':  (80,  255, 120),
    'wide':   (80,  180, 255),
    'slow':   (180, 100, 255),
    'laser':  (255,  80,  80),
    'pierce': (255, 140,  30),
}
POWERUP_LABELS = {
    'multi':  'M',
    'wide':   'W',
    'slow':   'S',
    'laser':  'L',
    'pierce': 'P',
}


# ══════════════════════════════════════════════════════════════════
#  DATA CLASSES
# ══════════════════════════════════════════════════════════════════

class Brick:
    __slots__ = ('x', 'y', 'w', 'h', 'hp', 'max_hp', 'flash_t', 'alive', 'has_powerup', 'row')

    def __init__(self, x, y, w, h, hp, has_powerup=False, row=0):
        self.x, self.y = x, y
        self.w, self.h = w, h
        self.hp        = hp
        self.max_hp    = hp
        self.flash_t   = 0.0
        self.alive     = True
        self.has_powerup = has_powerup
        self.row       = row


class Ball:
    __slots__ = ('x', 'y', 'vx', 'vy', 'trail', 'alive', 'owner')

    def __init__(self, x, y, vx, vy, owner='player'):
        self.x, self.y   = float(x), float(y)
        self.vx, self.vy = float(vx), float(vy)
        self.trail = []
        self.alive = True
        self.owner = owner


class Powerup:
    __slots__ = ('x', 'y', 'vy', 'kind', 'alive', 'owner')

    def __init__(self, x, y, kind, owner='player'):
        self.x, self.y = float(x), float(y)
        # AI powerups fall upward toward the top paddle
        self.vy    = -float(POWERUP_FALL_SPEED) if owner == 'ai' else float(POWERUP_FALL_SPEED)
        self.kind  = kind
        self.alive = True
        self.owner = owner


class LaserShot:
    __slots__ = ('x', 'y', 'vy', 'alive', 'owner')

    def __init__(self, x, y, owner='player'):
        self.x, self.y = float(x), float(y)
        # Player shots travel upward, AI shots travel downward
        self.vy    = float(LASER_SPEED) if owner == 'ai' else -float(LASER_SPEED)
        self.alive = True
        self.owner = owner


# ══════════════════════════════════════════════════════════════════
#  BREAKOUT GAME  —  pure logic, local coords (origin = play area TL)
# ══════════════════════════════════════════════════════════════════

class BreakoutGame:
    """
    All coordinates are local to the play area (origin at top-left).
    The rendering layer is responsible for offsetting when drawing.
    """

    def __init__(self, play_w, play_h, mode='classic', difficulty='medium'):
        self.play_w     = play_w
        self.play_h     = play_h
        self.mode       = mode
        self.difficulty = difficulty
        cfg = DIFFICULTY[difficulty]
        self._base_speed = cfg['speed']
        self.paddle_w    = max(60, int(play_w * cfg['paddle']))
        self.score       = 0
        self.ai_score    = 0
        self.lives       = 3
        self.ai_lives    = 3 if mode == 'vs_ai' else 0
        self.level       = 1
        self.game_over      = False
        self.level_complete = False
        self.player_won     = False
        self.has_top_paddle = (mode == 'vs_ai')
        self.top_paddle_w   = max(60, int(play_w * DIFFICULTY[difficulty]['paddle']))
        self.top_paddle_x   = 0.0
        self.top_wide_t     = 0.0
        self.ai_slow_t      = 0.0
        self.pierce_t       = 0.0
        self.ai_pierce_t    = 0.0
        self.ai_laser_t     = 0.0
        self._brick_w = (play_w - BRK_GAP * (BRK_COLS + 1)) // BRK_COLS
        self._reset_level(keep_score=False)

    # ── helpers ──────────────────────────────────────────────────

    def _ball_speed(self):
        return self._base_speed + (self.level - 1) * 20

    def _eff_paddle_w(self):
        return self.paddle_w * 2 if self.wide_t > 0 else self.paddle_w

    def _eff_top_paddle_w(self):
        return self.top_paddle_w * 2 if self.top_wide_t > 0 else self.top_paddle_w

    def _paddle_rect(self):
        return (self.paddle_x, float(self.play_h - PADDLE_Y_OFF),
                float(self._eff_paddle_w()), float(PADDLE_H))

    def _top_paddle_rect(self):
        return (self.top_paddle_x, float(TOP_PADDLE_Y_OFF),
                float(self._eff_top_paddle_w()), float(PADDLE_H))

    # ── level setup ──────────────────────────────────────────────

    def _reset_level(self, keep_score=True):
        self.bricks      = self._make_bricks()
        self.balls       = [self._spawn_ball('player')]
        if self.has_top_paddle:
            self.balls.append(self._spawn_ai_ball())
        self.powerups    = []
        self.laser_shots = []
        self.paddle_x    = float(self.play_w // 2 - self.paddle_w // 2)
        self.top_paddle_x = float(self.play_w // 2 - self.top_paddle_w // 2)
        self.wide_t      = 0.0
        self.slow_t      = 0.0
        self.laser_t     = 0.0
        self.top_wide_t  = 0.0
        self.ai_slow_t   = 0.0
        self.pierce_t    = 0.0
        self.ai_pierce_t = 0.0
        self.ai_laser_t  = 0.0
        self._laser_cd   = 0.0
        self._ai_laser_cd = 0.0
        self.level_complete = False
        if not keep_score:
            self.score    = 0
            self.ai_score = 0
            self.ai_lives = 3 if self.has_top_paddle else 0

    def _make_bricks(self):
        rows = min(BRK_ROWS_BASE + self.level - 1, 12)
        bw   = self._brick_w
        bricks = []
        if self.mode == 'vs_ai':
            # Paddle Battle: half-height bricks centred vertically in play area
            brk_h   = BRK_H // 2
            total_h = rows * (brk_h + BRK_GAP) - BRK_GAP
            start_y = (self.play_h - total_h) // 2
        else:
            brk_h   = BRK_H
            start_y = BRK_TOP_PAD
        for r in range(rows):
            for c in range(BRK_COLS):
                x  = BRK_GAP + c * (bw + BRK_GAP)
                y  = start_y + r * (brk_h + BRK_GAP)
                hp = self._brick_hp(r, rows)
                has_pu = random.random() < POWERUP_CHANCE
                bricks.append(Brick(x, y, bw, brk_h, hp, has_powerup=has_pu, row=r))
        return bricks

    def _brick_hp(self, row, total_rows):
        if self.level < 2:
            return 1
        max_hp = min(3, 1 + (self.level - 1) // 2)
        if self.mode == 'vs_ai':
            # Centre rows hardest, edges softest — fair for both paddles
            mid  = (total_rows - 1) / 2.0
            frac = 1.0 - abs(row - mid) / max(1, mid)  # 1.0 at centre, 0.0 at edges
        else:
            frac = 1.0 - row / max(1, total_rows - 1)  # 1.0 at top, 0.0 at bottom
        if frac > 0.66:
            return max_hp
        elif frac > 0.33:
            return max(1, max_hp - 1)
        return 1

    def _spawn_ball(self, owner='player'):
        x     = float(self.play_w // 2)
        y     = float(self.play_h - PADDLE_Y_OFF - PADDLE_H - BALL_RADIUS - 2)
        angle = math.radians(random.uniform(-40, 40) - 90)
        spd   = self._ball_speed()
        return Ball(x, y, spd * math.cos(angle), spd * math.sin(angle), owner=owner)

    def _spawn_ai_ball(self):
        """Spawn an AI-owned red ball near the top paddle heading downward."""
        x     = float(self.play_w // 2)
        y     = float(TOP_PADDLE_Y_OFF + PADDLE_H + BALL_RADIUS + 2)
        angle = math.radians(random.uniform(-40, 40) + 90)   # ~90° = downward
        spd   = self._ball_speed()
        return Ball(x, y, spd * math.cos(angle), spd * math.sin(angle), owner='ai')

    # ── main update ──────────────────────────────────────────────

    def update(self, dt, target_paddle_x, top_target_x=None, fire=False, top_fire=False):
        if self.game_over or self.level_complete:
            return

        self._move_paddle(target_paddle_x)
        if self.has_top_paddle and top_target_x is not None:
            pw = float(self._eff_top_paddle_w())
            self.top_paddle_x = max(0.0, min(float(self.play_w) - pw,
                                             float(top_target_x)))
        self._tick_timers(dt)

        if fire and self.laser_t > 0 and self._laser_cd <= 0:
            self._fire_laser()
        if top_fire and self.has_top_paddle and self.ai_laser_t > 0 and self._ai_laser_cd <= 0:
            self._fire_ai_laser()

        self._update_lasers(dt)

        for ball in self.balls:
            if ball.owner == 'ai':
                mult = 0.60 if self.ai_slow_t > 0 else 1.0
            else:
                mult = 0.60 if self.slow_t > 0 else 1.0
            self._update_ball(ball, dt * mult)
        self.balls = [b for b in self.balls if b.alive]

        self._update_powerups(dt)

        if all(not b.alive for b in self.bricks):
            self.level_complete = True
            return

        if self.has_top_paddle:
            player_balls = [b for b in self.balls if b.owner == 'player']
            ai_balls     = [b for b in self.balls if b.owner == 'ai']
            if not player_balls:
                self.lives -= 1
                if self.lives <= 0:
                    self.game_over  = True
                    self.player_won = False
                else:
                    self.balls.append(self._spawn_ball('player'))
                    self.wide_t  = 0.0
                    self.slow_t  = 0.0
                    self.laser_t = 0.0
                    self.pierce_t    = 0.0
                    self.ai_pierce_t = 0.0
            if not ai_balls and not self.game_over:
                self.ai_lives -= 1
                if self.ai_lives <= 0:
                    self.game_over  = True
                    self.player_won = True
                else:
                    self.balls.append(self._spawn_ai_ball())
                    self.top_wide_t  = 0.0
                    self.ai_slow_t   = 0.0
                    self.ai_laser_t  = 0.0
        else:
            if not self.balls:
                self.lives -= 1
                if self.lives <= 0:
                    self.game_over  = True
                    self.player_won = False
                else:
                    self.balls   = [self._spawn_ball('player')]
                    self.wide_t  = 0.0
                    self.slow_t  = 0.0
                    self.laser_t = 0.0

    def _move_paddle(self, target_x):
        pw = float(self._eff_paddle_w())
        self.paddle_x = max(0.0, min(float(self.play_w) - pw, float(target_x)))

    def _tick_timers(self, dt):
        if self.wide_t     > 0: self.wide_t     = max(0.0, self.wide_t     - dt)
        if self.slow_t     > 0: self.slow_t     = max(0.0, self.slow_t     - dt)
        if self.laser_t    > 0: self.laser_t    = max(0.0, self.laser_t    - dt)
        if self.top_wide_t > 0: self.top_wide_t = max(0.0, self.top_wide_t - dt)
        if self.ai_slow_t   > 0: self.ai_slow_t   = max(0.0, self.ai_slow_t   - dt)
        if self.pierce_t    > 0: self.pierce_t    = max(0.0, self.pierce_t    - dt)
        if self.ai_pierce_t > 0: self.ai_pierce_t = max(0.0, self.ai_pierce_t - dt)
        if self.ai_laser_t  > 0: self.ai_laser_t  = max(0.0, self.ai_laser_t  - dt)
        if self._ai_laser_cd > 0: self._ai_laser_cd = max(0.0, self._ai_laser_cd - dt)
        if self._laser_cd  > 0: self._laser_cd  = max(0.0, self._laser_cd  - dt)
        for b in self.bricks:
            if b.flash_t > 0:
                b.flash_t = max(0.0, b.flash_t - dt)

    def _fire_laser(self):
        px, py, pw, _ = self._paddle_rect()
        self.laser_shots.append(LaserShot(px + pw * 0.25, py, owner='player'))
        self.laser_shots.append(LaserShot(px + pw * 0.75, py, owner='player'))
        self._laser_cd = LASER_COOLDOWN

    def _fire_ai_laser(self):
        px, py, pw, ph = self._top_paddle_rect()
        shot_y = py + ph   # fire from bottom edge of top paddle
        self.laser_shots.append(LaserShot(px + pw * 0.25, shot_y, owner='ai'))
        self.laser_shots.append(LaserShot(px + pw * 0.75, shot_y, owner='ai'))
        self._ai_laser_cd = LASER_COOLDOWN

    def _update_lasers(self, dt):
        for shot in self.laser_shots:
            shot.y += shot.vy * dt
            # Out of bounds
            if shot.y < 0 or shot.y > self.play_h:
                shot.alive = False
                continue
            for b in self.bricks:
                if not b.alive:
                    continue
                if b.x <= shot.x <= b.x + b.w and b.y <= shot.y <= b.y + b.h:
                    shot.alive = False
                    self._hit_brick(b, shot.owner)
                    break
        self.laser_shots = [s for s in self.laser_shots if s.alive]

    def _update_ball(self, ball, dt):
        TRAIL_LEN = 8
        ball.trail.append((ball.x, ball.y))
        if len(ball.trail) > TRAIL_LEN:
            ball.trail.pop(0)

        ball.x += ball.vx * dt
        ball.y += ball.vy * dt

        # Side walls
        if ball.x - BALL_RADIUS < 0:
            ball.x  = float(BALL_RADIUS)
            ball.vx = abs(ball.vx)
        elif ball.x + BALL_RADIUS > self.play_w:
            ball.x  = float(self.play_w - BALL_RADIUS)
            ball.vx = -abs(ball.vx)

        # Top wall / top paddle
        if self.has_top_paddle:
            self._ball_vs_top_paddle(ball)
        if ball.y - BALL_RADIUS < 0:
            if self.has_top_paddle and ball.owner == 'ai':
                ball.alive = False   # AI missed their ball past the top
                return
            ball.y  = float(BALL_RADIUS)
            ball.vy = abs(ball.vy)

        # Bottom — player ball lost; AI ball bounces
        if ball.y + BALL_RADIUS > self.play_h:
            if self.has_top_paddle and ball.owner == 'ai':
                ball.y  = float(self.play_h - BALL_RADIUS)
                ball.vy = -abs(ball.vy)
            else:
                ball.alive = False
                return

        self._ball_vs_paddle(ball)

        for b in self.bricks:
            if b.alive:
                self._ball_vs_brick(ball, b)

    def _ball_vs_paddle(self, ball):
        # In Paddle Battle, AI-owned balls don't interact with the bottom paddle
        if self.has_top_paddle and ball.owner == 'ai':
            return
        px, py, pw, ph = self._paddle_rect()
        if not (ball.vy > 0 and
                px <= ball.x <= px + pw and
                py - BALL_RADIUS <= ball.y + BALL_RADIUS <= py + ph + 4):
            return
        ball.y  = py - float(BALL_RADIUS)
        ball.vy = -abs(ball.vy)
        rel     = (ball.x - (px + pw * 0.5)) / (pw * 0.5)
        speed   = math.hypot(ball.vx, ball.vy)
        angle   = math.radians(-90.0 + rel * 55.0)
        ball.vx = speed * math.cos(angle)
        ball.vy = speed * math.sin(angle)

    def _ball_vs_top_paddle(self, ball):
        # Only AI-owned balls interact with the top paddle
        if ball.owner != 'ai':
            return
        px, py, pw, ph = self._top_paddle_rect()
        if not (ball.vy < 0 and
                px <= ball.x <= px + pw and
                py - 4 <= ball.y - BALL_RADIUS <= py + ph + BALL_RADIUS):
            return
        ball.y  = float(py + ph + BALL_RADIUS)
        rel     = (ball.x - (px + pw * 0.5)) / (pw * 0.5)
        speed   = math.hypot(ball.vx, ball.vy)
        angle   = math.radians(90.0 - rel * 55.0)
        ball.vx = speed * math.cos(angle)
        ball.vy = abs(speed * math.sin(angle))

    def _ball_vs_brick(self, ball, b):
        """Circle vs AABB. Returns True if a hit occurred."""
        nx = max(b.x, min(ball.x, b.x + b.w))
        ny = max(b.y, min(ball.y, b.y + b.h))
        if math.hypot(ball.x - nx, ball.y - ny) >= BALL_RADIUS:
            return False
        if ((ball.owner == 'player' and self.pierce_t > 0) or
                (ball.owner == 'ai' and self.ai_pierce_t > 0)):
            # Pierce mode — ball passes through bricks without bouncing
            self._hit_brick(b, ball.owner)
            return False   # returning False lets the ball keep checking other bricks
        dx = ball.x - (b.x + b.w * 0.5)
        dy = ball.y - (b.y + b.h * 0.5)
        if abs(dx / b.w) > abs(dy / b.h):
            ball.vx = -ball.vx
            ball.x += ball.vx * 0.01
        else:
            ball.vy = -ball.vy
            ball.y += ball.vy * 0.01
        self._hit_brick(b, ball.owner)
        return True

    def _hit_brick(self, b, owner):
        b.hp     -= 1
        b.flash_t = 0.20
        if b.hp <= 0:
            b.alive = False
            pts = b.max_hp * 10
            if self.has_top_paddle and owner == 'ai':
                self.ai_score += pts
            else:
                self.score += pts
            if b.has_powerup:
                self.powerups.append(
                    Powerup(b.x + b.w * 0.5, b.y + b.h,
                            random.choice(POWERUP_TYPES), owner=owner))

    def _update_powerups(self, dt):
        px, py, pw, ph = self._paddle_rect()
        for pu in self.powerups:
            pu.y += pu.vy * dt
            # Fell off screen
            if pu.vy > 0 and pu.y > self.play_h + 20:
                pu.alive = False
                continue
            if pu.vy < 0 and pu.y < -20:
                pu.alive = False
                continue
            # Bottom paddle collection (player powerups falling down)
            if pu.vy > 0:
                if (px <= pu.x <= px + pw and
                        py <= pu.y + 10 <= py + ph + 12):
                    self._apply_powerup(pu.kind, 'player')
                    pu.alive = False
            # Top paddle collection (AI powerups falling up)
            elif pu.vy < 0 and self.has_top_paddle:
                tpx, tpy, tpw, tph = self._top_paddle_rect()
                if (tpx <= pu.x <= tpx + tpw and
                        tpy - 10 <= pu.y <= tpy + tph + 12):
                    self._apply_powerup(pu.kind, 'ai')
                    pu.alive = False
        self.powerups = [p for p in self.powerups if p.alive]

    def _apply_powerup(self, kind, owner='player'):
        if owner == 'player':
            self.score += 50
        else:
            self.ai_score += 50
        if kind == 'multi':
            new = []
            for ball in self.balls:
                if ball.owner != owner:
                    continue
                spd = math.hypot(ball.vx, ball.vy)
                for off in (-28, 28):
                    a = math.atan2(ball.vy, ball.vx) + math.radians(off)
                    new.append(Ball(ball.x, ball.y,
                                    spd * math.cos(a), spd * math.sin(a),
                                    owner=owner))
            self.balls.extend(new)
        elif kind == 'wide':
            if owner == 'player':
                self.wide_t     = WIDE_DURATION
            else:
                self.top_wide_t = WIDE_DURATION
        elif kind == 'slow':
            if owner == 'ai':
                self.ai_slow_t = SLOW_DURATION
            else:
                self.slow_t = SLOW_DURATION
        elif kind == 'laser':
            if owner == 'player':
                self.laser_t = LASER_DURATION
            else:
                self.ai_laser_t = LASER_DURATION
        elif kind == 'pierce':
            if owner == 'player':
                self.pierce_t    = PIERCE_DURATION
            else:
                self.ai_pierce_t = PIERCE_DURATION

    # ── level progression ────────────────────────────────────────

    def next_level(self):
        self.level += 1
        if self.mode in ('classic', 'vs_ai') and self.level > 10:
            self.game_over  = True
            self.player_won = (self.score >= self.ai_score) if self.has_top_paddle else True
            return
        self._reset_level(keep_score=True)
