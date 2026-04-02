import math
import pygame

# ──────────────────────────────────────────────
#  3-D MATH
# ──────────────────────────────────────────────
def rot_x(pts, a):
    c, s = math.cos(a), math.sin(a)
    return [(x, c*y - s*z, s*y + c*z) for x,y,z in pts]

def rot_y(pts, a):
    c, s = math.cos(a), math.sin(a)
    return [(c*x + s*z, y, -s*x + c*z) for x,y,z in pts]

def project(x, y, z, cx, cy, fov):
    scale = fov / (fov + z)
    return (cx + x*scale, cy - y*scale, z)

def face_normal_z(pts2d):
    p0,p1,p2 = pts2d[0],pts2d[1],pts2d[2]
    return (p1[0]-p0[0])*(p2[1]-p0[1]) - (p1[1]-p0[1])*(p2[0]-p0[0])

def lerp2(a, b, t):
    return (a[0]+(b[0]-a[0])*t, a[1]+(b[1]-a[1])*t)

def lerp_color(a, b, t):
    return tuple(int(a[i]+(b[i]-a[i])*t) for i in range(3))

def point_in_poly(x, y, poly):
    inside = False
    n = len(poly)
    j = n-1
    for i in range(n):
        xi,yi = poly[i]; xj,yj = poly[j]
        if ((yi>y)!=(yj>y)) and (x < (xj-xi)*(y-yi)/(yj-yi+1e-9)+xi):
            inside = not inside
        j = i
    return inside

# ──────────────────────────────────────────────
#  DRAW HELPERS
# ──────────────────────────────────────────────
def draw_rounded_rect(surf, color, rect, radius, border=0, border_color=None):
    r = pygame.Rect(rect)
    pygame.draw.rect(surf, color, r, border_radius=radius)
    if border and border_color:
        pygame.draw.rect(surf, border_color, r, border, border_radius=radius)

def draw_X(surf, cx, cy, size, color, alpha=255, thickness_ratio=0.13, glow_color=None):
    cx,cy = int(cx),int(cy)
    thickness = max(3, int(size*thickness_ratio))
    half = size*0.36
    gc = glow_color if glow_color is not None else color
    gs = pygame.Surface((int(size*2)+4, int(size*2)+4), pygame.SRCALPHA)
    sz = size
    for off in range(6,0,-1):
        pygame.draw.line(gs,(*gc,8*off),
            (sz-half-off,sz-half-off),(sz+half+off,sz+half+off),thickness+off*2)
        pygame.draw.line(gs,(*gc,8*off),
            (sz+half+off,sz-half-off),(sz-half-off,sz+half+off),thickness+off*2)
    surf.blit(gs,(cx-int(size)-2, cy-int(size)-2))
    col=(*color,alpha)
    pygame.draw.line(surf,col,(cx-int(half),cy-int(half)),(cx+int(half),cy+int(half)),thickness)
    pygame.draw.line(surf,col,(cx+int(half),cy-int(half)),(cx-int(half),cy+int(half)),thickness)

def draw_X_crisp(surf, cx, cy, size, color):
    """Sharp anti-alias-free X — no glow surface, ideal for small panel icons."""
    cx, cy = int(cx), int(cy)
    half = int(size * 0.38)
    thick = max(2, int(size * 0.20))
    pygame.draw.line(surf, color, (cx-half, cy-half), (cx+half, cy+half), thick)
    pygame.draw.line(surf, color, (cx+half, cy-half), (cx-half, cy+half), thick)

def draw_O_crisp(surf, cx, cy, size, color):
    """Sharp circle O — no glow surface, ideal for small panel icons."""
    cx, cy = int(cx), int(cy)
    radius = int(size * 0.36)
    thick  = max(2, int(size * 0.20))
    pygame.draw.circle(surf, color, (cx, cy), radius, thick)

def draw_O(surf, cx, cy, size, color, alpha=255, thickness_ratio=0.13, glow_color=None):
    cx,cy = int(cx),int(cy)
    thickness = max(3, int(size*thickness_ratio))
    radius = int(size*0.34)
    gc = glow_color if glow_color is not None else color
    gs = pygame.Surface((int(size*2)+4, int(size*2)+4), pygame.SRCALPHA)
    sz = size
    for off in range(6,0,-1):
        pygame.draw.circle(gs,(*gc,8*off),(int(sz),int(sz)),radius+off,thickness+off*2)
    surf.blit(gs,(cx-int(size)-2, cy-int(size)-2))
    pygame.draw.circle(surf,(*color,alpha),(cx,cy),radius,thickness)
