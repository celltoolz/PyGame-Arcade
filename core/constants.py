# ──────────────────────────────────────────────
#  CONSTANTS
# ──────────────────────────────────────────────
MIN_W, MIN_H  = 620, 680
DEFAULT_W     = 980
DEFAULT_H     = 820
FPS           = 60
AI_MOVE_DELAY     = 0.65
AI_MOVE_DELAY_MIN = 0.35
AI_MOVE_DELAY_MAX = 1.1
AI_RANDOM_CHANCE  = 0.15

# AI difficulty levels: name → minimax depth (0 = random)
AI_DIFFICULTIES = ['Easy', 'Medium', 'Hard']
AI_DEPTHS       = {'Easy': 0, 'Medium': 1, 'Hard': 4}

WIN_COMBOS = [
    (0,1,2),(3,4,5),(6,7,8),
    (0,3,6),(1,4,7),(2,5,8),
    (0,4,8),(2,4,6),
]
