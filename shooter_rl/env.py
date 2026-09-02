"""Gymnasium wrapper around the pure-numpy prototype simulation."""

import gymnasium
import numpy as np
from gymnasium import spaces

from . import config
from .prototype.env_py import (
    GAME_HEIGHT,
    LASER_REFIRE_Y,
    PLAYER_X_MAX,
    START_LIVES,
    SpaceShooterSim,
)


def _make_obs(state):
    """Build a normalised observation vector from a raw state dict.

    Shared helper so the future C++ Gymnasium wrapper can replicate the same
    mapping from pixel-space state to [-1, 1] observation.

    Layout (OBS_DIM = 6):
        0  player_x       [0, 1]  over [PLAYER_X_MIN, PLAYER_X_MAX]
        1  lives           [0, 1]  over [0, START_LIVES]
        2  laser_in_flight 0 / 1
        3  laser_y         [0, 1]  over [0, GAME_HEIGHT]
        4  enemy_rel_x     [-1, 1] over [-500, 500]
        5  enemy_y         [0, 1]  over [0, GAME_HEIGHT]
    """
    player_x_norm = state["player_x"] / PLAYER_X_MAX

    lives_norm = state["lives"] / START_LIVES

    laser_y_raw = state["laser_y"]
    in_flight = 1.0 if (LASER_REFIRE_Y < laser_y_raw <= GAME_HEIGHT) else 0.0
    laser_y_norm = float(np.clip(laser_y_raw / GAME_HEIGHT, 0.0, 1.0))

    enemy_rel_x = (state["enemy_x"] - state["player_x"]) / 500.0
    enemy_y_norm = float(np.clip(state["enemy_y"] / GAME_HEIGHT, 0.0, 1.0))

    return np.array(
        [player_x_norm, lives_norm, in_flight, laser_y_norm, enemy_rel_x, enemy_y_norm],
        dtype=np.float32,
    )


class AlienShooterEnv(gymnasium.Env):
    """Gymnasium (v1) wrapper for the one-enemy SpaceShooter sim.

    Observation:  Box(-1, 1, shape=(6,), float32)
    Action:       Discrete(4)  — LEFT / RIGHT / STAY / SHOOT

    The episode terminates on death (lives <= 0) or truncates at MAX_STEPS.
    A ``is_win`` flag is added to *info* at episode end (label only — does not
    affect reward or termination).
    """

    metadata = {"render_modes": []}

    def __init__(self, seed=None):
        super().__init__()
        self._seed = seed
        self._sim = SpaceShooterSim(seed=seed, max_steps=config.MAX_STEPS)
        self.action_space = spaces.Discrete(config.N_ACTIONS)
        self.observation_space = spaces.Box(
            low=-1.0, high=1.0, shape=(config.OBS_DIM,), dtype=np.float32,
        )

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        raw = self._sim.reset(seed=seed)
        return _make_obs(raw), {}

    def step(self, action):
        raw, reward, done, info = self._sim.step(int(action))
        obs = _make_obs(raw)

        terminated = info["death"]
        truncated = info["hit_cap"]

        if terminated or truncated:
            info["is_win"] = info["score"] >= config.WIN_SCORE

        return obs, float(reward), terminated, truncated, info
