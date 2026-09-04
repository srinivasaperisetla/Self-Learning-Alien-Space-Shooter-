"""Assert BatchedEnvironment produces results identical to N separate
Environment instances given the same seeds and action sequences.

Runs single-threaded AND multi-threaded and asserts both match the reference.
"""

import numpy as np
import pytest

import shooter_cpp

OBS_DIM = 19
N_ENVS = 8
N_STEPS = 3000
BASE_SEED = 77


def _run_equiv(n_threads):
    """Run N_ENVS single Environments and one BatchedEnvironment in lockstep."""
    rng = np.random.default_rng(42)
    moves_all = rng.integers(0, 3, size=(N_STEPS, N_ENVS))
    fires_all = rng.integers(0, 2, size=(N_STEPS, N_ENVS))

    singles = [shooter_cpp.Environment(0, BASE_SEED + i) for i in range(N_ENVS)]
    batch = shooter_cpp.BatchedEnvironment(N_ENVS, 0, BASE_SEED, n_threads)

    for tick in range(N_STEPS):
        mv = moves_all[tick].astype(np.intc).copy()
        fr = fires_all[tick].astype(np.intc).copy()

        b_obs, b_rew, b_done = batch.step(mv, fr)

        for i in range(N_ENVS):
            s_obs, s_rew, s_done = singles[i].step(int(mv[i]), int(fr[i]))

            if s_done:
                s_obs_reset = singles[i].reset()

                assert b_done[i] == 1, (
                    f"tick {tick} env {i}: single done but batched not done"
                )
                assert abs(s_rew - float(b_rew[i])) < 1e-6, (
                    f"tick {tick} env {i}: reward mismatch on done tick: "
                    f"single={s_rew}, batched={float(b_rew[i])}"
                )
                np.testing.assert_allclose(
                    s_obs_reset, b_obs[i], atol=1e-6,
                    err_msg=f"tick {tick} env {i}: post-reset obs mismatch "
                            f"(n_threads={n_threads})",
                )
            else:
                assert b_done[i] == 0, (
                    f"tick {tick} env {i}: single alive but batched done"
                )
                assert abs(s_rew - float(b_rew[i])) < 1e-6, (
                    f"tick {tick} env {i}: reward mismatch: "
                    f"single={s_rew}, batched={float(b_rew[i])}"
                )
                np.testing.assert_allclose(
                    np.asarray(s_obs), b_obs[i], atol=1e-6,
                    err_msg=f"tick {tick} env {i}: obs mismatch "
                            f"(n_threads={n_threads})",
                )


def test_batched_equiv_single_threaded():
    """BatchedEnvironment (1 thread) matches N single Environments."""
    _run_equiv(n_threads=1)


def test_batched_equiv_multi_threaded():
    """BatchedEnvironment (multi-threaded) matches N single Environments."""
    _run_equiv(n_threads=4)
