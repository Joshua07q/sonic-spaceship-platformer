"""Sonic Spaceship Platformer - The Astral Carrier
Run locally:   python main.py
Build for web:  python -m pygbag --build .
"""
import sys
import os
import asyncio

# Ensure project root on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pygame
from settings import SCREEN_WIDTH, SCREEN_HEIGHT, FPS
from game.states import Game
from levels.level_loader import generate_all_levels


async def main():
    pygame.init()
    pygame.display.set_caption("Sonic Spaceship Platformer — The Astral Carrier")

    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))

    # Generate level JSONs on first run
    levels_dir = os.path.join(os.path.dirname(__file__), "levels")
    if not os.path.exists(os.path.join(levels_dir, "world_1_1.json")):
        print("Generating levels…")
        generate_all_levels()
        print("Done!")

    game = Game(screen)
    await game.run()

    pygame.quit()


if __name__ == "__main__":
    asyncio.run(main())
