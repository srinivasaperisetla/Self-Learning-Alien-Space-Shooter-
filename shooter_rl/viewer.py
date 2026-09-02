"""Pygame viewer for the SpaceShooter sim.

Renders the one-enemy numpy sim on screen with the original PNGs.
Manual mode lets a human play; AI mode is Phase 3 (not yet implemented).
"""

import argparse
import sys
from pathlib import Path

import pygame

from .prototype.env_py import (
    GAME_HEIGHT,
    GAME_WIDTH,
    LASER_REFIRE_Y,
    LEFT,
    PLAYER_Y,
    RIGHT,
    SHOOT,
    STAY,
    SpaceShooterSim,
)

_ASSETS = Path(__file__).resolve().parent.parent / "assets"
_WHITE = (255, 255, 255)
_BLACK = (0, 0, 0)
_MONO = "consolas,menlo,couriernew,courier,monospace"


def _load_sprite(name, fallback_size, fallback_color):
    """Load a PNG from assets/, falling back to a coloured rectangle."""
    path = _ASSETS / name
    try:
        img = pygame.image.load(str(path)).convert_alpha()
        print(f"  [ok] {name}")
        return img
    except (pygame.error, FileNotFoundError):
        print(f"  [MISSING] {name} — using placeholder {fallback_size}")
        surf = pygame.Surface(fallback_size, pygame.SRCALPHA)
        surf.fill(fallback_color)
        return surf


def _draw_centered(surface, font, text, color, y):
    """Render *text* horizontally centred at the given *y*."""
    rendered = font.render(text, True, color)
    x = (surface.get_width() - rendered.get_width()) // 2
    surface.blit(rendered, (x, y))


def run_manual():
    """Main loop for manual (human-keyboard) play."""
    pygame.init()
    screen = pygame.display.set_mode((GAME_WIDTH, GAME_HEIGHT))
    pygame.display.set_caption("SpaceShooter")
    clock = pygame.time.Clock()

    # ---- assets --------------------------------------------------------
    print(f"Loading assets from {_ASSETS}")
    player_img = _load_sprite("spaceship.png", (100, 80), (0, 180, 255))
    enemy_img = _load_sprite("enemy1.png", (75, 75), (255, 60, 60))
    laser_img = _load_sprite("laser.png", (10, 30), (255, 0, 0))

    # ---- fonts ---------------------------------------------------------
    font_title = pygame.font.SysFont(_MONO, 50, bold=True)
    font_prompt = pygame.font.SysFont(_MONO, 22)
    font_hud = pygame.font.SysFont(_MONO, 20)
    font_hud_sm = pygame.font.SysFont(_MONO, 16)
    font_gameover = pygame.font.SysFont(_MONO, 50, bold=True)

    # ---- sim -----------------------------------------------------------
    sim = SpaceShooterSim(max_steps=None)
    state = sim._state()
    phase = "start"                    # start | running | game_over

    alive = True
    while alive:
        # ---- events ----------------------------------------------------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                alive = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    alive = False

                elif phase == "start":
                    if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                        state = sim.reset()
                        phase = "running"

                elif phase == "game_over":
                    if event.key == pygame.K_r:
                        state = sim.reset()
                        phase = "running"

        # ---- step sim (running only) -----------------------------------
        if phase == "running":
            keys = pygame.key.get_pressed()
            # SHOOT takes priority when both a move key and SPACE are held
            # (known Discrete(4) limitation — Java could move+shoot
            # simultaneously via separate key events).
            if keys[pygame.K_SPACE]:
                action = SHOOT
            elif keys[pygame.K_LEFT]:
                action = LEFT
            elif keys[pygame.K_RIGHT]:
                action = RIGHT
            else:
                action = STAY

            state, _reward, done, _info = sim.step(action)
            if done:
                phase = "game_over"

        # ---- render ----------------------------------------------------
        screen.fill(_BLACK)

        # Sprites — draw order mirrors Java: laser, player, enemy
        lx, ly = state["laser_x"], state["laser_y"]
        if ly > LASER_REFIRE_Y and lx < GAME_WIDTH:
            screen.blit(laser_img, (lx, ly))

        screen.blit(player_img, (state["player_x"], PLAYER_Y))
        screen.blit(enemy_img, (state["enemy_x"], state["enemy_y"]))

        # HUD — score + lives, right-aligned with 10px padding
        _HUD_RIGHT = GAME_WIDTH - 10
        score_surf = font_hud.render(str(state["score"]), True, _WHITE)
        lives_surf = font_hud_sm.render(f"Lives: {state['lives']}", True, _WHITE)
        screen.blit(score_surf, (_HUD_RIGHT - score_surf.get_width(), 25))
        screen.blit(lives_surf, (_HUD_RIGHT - lives_surf.get_width(), 45))

        # Phase-specific overlays
        if phase == "start":
            _draw_centered(screen, font_title, "SpaceShooter", _WHITE, 170)
            _draw_centered(screen, font_prompt,
                           "Press SPACE or ENTER to start", _WHITE, 270)

        elif phase == "game_over":
            _draw_centered(screen, font_gameover, "Game Over!", _WHITE, 180)
            _draw_centered(screen, font_prompt,
                           f"Score: {state['score']}", _WHITE, 260)
            _draw_centered(screen, font_prompt,
                           "R to restart  |  ESC to quit", _WHITE, 300)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


def main():
    parser = argparse.ArgumentParser(description="SpaceShooter viewer")
    parser.add_argument(
        "--mode", default="manual", choices=["manual", "ai"],
        help="Play mode (default: manual)",
    )
    args = parser.parse_args()

    if args.mode == "ai":
        # TODO (Phase 3): load a trained checkpoint and feed model actions
        #   to the sim instead of reading keyboard input.
        print("AI mode: coming in Phase 3")
        sys.exit(0)

    run_manual()


if __name__ == "__main__":
    main()
