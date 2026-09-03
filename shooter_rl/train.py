"""Stable-Baselines3 PPO training loop."""

import argparse
import os

from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import CheckpointCallback
from stable_baselines3.common.env_checker import check_env

from . import config
from .env import AlienShooterEnv


def main():
    parser = argparse.ArgumentParser(description="Train PPO on AlienShooterEnv")
    parser.add_argument("--timesteps", type=int, default=config.TOTAL_TIMESTEPS,
                        help="Total training timesteps")
    parser.add_argument("--seed", type=int, default=None,
                        help="RNG seed for env and PPO")
    args = parser.parse_args()

    env = AlienShooterEnv(seed=args.seed)
    print("Running SB3 env checker …")
    check_env(env, warn=True)
    print("Env check passed.\n")

    os.makedirs(config.MODELS_DIR, exist_ok=True)
    os.makedirs(config.LOGS_DIR, exist_ok=True)

    model = PPO(
        "MlpPolicy",
        env,
        verbose=1,
        ent_coef=0.01,
        tensorboard_log=config.LOGS_DIR,
        seed=args.seed,
    )

    checkpoint_cb = CheckpointCallback(
        save_freq=10_000,
        save_path=config.MODELS_DIR,
        name_prefix=config.CHECKPOINT_PREFIX,
    )

    print(f"Training for {args.timesteps:,} timesteps …\n")
    model.learn(total_timesteps=args.timesteps, callback=checkpoint_cb)

    final_path = os.path.join(config.MODELS_DIR, f"{config.CHECKPOINT_PREFIX}_final")
    model.save(final_path)

    print(f"\nFinal model saved to {final_path}")
    print(f"\nView training curves:\n  tensorboard --logdir {config.LOGS_DIR}")


if __name__ == "__main__":
    main()
