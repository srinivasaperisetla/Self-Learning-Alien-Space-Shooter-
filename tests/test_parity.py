"""Assert C++ sim == numpy prototype for same injected spawns + actions.

Per-entity spawn design:
    Each entity (enemy1, enemy2, enemy3, heart) has its OWN list of (x, y)
    pairs injected into both sims.  Pairs are consumed in collision-resolution
    order, which is identical in Python and C++:

        reset  -> pair 0 from each entity's list
        recycle events during step (in collision order):
            enemy1 bottom / laser-kill / player-hit -> next from enemy1 list
            enemy2 bottom / laser-kill / player-hit -> next from enemy2 list
            enemy3 bottom / laser-kill / player-hit -> next from enemy3 list
            heart  missed / pickup                  -> next from heart list

    Blue laser position is deterministic (derived from enemy3) -- no source.

Actions are [move, fire] pairs (MultiDiscrete([3, 2])):
    move: 0=LEFT, 1=STAY, 2=RIGHT    fire: 0=NO-FIRE, 1=FIRE
"""

import numpy as np
import pytest

import shooter_cpp
from shooter_rl.env import _make_obs
from shooter_rl.prototype.env_py import SpaceShooterSim

_STATE_KEYS = (
    "player_x", "lives", "score",
    "laser_x", "laser_y",
    "enemy1_x", "enemy1_y",
    "enemy2_x", "enemy2_y",
    "enemy3_x", "enemy3_y",
    "blue_x", "blue_y",
    "heart_x", "heart_y",
    "steps",
)


def _make_entity_pairs(n, seed):
    """Generate *n* (x, y) pairs from a fixed seed."""
    rng = np.random.default_rng(seed)
    pairs = []
    for _ in range(n):
        x = int(rng.integers(0, 500))
        y = -int(rng.integers(50, 800))
        pairs.append((x, y))
    return pairs


def _make_all_spawns(n=500, base_seed=10000):
    """Return a dict of 4 entity pair lists (deterministic)."""
    return {
        "enemy1": _make_entity_pairs(n, base_seed),
        "enemy2": _make_entity_pairs(n, base_seed + 1),
        "enemy3": _make_entity_pairs(n, base_seed + 2),
        "heart":  _make_entity_pairs(n, base_seed + 3),
    }


def _assert_states_match(py_state, cpp_state, tick, move, fire):
    for key in _STATE_KEYS:
        pv = py_state[key]
        cv = cpp_state[key]
        assert pv == cv, (
            f"MISMATCH at tick {tick} (move={move}, fire={fire}): "
            f"{key}: python={pv}, cpp={cv}"
        )


def _run_parity(actions, n_pairs=500):
    """Step both sims in lockstep and assert full parity.

    *actions* is a sequence of (move, fire) tuples.
    """
    spawns = _make_all_spawns(n_pairs)

    py_src = {k: iter(v) for k, v in spawns.items()}
    py_sim = SpaceShooterSim(max_steps=0, spawn_source=py_src)

    cpp_env = shooter_cpp.Environment(0, spawns)

    py_state = py_sim._state()
    cpp_state = cpp_env.get_state()
    _assert_states_match(py_state, cpp_state, tick=-1, move=-1, fire=-1)

    for tick, (move, fire) in enumerate(actions):
        move = int(move)
        fire = int(fire)

        py_state, py_reward, py_done, _info = py_sim.step([move, fire])
        cpp_obs, cpp_reward, cpp_done = cpp_env.step(move, fire)
        cpp_state = cpp_env.get_state()

        _assert_states_match(py_state, cpp_state, tick, move, fire)

        assert abs(py_reward - cpp_reward) < 1e-9, (
            f"REWARD MISMATCH at tick {tick} (move={move}, fire={fire}): "
            f"python={py_reward}, cpp={cpp_reward}"
        )

        assert py_done == cpp_done, (
            f"DONE MISMATCH at tick {tick} (move={move}, fire={fire}): "
            f"python={py_done}, cpp={cpp_done}"
        )

        py_obs = _make_obs(py_state)
        np.testing.assert_allclose(
            py_obs, cpp_obs, atol=1e-6,
            err_msg=f"OBS MISMATCH at tick {tick} (move={move}, fire={fire})",
        )

        if py_done:
            break


# --------------------------------------------------------------------------
# Test cases
# --------------------------------------------------------------------------

def test_random_actions():
    """10 000-step pseudo-random (move, fire) sequence."""
    rng = np.random.default_rng(42)
    moves = rng.integers(0, 3, size=10_000)
    fires = rng.integers(0, 2, size=10_000)
    _run_parity(list(zip(moves, fires)))


def test_spam_shoot():
    """Agent stays still and fires every tick."""
    _run_parity([(1, 1)] * 5_000)


def test_hug_left_wall():
    """Agent holds LEFT, no fire."""
    _run_parity([(0, 0)] * 5_000)


def test_alternate_left_right():
    """Agent alternates LEFT / RIGHT, firing every tick."""
    actions = [(0 if i % 2 == 0 else 2, 1) for i in range(5_000)]
    _run_parity(actions)


def test_stay_under_blue_laser():
    """Agent stays still, no fire — exercises blue laser refire + hit."""
    _run_parity([(1, 0)] * 5_000)


def test_chase_right():
    """Agent holds RIGHT, fires every tick."""
    _run_parity([(2, 1)] * 5_000)


def test_move_and_shoot():
    """Agent moves AND shoots simultaneously — exercises the MultiDiscrete
    capability that Discrete(4) couldn't express."""
    rng = np.random.default_rng(99)
    moves = rng.integers(0, 3, size=5_000)
    actions = [(int(m), 1) for m in moves]
    _run_parity(actions)
