"""
╔══════════════════════════════════════════════════╗
║                   ARCADE                        ║
║  Games: Tic Tac Toe · Tetris · Connect 4        ║
║         Checkers · Doom                         ║
║                                                 ║
║  Requirements: pip install pygame               ║
║  Run:          python arcade.py                 ║
╚══════════════════════════════════════════════════╝
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pygame
from core.screen import SM
from launcher.launcher import Launcher

if __name__ == "__main__":
    pygame.init()
    SM.init()
    SM.center()
    try:
        Launcher().run()
    except KeyboardInterrupt:
        pass
