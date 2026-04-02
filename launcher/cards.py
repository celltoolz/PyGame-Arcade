import pygame

from core.drawing import lerp_color, draw_X, draw_O
from checkers.game import (CK_LIGHT, CK_DARK, CK_BORDER, CK_BLACK_COL, CK_RED_COL,
                              CK_BLACK_RIM, CK_RED_RIM, CK_CROWN, CK_RED, CK_BLACK,
                              CK_RED_K, _ck_is_black, _ck_is_king)

# ══════════════════════════════════════════════════════════════════
#  GAME CARD
# ══════════════════════════════════════════════════════════════════

class GameCard:
    """Animated box-art style game card."""

    def __init__(self, title, subtitle, key_hint, draw_art_fn,
                 accent, x, y, w, h):
        self.title       = title
        self.subtitle    = subtitle
        self.key_hint    = key_hint
        self.draw_art    = draw_art_fn   # fn(surf, rect) paints the art area
        self.accent      = accent
        self.rect        = pygame.Rect(x, y, w, h)
        self.hover_t     = 0.0           # 0..1 hover animation
        self.selected_t  = 0.0

    def update(self, dt, hovered):
        speed = 6.0
        self.hover_t = min(1.0, self.hover_t + dt*speed) if hovered \
                  else max(0.0, self.hover_t - dt*speed)

    def draw(self, surf, font_title, font_sub, font_hint):
        t   = self.hover_t
        r   = self.rect

        # Lift effect
        lift    = int(t * 10)
        draw_r  = pygame.Rect(r.x, r.y - lift, r.w, r.h)

        # Drop shadow
        if draw_r.w <= 0 or draw_r.h <= 0:
            return
        shadow_alpha = int(60 + t * 100)
        for i in range(8, 0, -1):
            s = pygame.Surface((draw_r.w + i*2, draw_r.h + i*2), pygame.SRCALPHA)
            s.fill((0, 0, 0, shadow_alpha // i))
            surf.blit(s, (draw_r.x - i, draw_r.y - i + lift//2))

        # Card background
        bg = lerp_color((18, 22, 38), (28, 34, 56), t)
        pygame.draw.rect(surf, bg, draw_r, border_radius=16)

        # Art area (top 60%)
        art_h  = int(draw_r.h * 0.60)
        art_r  = pygame.Rect(draw_r.x, draw_r.y, draw_r.w, art_h)
        # Clip art to rounded top
        art_surf = pygame.Surface((art_r.w, art_r.h), pygame.SRCALPHA)
        pygame.draw.rect(art_surf, (255,255,255,255),
            (0, 0, art_r.w, art_r.h), border_radius=16)
        art_content = pygame.Surface((art_r.w, art_r.h))
        self.draw_art(art_content, pygame.Rect(0, 0, art_r.w, art_r.h))
        art_content.blit(art_surf, (0,0), special_flags=pygame.BLEND_RGBA_MIN)
        surf.blit(art_content, art_r.topleft)

        # Accent bar
        bar_h = max(3, int(draw_r.h * 0.008) + 2)
        bar_col = lerp_color(self.accent, (255,255,255), t * 0.3)
        pygame.draw.rect(surf, bar_col,
            (draw_r.x, draw_r.y + art_h, draw_r.w, bar_h))

        # Info area
        info_y = draw_r.y + art_h + bar_h + 12
        t1 = font_title.render(self.title, True,
            lerp_color((180,185,205),(255,255,255), t))
        surf.blit(t1, (draw_r.x + 18, info_y))

        t2 = font_sub.render(self.subtitle, True, (90, 100, 135))
        surf.blit(t2, (draw_r.x + 18, info_y + t1.get_height() + 4))

        # Key hint badge
        badge_col = lerp_color((35,40,62), self.accent, t * 0.8)
        badge_r   = pygame.Rect(draw_r.right - 80, draw_r.bottom - 36, 64, 24)
        pygame.draw.rect(surf, badge_col, badge_r, border_radius=6)
        th = font_hint.render(self.key_hint, True, (220,225,245))
        surf.blit(th, (badge_r.centerx - th.get_width()//2,
                       badge_r.centery - th.get_height()//2))

        # Hover border
        if t > 0.05:
            border_col = (*self.accent, int(t * 200))
            bs = pygame.Surface((draw_r.w, draw_r.h), pygame.SRCALPHA)
            pygame.draw.rect(bs, border_col, (0,0,draw_r.w,draw_r.h),
                3, border_radius=16)
            surf.blit(bs, draw_r.topleft)


# ══════════════════════════════════════════════════════════════════
#  BOX ART FUNCTIONS
# ══════════════════════════════════════════════════════════════════

def _art_tictactoe(surf, rect):
    """Draw a mini Tic-Tac-Toe board as box art."""
    surf.fill((15, 17, 26))
    # Subtle grid bg
    for x in range(0, rect.w, 20):
        pygame.draw.line(surf, (22,25,38),(x,0),(x,rect.h))
    for y in range(0, rect.h, 20):
        pygame.draw.line(surf, (22,25,38),(0,y),(rect.w,y))

    pad  = int(rect.w * 0.12)
    bsz  = min(rect.w, rect.h) - pad*2
    bx   = (rect.w - bsz) // 2
    by   = (rect.h - bsz) // 2
    cs   = bsz // 3
    lw   = max(2, bsz // 30)

    # Grid
    for i in range(1, 3):
        pygame.draw.line(surf, (55,65,100),
            (bx+i*cs, by+4), (bx+i*cs, by+bsz-4), lw)
        pygame.draw.line(surf, (55,65,100),
            (bx+4, by+i*cs), (bx+bsz-4, by+i*cs), lw)

    # Sample board state
    board = ['X','O','X', None,'X',None, 'O',None,'X']
    for i, v in enumerate(board):
        r, c = divmod(i, 3)
        cx = bx + c*cs + cs//2
        cy = by + r*cs + cs//2
        sz = cs * 0.32
        if v == 'X':
            draw_X(surf, cx, cy, sz, (255,90,90), 220)
        elif v == 'O':
            draw_O(surf, cx, cy, sz, (140,60,200), 220)

    # Win line
    p1 = pygame.Vector2(bx + 0*cs + cs//2, by + 0*cs + cs//2)
    p2 = pygame.Vector2(bx + 2*cs + cs//2, by + 2*cs + cs//2)
    pygame.draw.line(surf, (255,220,80), (int(p1.x),int(p1.y)),
        (int(p2.x),int(p2.y)), max(3, lw*2))

    # Mini 3D cube hint in corner
    cube_x, cube_y, cube_sz = rect.w - 38, 10, 22
    pts = [(cube_x+cube_sz//2, cube_y),
           (cube_x+cube_sz,    cube_y+cube_sz//3),
           (cube_x+cube_sz,    cube_y+cube_sz),
           (cube_x+cube_sz//2, cube_y+cube_sz*2//3),
           (cube_x,            cube_y+cube_sz),
           (cube_x,            cube_y+cube_sz//3)]
    pygame.draw.polygon(surf, (40,30,70), [pts[0],pts[1],pts[3],pts[5]])
    pygame.draw.polygon(surf, (55,45,90), [pts[1],pts[2],pts[3]])
    pygame.draw.polygon(surf, (30,22,55), [pts[3],pts[4],pts[5]])
    pygame.draw.lines(surf,(80,70,120),True,pts,1)


def _art_tetris(surf, rect):
    """Draw a Tetris stack as box art."""
    surf.fill((5, 8, 16))
    for x in range(0, rect.w, 18):
        pygame.draw.line(surf, (10,14,26),(x,0),(x,rect.h))
    for y in range(0, rect.h, 18):
        pygame.draw.line(surf, (10,14,26),(0,y),(rect.w,y))

    cols = 8
    rows = 10
    cell = min(rect.w // cols, rect.h // rows)
    ox   = (rect.w - cols*cell) // 2
    oy   = rect.h - rows*cell

    # Pre-defined stack layout [row][col] = color or None
    stack = [
        [None,None,None,None,None,None,None,None],
        [None,None,None,(0,220,220),None,None,None,None],
        [None,None,(0,220,220),(0,220,220),(0,220,220),None,None,None],
        [None,None,None,(160,0,220),(160,0,220),None,None,None],
        [None,(160,0,220),(160,0,220),(220,220,0),(220,220,0),None,None,None],
        [(220,140,0),(220,140,0),(220,140,0),(220,220,0),(220,220,0),(0,200,0),None,None],
        [(220,140,0),(220,0,0),(220,0,0),(220,0,0),(0,200,0),(0,200,0),(0,80,220),None],
        [(0,80,220),(220,0,0),(220,220,0),(220,220,0),(220,0,0),(0,200,0),(0,80,220),(0,80,220)],
        [(0,80,220),(0,80,220),(220,220,0),(160,0,220),(160,0,220),(0,200,0),(220,0,0),(220,0,0)],
        [(0,220,220),(0,220,220),(0,220,220),(0,220,220),(0,220,220),(0,220,220),(0,220,220),(0,220,220)],
    ]

    for r, row in enumerate(stack):
        for c, col in enumerate(row):
            if col:
                x = ox + c*cell
                y = oy + r*cell
                pygame.draw.rect(surf, col, (x+1,y+1,cell-2,cell-2), border_radius=2)
                hi = tuple(min(255,v+60) for v in col)
                pygame.draw.line(surf, hi, (x+2,y+2),(x+cell-3,y+2))
                pygame.draw.line(surf, hi, (x+2,y+2),(x+2,y+cell-3))

    # Falling I-piece
    fall_col = (0, 220, 220)
    for i in range(4):
        x = ox + 3*cell
        y = oy - (4-i)*cell
        if y >= 0:
            pygame.draw.rect(surf, fall_col, (x+1,y+1,cell-2,cell-2), border_radius=2)
            hi = tuple(min(255,v+80) for v in fall_col)
            pygame.draw.line(surf, hi,(x+2,y+2),(x+cell-3,y+2))

    # Glow at top
    glow = pygame.Surface((rect.w, 40), pygame.SRCALPHA)
    for i in range(40):
        alpha = max(0, 80 - i*3)
        pygame.draw.line(glow, (0,220,220,alpha),(0,i),(rect.w,i))
    surf.blit(glow, (0, 0))


def _art_doom(surf, rect):
    """Simple raycaster-style corridor art for the launcher card."""
    W, H = rect.w, rect.h
    surf.fill((10, 5, 5))

    # Floor and ceiling
    pygame.draw.rect(surf, (18, 8, 8),  (0, 0, W, H//2))
    pygame.draw.rect(surf, (22, 18, 14),(0, H//2, W, H//2))

    # Raycaster-style wall columns — fake perspective corridor
    num_cols  = 40
    col_w     = W / num_cols
    for i in range(num_cols):
        # Distance fades toward centre
        cx     = i / (num_cols - 1)              # 0..1
        dist   = 0.3 + 2.5 * (2*abs(cx-0.5))**1.4
        wall_h = min(H, int(H / (dist + 0.001)))
        # Texture-like colour with distance shading
        base   = max(20, int(180 / (dist + 0.5)))
        red    = min(255, int(base * 1.1))
        col    = (red, int(base * 0.35), int(base * 0.3))
        x      = int(i * col_w)
        y      = (H - wall_h) // 2
        pygame.draw.rect(surf, col, (x, y, max(1, int(col_w)+1), wall_h))

    # Centre crosshair
    cx, cy = W//2, H//2
    pygame.draw.line(surf, (200, 200, 200), (cx-8, cy), (cx+8, cy), 1)
    pygame.draw.line(surf, (200, 200, 200), (cx, cy-8), (cx, cy+8), 1)

    # Ominous red glow at vanishing point
    for r in range(30, 0, -1):
        a = max(0, 60 - r*2)
        gs = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
        pygame.draw.circle(gs, (180, 30, 20, a), (r, r), r)
        surf.blit(gs, (cx - r, cy - r))

    # Top vignette
    glow = pygame.Surface((W, H//3), pygame.SRCALPHA)
    for i in range(H//3):
        a = max(0, 80 - i*3)
        pygame.draw.line(glow, (0, 0, 0, a), (0, i), (W, i))
    surf.blit(glow, (0, 0))
