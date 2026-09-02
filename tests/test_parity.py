"""Assert C++ sim == numpy prototype for same seed + actions.

Each test injects a pre-computed list of (enemy_x, enemy_y) spawn pairs into
BOTH the Python SpaceShooterSim (via spawn_source=iter(pairs)) and the C++
Environment (via the VectorSpawnSource constructor).  Both sims consume pairs
in identical order (reset → pair 0, each recycle → next pair), so every
field is deterministic and comparable tick-for-tick.

On mismatch the assertion prints the tick index, field name, and both values.
"""

import numpy as np
import pytest

import shooter_cpp
from shooter_rl.env import _make_obs
from shooter_rl.prototype.env_py import SpaceShooterSim

_STATE_KEYS = ("player_x", "lives", "score", "laser_x", "laser_y",
               "enemy_x", "enemy_y", "steps")


def _make_spawn_pairs(n, seed=12345):
    """Generate *n* (x, y) spawn pairs from a fixed seed."""
    rng = np.random.default_rng(seed)
    pairs = []
    for _ in range(n):
        x = int(rng.integers(0, 415))
        y = -int(rng.integers(100, 500))
        pairs.append((x, y))
    return pairs


def _assert_states_match(py_state, cpp_state, tick, action):
    for key in _STATE_KEYS:
        pv = py_state[key]
        cv = cpp_state[key]
        assert pv == cv, (
            f"MISMATCH at tick {tick} (action={action}): "
            f"{key}: python={pv}, cpp={cv}"
        )


def _run_parity(actions, n_pairs=500):
    """Step both sims in lockstep and assert full parity."""
    pairs = _make_spawn_pairs(n_pairs)

    py_sim = SpaceShooterSim(max_steps=0, spawn_source=iter(pairs))
    cpp_env = shooter_cpp.Environment(0, list(pairs))

    # Initial state (set by constructors, which each consume pair 0)
    py_state = py_sim._state()
    cpp_state = cpp_env.get_state()
    _assert_states_match(py_state, cpp_state, tick=-1, action=-1)

    for tick, action in enumerate(actions):
        action = int(action)

        py_state, py_reward, py_done, _info = py_sim.step(action)
        cpp_obs, cpp_reward, cpp_done = cpp_env.step(action)
        cpp_state = cpp_env.get_state()

        # Raw state fields
        _assert_states_match(py_state, cpp_state, tick, action)

        # Reward
        assert abs(py_reward - cpp_reward) < 1e-9, (
            f"REWARD MISMATCH at tick {tick} (action={action}): "
            f"python={py_reward}, cpp={cpp_reward}"
        )

        # Done flag
        assert py_done == cpp_done, (
            f"DONE MISMATCH at tick {tick} (action={action}): "
            f"python={py_done}, cpp={cpp_done}"
        )

        # Observation vector (C++ obs vs env.py _make_obs on Python state)
        py_obs = _make_obs(py_state)
        np.testing.assert_allclose(
            py_obs, cpp_obs, atol=1e-6,
            err_msg=f"OBS MISMATCH at tick {tick} (action={action})",
        )

        if py_done:
            break


# --------------------------------------------------------------------------
# Test cases
# --------------------------------------------------------------------------

def test_random_actions():
    """10 000-step pseudo-random action sequence (seed 42)."""
    rng = np.random.default_rng(42)
    actions = rng.integers(0, 4, size=10_000)
    _run_parity(actions)


def test_spam_shoot():
    """Agent spams SHOOT every tick."""
    _run_parity([3] * 5_000)


def test_hug_left_wall():
    """Agent holds LEFT every tick."""
    _run_parity([0] * 5_000)


def test_alternate_left_right():
    """Agent alternates LEFT / RIGHT every tick."""
    actions = [0 if i % 2 == 0 else 1 for i in range(5_000)]
    _run_parity(actions)
