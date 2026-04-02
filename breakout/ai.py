import math
import random

from .game import BALL_RADIUS, PADDLE_H, PADDLE_Y_OFF, TOP_PADDLE_Y_OFF

# ══════════════════════════════════════════════════════════════════
#  BREAKOUT AI
# ══════════════════════════════════════════════════════════════════

AI_PARAMS = {
    #                                                urgency = seconds before ball arrives
    #                                                at which point AI abandons powerup chase
    'easy':   {'speed': 210, 'error': 58,  'react_delay': 0.45, 'aim': 0.20, 'urgency': 0.50},
    'medium': {'speed': 330, 'error': 22,  'react_delay': 0.20, 'aim': 0.60, 'urgency': 0.85},
    'hard':   {'speed': 560, 'error': 6,   'react_delay': 0.05, 'aim': 0.92, 'urgency': 1.20},
}

# Top paddle gets a speed boost in Paddle Battle — it has to cover the full
# width to intercept its own ball with no help from walls above.
TOP_PADDLE_SPEED_MULT = 1.4


class BreakoutAI:
    """
    Ball-tracking AI for Breakout.
    - Predicts ball landing position accounting for wall bounces.
    - Aims the return shot toward the brick cluster.
    - Speed-limited movement to stay beatable.
    - Periodic reaction-delay to simulate human-like imperfection.
    """

    def __init__(self, difficulty='medium'):
        p = AI_PARAMS.get(difficulty, AI_PARAMS['medium'])
        self._speed        = float(p['speed'])
        self._error_range  = float(p['error'])
        self._react_delay  = float(p['react_delay'])
        self._aim_strength = float(p['aim'])
        self._urgency      = float(p['urgency'])
        self._react_timer  = 0.0
        self._error        = 0.0   # current lateral error offset (px)

    def tick(self, dt):
        """Call once per frame before querying targets."""
        self._react_timer -= dt
        if self._react_timer <= 0:
            self._react_timer = self._react_delay + random.uniform(0, self._react_delay * 0.5)
            self._error = random.uniform(-self._error_range, self._error_range)

    def get_bottom_target(self, game, dt):
        """Target left-edge x for the bottom (player-side) paddle."""
        target_y     = game.play_h - PADDLE_Y_OFF
        owner_filter = 'player' if game.has_top_paddle else None
        paddle_w     = game._eff_paddle_w()
        bx, by       = self._brick_cluster(game)

        ball, ball_dist = self._find_best_ball(game, target_y, heading_down=True,
                                               owner_filter=owner_filter)
        pu_x = self._nearest_powerup_x(game, heading_down=True)

        if ball is not None:
            pred       = self._predict_x(ball.x, ball.vx, ball.y, ball.vy, target_y,
                                         game.play_w, bricks=game.bricks)
            rel        = self._aim_rel(pred, bx, target_y, by) * self._aim_strength
            ideal_ball = pred - paddle_w * 0.5 - rel * (paddle_w * 0.5)
            # Commit to powerup while ball is far; switch fully to ball when urgent
            if pu_x is not None:
                t_ball = ball_dist / abs(ball.vy) if abs(ball.vy) > 1 else 0.0
                ideal  = (pu_x - paddle_w * 0.5) if t_ball > self._urgency else ideal_ball
            else:
                ideal = ideal_ball
        elif pu_x is not None:
            ideal = pu_x - paddle_w * 0.5
        else:
            ideal = game.play_w * 0.5 - paddle_w * 0.5

        return self._clamp_speed(game.paddle_x, ideal + self._error,
                                 game.play_w - paddle_w, dt)

    def get_top_target(self, game, dt):
        """Target left-edge x for the top (AI-side) paddle — tracks only AI balls."""
        target_y = float(TOP_PADDLE_Y_OFF + PADDLE_H)
        paddle_w = game._eff_top_paddle_w()
        bx, by   = self._brick_cluster(game)

        ball, ball_dist = self._find_best_ball(game, target_y, heading_down=False,
                                               owner_filter='ai')
        pu_x = self._nearest_powerup_x(game, heading_down=False)

        if ball is not None:
            pred = self._predict_x(ball.x, ball.vx, ball.y, ball.vy, target_y,
                                   game.play_w, bricks=game.bricks)
            rel  = self._aim_rel(pred, bx, target_y, by) * self._aim_strength
            ideal_ball = pred - paddle_w * 0.5 - rel * (paddle_w * 0.5)
            if pu_x is not None:
                t_ball = ball_dist / abs(ball.vy) if abs(ball.vy) > 1 else 0.0
                ideal  = (pu_x - paddle_w * 0.5) if t_ball > self._urgency else ideal_ball
            else:
                ideal = ideal_ball
        elif pu_x is not None:
            ideal = pu_x - paddle_w * 0.5
        else:
            ideal = game.play_w * 0.5 - paddle_w * 0.5

        boosted_speed = self._speed * TOP_PADDLE_SPEED_MULT
        return self._clamp_speed(game.top_paddle_x, ideal + self._error,
                                 game.play_w - paddle_w, dt, speed=boosted_speed)

    def should_fire_laser(self, game, top=False):
        """
        Return True when the AI should fire its laser.
        Fires only when there are bricks roughly in front of the paddle,
        so the AI targets bricks rather than shooting into empty space.
        top=True  → top paddle (fires downward, uses top_paddle_x / ai_laser_t)
        top=False → bottom paddle (fires upward, uses paddle_x / laser_t)
        """
        if top:
            if game.ai_laser_t <= 0 or game._ai_laser_cd > 0:
                return False
            px = game.top_paddle_x
            pw = game._eff_top_paddle_w()
            def brick_ahead(b):
                return b.y >= TOP_PADDLE_Y_OFF + PADDLE_H
        else:
            if game.laser_t <= 0 or game._laser_cd > 0:
                return False
            px = game.paddle_x
            pw = game._eff_paddle_w()
            def brick_ahead(b):
                return b.y + b.h <= game.play_h - PADDLE_Y_OFF

        # Widen the search zone a little so the AI anticipates rather than reacts
        zone_l = px - pw * 0.3
        zone_r = px + pw + pw * 0.3
        for b in game.bricks:
            if not b.alive:
                continue
            if not brick_ahead(b):
                continue
            if b.x + b.w >= zone_l and b.x <= zone_r:
                return True
        return False

    # ── internals ────────────────────────────────────────────────

    def _brick_cluster(self, game):
        """Return (cx, cy) centroid of all alive bricks."""
        alive = [b for b in game.bricks if b.alive]
        if not alive:
            return game.play_w * 0.5, game.play_h * 0.5
        cx = sum(b.x + b.w * 0.5 for b in alive) / len(alive)
        cy = sum(b.y + b.h * 0.5 for b in alive) / len(alive)
        return cx, cy

    def _aim_rel(self, pred_x, target_x, paddle_y, brick_y):
        """
        Compute the paddle rel value [-0.85, 0.85] needed so the ball deflects
        from pred_x toward target_x.  Max deflection angle is 55° from vertical.

        Positive rel  → ball goes right.
        Negative rel  → ball goes left.
        paddle_left   = (pred_x - paddle_w/2) - rel * (paddle_w/2)
        """
        dist = abs(paddle_y - brick_y)
        if dist < 1:
            return 0.0
        max_reach = dist * math.tan(math.radians(55.0))
        rel = (target_x - pred_x) / max_reach
        return max(-0.85, min(0.85, rel))

    def _find_best_ball(self, game, target_y, heading_down, owner_filter=None):
        """Return (ball, distance) for the most threatening ball heading our way,
        or (None, inf) if no ball is heading toward our paddle."""
        best, best_dist = None, float('inf')
        for ball in game.balls:
            if owner_filter is not None and ball.owner != owner_filter:
                continue
            if heading_down and ball.vy <= 0:
                continue
            if not heading_down and ball.vy >= 0:
                continue
            d = abs(ball.y - target_y)
            if d < best_dist:
                best_dist, best = d, ball
        return best, best_dist

    def _nearest_powerup_x(self, game, heading_down):
        """Return x of the powerup closest to our paddle heading our way, or None.
        No spatial gate — detect from spawn and let the urgency system decide
        whether to chase it."""
        if not game.powerups:
            return None
        best_x, best_dist = None, float('inf')
        for pu in game.powerups:
            if heading_down and pu.vy <= 0:
                continue
            if not heading_down and pu.vy >= 0:
                continue
            d = abs(pu.y - (game.play_h if heading_down else 0))
            if d < best_dist:
                best_dist, best_x = d, pu.x
        return best_x

    def _predict_x(self, bx, vx, by, vy, target_y, play_w, bricks=None):
        """
        Step-simulate the ball to target_y, bouncing off walls and alive bricks.
        Bricks deflect vy (same logic as game physics) so the AI doesn't plan
        paths through brick walls that no longer exist.
        """
        if abs(vy) < 1:
            return bx
        if (vy > 0) == (target_y < by):
            return bx   # ball moving away from target

        r     = float(BALL_RADIUS)
        x, y  = float(bx), float(by)
        dx, dy = float(vx), float(vy)
        # Step size: ~half a brick height is fine for accuracy
        step  = 8.0
        max_steps = int(abs(target_y - by) / step) + 400  # safety cap

        for _ in range(max_steps):
            remaining = abs(target_y - y)
            if remaining <= step:
                # Final step — land exactly at target_y
                t  = remaining / abs(dy)
                x += dx * t
                break
            # Advance one step
            t  = step / abs(dy)
            nx = x + dx * t
            ny = y + dy * t

            # Wall bounces
            if nx - r < 0:
                nx = r
                dx = abs(dx)
            elif nx + r > play_w:
                nx = play_w - r
                dx = -abs(dx)

            # Brick collisions — only check if bricks provided
            if bricks:
                for b in bricks:
                    if not b.alive:
                        continue
                    # Simple AABB: did the ball centre pass through this brick?
                    if (b.x - r <= nx <= b.x + b.w + r and
                            b.y - r <= ny <= b.y + b.h + r):
                        dy = -dy
                        ny = y + dy * t   # re-step with flipped direction
                        break             # one deflection per step is enough

            x, y = nx, ny

        # Clamp to play area
        return max(r, min(play_w - r, x))

    def _clamp_speed(self, current, ideal, max_x, dt, speed=None):
        """Move current toward ideal but no faster than speed px/s."""
        max_move = (speed if speed is not None else self._speed) * dt
        result   = max(current - max_move, min(current + max_move, ideal))
        return max(0.0, min(max_x, result))
