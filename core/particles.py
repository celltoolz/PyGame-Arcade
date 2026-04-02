import math
import random
import pygame

# ──────────────────────────────────────────────
#  PARTICLE SYSTEM
# ──────────────────────────────────────────────
class Particle:
    def __init__(self, x, y, color):
        angle  = random.uniform(0, 2*math.pi)
        speed  = random.uniform(60, 220)
        self.x = x
        self.y = y
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.life     = 1.0                          # 1.0 → 0.0
        self.decay    = random.uniform(1.1, 2.0)     # lifetime speed
        self.size     = random.uniform(3, 7)
        self.color    = color
        self.gravity  = random.uniform(80, 160)

    def update(self, dt):
        self.x    += self.vx * dt
        self.y    += self.vy * dt
        self.vy   += self.gravity * dt               # drift downward
        self.vx   *= (1 - dt * 2)                    # air resistance
        self.life -= self.decay * dt
        self.size  = max(0, self.size - dt * 4)

    @property
    def alive(self):
        return self.life > 0

    def draw(self, surf):
        if not self.alive: return
        alpha = int(self.life * 220)
        r = max(1, int(self.size))
        s = pygame.Surface((r*2+2, r*2+2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color, alpha), (r+1, r+1), r)
        surf.blit(s, (int(self.x)-r-1, int(self.y)-r-1))


class ParticleSystem:
    def __init__(self):
        self._particles = []

    def burst(self, x, y, color, count=30):
        """Emit `count` particles from screen position (x, y)."""
        # Also add a few larger, slower "sparkle" particles
        for _ in range(count):
            self._particles.append(Particle(x, y, color))
        # bright white sparkles for pop
        for _ in range(8):
            p = Particle(x, y, (255, 255, 255))
            p.size   = random.uniform(2, 4)
            p.decay  = random.uniform(1.5, 2.5)
            self._particles.append(p)

    def update(self, dt):
        self._particles = [p for p in self._particles if p.alive]
        for p in self._particles:
            p.update(dt)

    def draw(self, surf):
        for p in self._particles:
            p.draw(surf)

    @property
    def active(self):
        return len(self._particles) > 0
