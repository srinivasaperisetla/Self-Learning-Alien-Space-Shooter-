"""Benchmark: honest steps/sec comparison — naive single-env vs optimized batched.

Baseline definition:
    "naive single-env Python-loop" = one Environment, stepped one tick at a time
    from a Python for-loop with random actions.  This is the honest floor — it
    includes Python-loop overhead and single-env serialisation.

Additional baselines for context:
    "C++ single-env tight-loop" = same single Environment, but the entire loop runs
    in C++ (no Python overhead).  Shows how much the Python boundary costs.

Optimized configs:
    "batched SoA (N envs, 1 thread)" = BatchedEnvironment in C++, no threading.
    "batched SoA (N envs, T threads)" = BatchedEnvironment with thread pool.
"""

import os
import time
from datetime import datetime

import numpy as np

import shooter_cpp


def _bench_python_loop(n_steps, seed=42):
    """Baseline: single Environment stepped from Python."""
    env = shooter_cpp.Environment(0, seed)
    rng = np.random.default_rng(seed + 99)
    moves = rng.integers(0, 3, size=n_steps)
    fires = rng.integers(0, 2, size=n_steps)

    t0 = time.perf_counter()
    for i in range(n_steps):
        _obs, _rew, done = env.step(int(moves[i]), int(fires[i]))
        if done:
            env.reset()
    t1 = time.perf_counter()
    return t1 - t0


def _bench_batched_python(batch, n_iters, n_envs, seed=42):
    """Optimized: BatchedEnvironment stepped from Python."""
    rng = np.random.default_rng(seed + 99)

    t0 = time.perf_counter()
    for _ in range(n_iters):
        mv = rng.integers(0, 3, size=n_envs, dtype=np.intc)
        fr = rng.integers(0, 2, size=n_envs, dtype=np.intc)
        batch.step(mv, fr)
    t1 = time.perf_counter()
    return t1 - t0


def main():
    n_envs = 1024
    n_single_steps = 500_000
    n_batch_iters = 2000
    total_batch_steps = n_envs * n_batch_iters
    seed = 42

    hw_threads = os.cpu_count() or 1

    print("=" * 66)
    print("THROUGHPUT BENCHMARK")
    print("=" * 66)
    print(f"Hardware threads: {hw_threads}")
    print(f"Single-env steps: {n_single_steps:,}")
    print(f"Batched: {n_envs} envs × {n_batch_iters} iters = "
          f"{total_batch_steps:,} env-steps")
    print()

    results = []

    # 1. Python-loop baseline
    secs = _bench_python_loop(n_single_steps, seed)
    sps = n_single_steps / secs
    results.append(("Python-loop single-env", sps, secs))
    baseline_sps = sps

    # 2. C++ tight-loop baseline
    secs = shooter_cpp.benchmark_single_env(n_single_steps, seed)
    sps = n_single_steps / secs
    results.append(("C++ tight-loop single-env", sps, secs))

    # 3. Batched, 1 thread (Python-driven)
    batch1 = shooter_cpp.BatchedEnvironment(n_envs, 0, seed, 1)
    secs = _bench_batched_python(batch1, n_batch_iters, n_envs, seed)
    sps = total_batch_steps / secs
    results.append((f"Batched SoA ({n_envs} envs, 1 thread)", sps, secs))

    # 4. Batched, 1 thread (pure C++)
    secs = shooter_cpp.benchmark_batched_env(n_envs, n_batch_iters, 1, seed)
    sps = total_batch_steps / secs
    results.append((f"Batched SoA C++ loop ({n_envs}×1T)", sps, secs))

    # 5. Batched, all threads (Python-driven)
    batch_mt = shooter_cpp.BatchedEnvironment(n_envs, 0, seed, hw_threads)
    secs = _bench_batched_python(batch_mt, n_batch_iters, n_envs, seed)
    sps = total_batch_steps / secs
    results.append((f"Batched SoA ({n_envs} envs, {hw_threads}T)", sps, secs))

    # 6. Batched, all threads (pure C++)
    secs = shooter_cpp.benchmark_batched_env(n_envs, n_batch_iters,
                                              hw_threads, seed)
    sps = total_batch_steps / secs
    results.append((f"Batched SoA C++ loop ({n_envs}×{hw_threads}T)", sps, secs))

    # ---- report ------------------------------------------------------
    print(f"{'Config':<42} {'steps/sec':>12} {'speedup':>8}")
    print("-" * 66)
    for name, sps, _secs in results:
        speedup = sps / baseline_sps
        print(f"{name:<42} {sps:>12,.0f} {speedup:>7.1f}x")

    best_name, best_sps, _ = max(results, key=lambda r: r[1])
    best_x = best_sps / baseline_sps

    print()
    print(f"RESULT: {best_name} is {best_x:.0f}x faster than the naive "
          f"single-env Python-loop baseline, at {best_sps:,.0f} steps/sec.")

    # ---- save to file -------------------------------------------------
    os.makedirs("benchmarks", exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = f"benchmarks/results_{ts}.txt"
    with open(out_path, "w") as f:
        f.write(f"Benchmark run: {ts}\n")
        f.write(f"Hardware threads: {hw_threads}\n\n")
        f.write(f"{'Config':<42} {'steps/sec':>12} {'speedup':>8}\n")
        f.write("-" * 66 + "\n")
        for name, sps, _secs in results:
            speedup = sps / baseline_sps
            f.write(f"{name:<42} {sps:>12,.0f} {speedup:>7.1f}x\n")
        f.write(f"\nBest: {best_name} = {best_x:.0f}x vs naive baseline, "
                f"{best_sps:,.0f} steps/sec\n")
    print(f"\nResults saved to {out_path}")


if __name__ == "__main__":
    main()
