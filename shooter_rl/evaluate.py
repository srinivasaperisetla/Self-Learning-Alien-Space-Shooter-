"""Headless evaluation: load a trained checkpoint, run N episodes, report stats."""

import argparse
import csv
import os
import sys
from datetime import datetime

import numpy as np

from . import config
from .env import AlienShooterEnv


def _run_episode(model, env, seed, deterministic):
    """Run one episode and return a results dict."""
    obs, _info = env.reset(seed=seed)
    total_reward = 0.0
    steps = 0

    while True:
        action, _ = model.predict(obs, deterministic=deterministic)
        obs, reward, terminated, truncated, info = env.step(action)
        total_reward += reward
        steps += 1

        if terminated or truncated:
            return {
                "score": info["score"],
                "reward": round(total_reward, 4),
                "length": info["steps"],
                "ended_by": "death" if info["death"] else "cap",
                "final_lives": info["lives"],
            }


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate a trained PPO checkpoint over N headless episodes",
    )
    parser.add_argument(
        "--model", default=None,
        help="Path to PPO checkpoint .zip "
             f"(default: {config.MODELS_DIR}/{config.CHECKPOINT_PREFIX}_final)",
    )
    parser.add_argument("--episodes", type=int, default=200)
    parser.add_argument("--seed", type=int, default=0,
                        help="Base seed (episode i uses seed+i)")
    parser.add_argument("--max-steps", type=int, default=config.MAX_STEPS,
                        help="Per-episode step cap (default: config.MAX_STEPS)")
    parser.add_argument("--deterministic", dest="deterministic",
                        action="store_true", default=True)
    parser.add_argument("--stochastic", dest="deterministic",
                        action="store_false")
    args = parser.parse_args()

    # ---- locate model ------------------------------------------------
    model_path = args.model or os.path.join(
        config.MODELS_DIR, f"{config.CHECKPOINT_PREFIX}_final",
    )
    zip_path = model_path if model_path.endswith(".zip") else model_path + ".zip"
    if not os.path.isfile(zip_path) and not os.path.isfile(model_path):
        print(f"ERROR: checkpoint not found at '{model_path}' or '{zip_path}'")
        print("Train a model first:  python -m shooter_rl.train --timesteps 4000000")
        sys.exit(1)

    from stable_baselines3 import PPO
    model = PPO.load(model_path)

    # ---- obs shape sanity check --------------------------------------
    env = AlienShooterEnv()
    expected = env.observation_space.shape
    try:
        model_obs = model.observation_space.shape
    except AttributeError:
        model_obs = None
    if model_obs is not None and model_obs != expected:
        print(f"ERROR: obs shape mismatch — model expects {model_obs}, "
              f"env provides {expected}.")
        print("This usually means the checkpoint was trained with a different "
              "OBS_DIM or with VecFrameStack. Retrain with the current env.")
        sys.exit(1)
    env.close()

    # ---- run episodes ------------------------------------------------
    print(f"Evaluating {args.episodes} episodes "
          f"(deterministic={args.deterministic}, max_steps={args.max_steps}, "
          f"base_seed={args.seed})\n")

    results = []
    for i in range(args.episodes):
        ep_env = AlienShooterEnv(seed=args.seed + i)
        ep_env._sim._max_steps = args.max_steps
        res = _run_episode(model, ep_env, seed=args.seed + i,
                           deterministic=args.deterministic)
        res["episode"] = i
        res["seed"] = args.seed + i
        results.append(res)
        ep_env.close()

        if (i + 1) % 50 == 0 or i == args.episodes - 1:
            print(f"  … {i + 1}/{args.episodes} episodes done")

    # ---- extract arrays -----------------------------------------------
    scores = np.array([r["score"] for r in results], dtype=float)
    rewards = np.array([r["reward"] for r in results], dtype=float)
    lengths = np.array([r["length"] for r in results], dtype=float)
    deaths = sum(1 for r in results if r["ended_by"] == "death")
    caps = sum(1 for r in results if r["ended_by"] == "cap")
    n = len(results)

    # ---- print report -------------------------------------------------
    print("\n" + "=" * 60)
    print("EVALUATION REPORT")
    print("=" * 60)

    print(f"\nEpisodes: {n}   |   Max steps/ep: {args.max_steps}   |   "
          f"Deterministic: {args.deterministic}")

    print(f"\n--- SCORE (in-game, kills×10) ---")
    print(f"  Mean:   {scores.mean():.1f}   Median: {np.median(scores):.1f}   "
          f"Std: {scores.std():.1f}")
    print(f"  Min:    {scores.min():.0f}   Max: {scores.max():.0f}")
    print(f"  Mean kills: {scores.mean() / 10:.1f}")
    pcts = [10, 25, 50, 75, 90]
    pvals = np.percentile(scores, pcts)
    print(f"  Percentiles: " +
          "  ".join(f"p{p}={v:.0f}" for p, v in zip(pcts, pvals)))

    print(f"\n--- SHAPED RL REWARD ---")
    print(f"  Mean: {rewards.mean():.2f}   Median: {np.median(rewards):.2f}   "
          f"Std: {rewards.std():.2f}")

    print(f"\n--- SURVIVAL (episode length) ---")
    print(f"  Mean: {lengths.mean():.0f}   Median: {np.median(lengths):.0f}   "
          f"Std: {lengths.std():.0f}")
    print(f"  Survived to cap ({args.max_steps} steps): "
          f"{caps}/{n} = {100 * caps / n:.1f}%")

    print(f"\n--- DEATH RATE ---")
    print(f"  Died: {deaths}/{n} = {100 * deaths / n:.1f}%   |   "
          f"Survived to cap: {caps}/{n} = {100 * caps / n:.1f}%")

    print(f"\n--- WIN RATE (score thresholds) ---")
    print(f"  {'Threshold':>10}  {'Wins':>6}  {'Rate':>7}")
    for t in [100, 200, 300, 400, 500, 1000]:
        w = int((scores >= t).sum())
        print(f"  {'≥' + str(t):>10}  {w:>6}  {100 * w / n:>6.1f}%")

    print(f"\n--- SURVIVAL RATE (step thresholds) ---")
    print(f"  {'Threshold':>10}  {'Count':>6}  {'Rate':>7}")
    for t in [1000, 1500, 2000, 2500, 3000]:
        c = int((lengths >= t).sum())
        print(f"  {'≥' + str(t):>10}  {c:>6}  {100 * c / n:>6.1f}%")

    # ---- save CSV -----------------------------------------------------
    os.makedirs(config.LOGS_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = os.path.join(config.LOGS_DIR, f"eval_{ts}.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["episode", "seed", "score", "reward",
                           "length", "ended_by", "final_lives"],
        )
        writer.writeheader()
        writer.writerows(results)
    print(f"\nRaw results saved to {csv_path}")

    # ---- suggested résumé metrics ------------------------------------
    print("\n" + "-" * 60)
    print("SUGGESTED RESUME METRICS (from this run)")
    print("-" * 60)
    print(f"  • Mean score {scores.mean():.0f} over {n} episodes "
          f"({scores.mean() / 10:.0f} avg kills)")
    print(f"  • Median score {np.median(scores):.0f} (p50)")
    if caps > 0:
        print(f"  • Survived to {args.max_steps}-step cap in "
              f"{100 * caps / n:.0f}% of episodes")
    best_threshold = None
    for t in [500, 400, 300, 200, 100]:
        rate = (scores >= t).sum() / n
        if rate >= 0.5:
            best_threshold = t
            break
    if best_threshold:
        rate = 100 * (scores >= best_threshold).sum() / n
        print(f"  • Score ≥{best_threshold} in {rate:.0f}% of episodes")
    print()


if __name__ == "__main__":
    main()
