"""Hyperparameters, observation/action dimensions, and file paths.

Game-physics constants live in prototype/env_py.py (and later constants.hpp).
Only training / evaluation knobs belong here.
"""

OBS_DIM = 14
N_ACTIONS = 4

MAX_STEPS = 3000
WIN_SCORE = 1000          # placeholder — label/eval only, tune after Phase 1

# Full game is harder; plan for 2M-10M timesteps for a strong agent.
TOTAL_TIMESTEPS = 300_000

MODELS_DIR = "models"
LOGS_DIR = "logs"
CHECKPOINT_PREFIX = "ppo_shooter"
