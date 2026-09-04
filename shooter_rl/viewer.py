"""Pygame viewer for the SpaceShooter sim.

Renders the full-game numpy sim on screen with the original PNGs.
Supports manual (keyboard) and AI (trained PPO checkpoint) play modes.
"""

import argparse
import os
import sys
from pathlib import Path

import pygame

from . import config
from .env import _make_obs
from .prototype.env_py import (
    GAME_HEIGHT,
    GAME_WIDTH,
    LASER_REFIRE_Y,
    LASER_SPAWN_X_OFFSET,
    LASER_SPAWN_Y,
    PLAYER_Y,
    SpaceShooterSim,
)

_ASSETS = Path(__file__).resolve().parent.parent / "assets"
_WHITE = (255, 255, 255)
_BLACK = (0, 0, 0)
_GREY = (160, 160, 160)
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


def _run_game(mode, model=None, seed=None):
    """Shared game loop for both manual and AI modes."""
    pygame.init()
    screen = pygame.display.set_mode((GAME_WIDTH, GAME_HEIGHT))
    pygame.display.set_caption("SpaceShooter")
    clock = pygame.time.Clock()

    # ---- assets --------------------------------------------------------
    print(f"Loading assets from {_ASSETS}")
    player_img = _load_sprite("spaceship.png", (100, 80), (0, 180, 255))
    enemy1_img = _load_sprite("enemy1.png", (75, 75), (255, 60, 60))
    enemy2_img = _load_sprite("enemy2.png", (75, 75), (255, 160, 0))
    enemy3_img = _load_sprite("enemy3.png", (90, 75), (180, 0, 255))
    laser_img = _load_sprite("laser.png", (10, 30), (255, 0, 0))
    blue_laser_img = _load_sprite("bluelaser.png", (10, 30), (0, 120, 255))
    heart_img = _load_sprite("heart.png", (30, 30), (255, 50, 100))

    # ---- fonts ---------------------------------------------------------
    font_title = pygame.font.SysFont(_MONO, 50, bold=True)
    font_prompt = pygame.font.SysFont(_MONO, 22)
    font_hud = pygame.font.SysFont(_MONO, 20)
    font_hud_sm = pygame.font.SysFont(_MONO, 16)
    font_gameover = pygame.font.SysFont(_MONO, 50, bold=True)
    font_mode = pygame.font.SysFont(_MONO, 14)

    # ---- sim (endless — no step cap for watching) ----------------------
    sim = SpaceShooterSim(seed=seed, max_steps=None)
    state = sim._state()
    phase = "start"

    mode_label = font_mode.render(f"MODE: {mode.upper()}", True, _GREY)

    alive = True
    while alive:
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

        if phase == "running":
            if mode == "ai":
                obs = _make_obs(state)
                action, _ = model.predict(obs, deterministic=True)
                move_act, fire_act = int(action[0]), int(action[1])
                state, _reward, done, _info = sim.step([move_act, fire_act])
            else:
                keys = pygame.key.get_pressed()
                move_act = 1  # STAY
                if keys[pygame.K_LEFT]:
                    move_act = 0
                elif keys[pygame.K_RIGHT]:
                    move_act = 2
                fire_act = 1 if keys[pygame.K_SPACE] else 0
                state, _reward, done, _info = sim.step([move_act, fire_act])

            if done:
                phase = "game_over"

        # ---- render ----------------------------------------------------
        screen.fill(_BLACK)

        # Red laser
        lx, ly = state["laser_x"], state["laser_y"]
        if ly > LASER_REFIRE_Y and lx < GAME_WIDTH:
            screen.blit(laser_img, (lx, ly))
        else:
            screen.blit(laser_img,
                        (state["player_x"] + LASER_SPAWN_X_OFFSET, LASER_SPAWN_Y))

        # Blue laser (draw only when on-screen)
        blx, bly = state["blue_x"], state["blue_y"]
        if 0 <= bly <= GAME_HEIGHT and blx < GAME_WIDTH:
            screen.blit(blue_laser_img, (blx, bly))

        # Heart (draw only when on-screen)
        hx, hy = state["heart_x"], state["heart_y"]
        if 0 <= hy <= GAME_HEIGHT and hx < GAME_WIDTH:
            screen.blit(heart_img, (hx, hy))

        # Player
        screen.blit(player_img, (state["player_x"], PLAYER_Y))

        # Enemies
        screen.blit(enemy1_img, (state["enemy1_x"], state["enemy1_y"]))
        screen.blit(enemy2_img, (state["enemy2_x"], state["enemy2_y"]))
        screen.blit(enemy3_img, (state["enemy3_x"], state["enemy3_y"]))

        # HUD
        _HUD_RIGHT = GAME_WIDTH - 10
        score_surf = font_hud.render(str(state["score"]), True, _WHITE)
        lives_surf = font_hud_sm.render(f"Lives: {state['lives']}", True, _WHITE)
        screen.blit(score_surf, (_HUD_RIGHT - score_surf.get_width(), 25))
        screen.blit(lives_surf, (_HUD_RIGHT - lives_surf.get_width(), 45))

        screen.blit(mode_label, (10, 10))

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
    parser.add_argument(
        "--model", default=None,
        help="Path to a PPO checkpoint .zip (default: models/ppo_shooter_final)",
    )
    parser.add_argument(
        "--seed", type=int, default=None,
        help="RNG seed for reproducible games",
    )
    args = parser.parse_args()

    model = None
    if args.mode == "ai":
        model_path = args.model or os.path.join(
            config.MODELS_DIR, f"{config.CHECKPOINT_PREFIX}_final",
        )
        if not (os.path.isfile(model_path) or os.path.isfile(model_path + ".zip")):
            print(f"ERROR: checkpoint not found at '{model_path}' or '{model_path}.zip'")
            print("Train a model first:  python -m shooter_rl.train")
            sys.exit(1)

        from stable_baselines3 import PPO
        model = PPO.load(model_path)
        print(f"Loaded checkpoint: {model_path}")

    _run_game(args.mode, model=model, seed=args.seed)


if __name__ == "__main__":
    main()
