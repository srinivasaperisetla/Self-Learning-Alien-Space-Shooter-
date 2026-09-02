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
    """Build a normalised float32 observation vector from a raw state dict.

    Shared helper so the C++ pybind make_obs replicates the exact same mapping.

    Layout (OBS_DIM = 14):
         0  player_x           / 417           [0, 1]
         1  lives              / 3             [0, 1+]
         2  red laser in-flight 0 / 1
         3  red laser_y        / 500  clip     [0, 1]
         4  enemy1 rel_x       (e1x-px)/500   [-1, 1]
         5  enemy1 rel_y       e1y/500 clip    [0, 1]
         6  enemy2 rel_x       (e2x-px)/500
         7  enemy2 rel_y       e2y/500 clip
         8  enemy3 rel_x       (e3x-px)/500
         9  enemy3 rel_y       e3y/500 clip
        10  blue laser rel_x   (blx-px)/500
        11  blue laser rel_y   bly/500 clip
        12  heart rel_x        (hx-px)/500
        13  heart rel_y        hy/500 clip
    """
    px = state["player_x"]
    _g = float(GAME_HEIGHT)

    player_x_norm = px / PLAYER_X_MAX
    lives_norm = state["lives"] / START_LIVES

    laser_y_raw = state["laser_y"]
    in_flight = 1.0 if (LASER_REFIRE_Y < laser_y_raw <= GAME_HEIGHT) else 0.0
    laser_y_norm = float(np.clip(laser_y_raw / _g, 0.0, 1.0))

    return np.array([
        player_x_norm,
        lives_norm,
        in_flight,
        laser_y_norm,
        (state["enemy1_x"] - px) / 500.0,
        float(np.clip(state["enemy1_y"] / _g, 0.0, 1.0)),
        (state["enemy2_x"] - px) / 500.0,
        float(np.clip(state["enemy2_y"] / _g, 0.0, 1.0)),
        (state["enemy3_x"] - px) / 500.0,
        float(np.clip(state["enemy3_y"] / _g, 0.0, 1.0)),
        (state["blue_x"] - px) / 500.0,
        float(np.clip(state["blue_y"] / _g, 0.0, 1.0)),
        (state["heart_x"] - px) / 500.0,
        float(np.clip(state["heart_y"] / _g, 0.0, 1.0)),
    ], dtype=np.float32)


class AlienShooterEnv(gymnasium.Env):
    """Gymnasium (v1) wrapper for the full SpaceShooter sim.

    Observation:  Box(-1, 1, shape=(14,), float32)
    Action:       Discrete(4) — LEFT / RIGHT / STAY / SHOOT
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
