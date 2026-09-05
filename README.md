# RL Alien Space Shooter

A self-learning agent that plays a full arcade shooter — three enemy types, a
blue laser, and a health pickup — with the game ported from Java to C++ for
high-throughput reinforcement learning training.

<!-- Drop a screen recording of the AI playing into docs/demo.gif -->
![agent playing](docs/demo.gif)

---

## Highlights

- **Full 3-enemy arcade game** ported verbatim from the original Java source:
  normal (slow), fast, and shooter enemies + blue laser + heart pickup.
- **PPO agent** (Stable-Baselines3) trained end-to-end from pixels-free
  observations, using a `MultiDiscrete([3, 2])` action space (simultaneous
  move + shoot).
- **Dual-sim architecture**: a NumPy reference simulation kept bit-identical to
  a C++ engine via 7 parity tests — the C++ sim is never trusted on its own.
- **SoA-batched, multithreaded C++ stepper** for training throughput:
  **~15 M env-steps/sec** (15× over a naive single-env Python-loop baseline) on
  8-core Apple Silicon.
- **Honest, measured metrics**: every number in this README is traceable to
  `logs/eval_*.csv` or `benchmarks/results_*.txt`.

---

## Architecture

```
┌──────────────┐
│  Java game   │  (original by Srini, Cyrus, Ryan, D2 Mo)
│  (GamePanel)  │
└──────┬───────┘
       │  manual port (constants, collision order, spawns)
       ▼
┌──────────────────┐      parity tests       ┌──────────────────────┐
│  NumPy sim       │◄══════════════════════►  │  C++ sim             │
│  env_py.py       │  7 tests, tick-exact     │  environment.cpp     │
│  (ground truth)  │                          │  (pybind11 module:   │
└──────┬───────────┘                          │   shooter_cpp)       │
       │                                      └──────────┬───────────┘
       │  Gymnasium wrapper (env.py)                     │
       │  obs: 19-dim float32                            │
       │  act: MultiDiscrete([3,2])                      │
       ▼                                                 ▼
┌──────────────┐                          ┌──────────────────────────┐
│  SB3 PPO     │                          │  BatchedEnvironment      │
│  train.py    │                          │  SoA + thread pool       │
└──────┬───────┘                          │  (batched_environment.cpp)│
       │  checkpoint (.zip)               └──────────────────────────┘
       ▼                                     ▲
┌──────────────┐                             │ 2 equivalence tests
│  viewer.py   │                             │ (single-thread + multi)
│  evaluate.py │                             │
└──────────────┘                          ┌──────────────────────────┐
                                          │  test_batched_equiv.py   │
                                          └──────────────────────────┘
```

**Why two sims?** NumPy is easy to read and debug — it's the trusted reference.
C++ is fast. Parity tests are the bridge: they prove the C++ engine reproduces
the NumPy sim tick-for-tick, given the same spawn sequence and actions. The
batched environment then scales the proven-correct C++ logic to 1024 parallel
envs for training throughput.

---

## Results

### Agent performance (200 eval episodes, deterministic policy)

| Metric | Value |
|--------|-------|
| Mean score | 141.8 (~14.2 kills/episode) |
| Median score | 130 |
| Score range | 20 – 360 |
| Mean survival | 1,253 steps |
| Death rate | 100% (endless game, no win state) |
| Score ≥ 100 | 72% of episodes |
| Score ≥ 200 | 25% of episodes |

The game is endless — there is no win condition. The agent is competent: it
actively hunts all three enemy types, fires accurately, and survives ~1,250
steps on average against three concurrent threats. It does not yet reliably
dodge the blue laser (speed 12, 1-tick reaction window).

> Source: `logs/eval_20260904_122459.csv` — 200 episodes, deterministic,
> base seed 0, max 3,000 steps/episode.

### C++ throughput (8-core Apple Silicon, -O3)

| Config | steps/sec | speedup |
|--------|-----------|---------|
| Python-loop single-env (baseline) | 1,014,847 | 1.0× |
| C++ tight-loop single-env | 15,480,855 | 15.3× |
| Batched SoA (1024 envs, 1 thread) | 10,089,320 | 9.9× |
| Batched SoA (1024 envs, 8 threads) | 15,349,025 | 15.1× |

Baseline definition: a single `Environment` (the existing parity-tested one)
stepped one tick at a time in a Python `for` loop with random actions. This is
the honest floor — it includes Python-loop overhead and single-env
serialisation.

Most of the 15× gain comes from eliminating the Python loop (batched C++
stepping). Threading adds ~1.5× on top of batching and plateaus because
per-env work is tiny (~50 ns) and memory-bandwidth-bound.

> Source: `benchmarks/results_20260904_133528.txt`

---

## Quickstart

### Prerequisites

- Python ≥ 3.8
- A C++17 compiler (clang, gcc, MSVC)
- CMake ≥ 3.15

### Install

```bash
pip install -e .
```

This builds the C++ extension (`shooter_cpp`) in Release mode (-O3) via
scikit-build-core.

### Train

```bash
python -m shooter_rl.train --timesteps 4000000
```

Checkpoints are saved to `models/` every 10k steps.

### Watch the agent play

```bash
python -m shooter_rl.viewer --mode ai --model models/ppo_shooter_final
```

### Play manually

```bash
python -m shooter_rl.viewer --mode manual
```

Controls: ← → to move, SPACE to shoot, ESC to quit, R to restart after game over.

### Evaluate a checkpoint

```bash
python -m shooter_rl.evaluate --model models/ppo_shooter_final --episodes 200
```

Flags: `--seed`, `--max-steps`, `--deterministic` (default) / `--stochastic`.
Raw per-episode results are saved to `logs/eval_<timestamp>.csv`.

### Run benchmarks

```bash
python -m benchmarks.throughput
```

Results are saved to `benchmarks/results_<timestamp>.txt`.

### Run tests

```bash
pytest tests/ -v
```

- `test_parity.py` — 7 tests proving NumPy ↔ C++ tick-exact equivalence.
- `test_batched_equiv.py` — 2 tests proving the SoA/threaded batched path
  matches N independent single `Environment` instances (single-threaded +
  multi-threaded).

---

## Tech stack

| Layer | Technology |
|-------|------------|
| Game simulation | C++17, NumPy |
| Python ↔ C++ bridge | pybind11 |
| Build system | scikit-build-core, CMake |
| RL algorithm | Stable-Baselines3 (PPO, PyTorch backend) |
| Environment interface | Gymnasium |
| Viewer | Pygame |
| Tests | pytest |

---

## Observation & action space

**Observation** — 19-dimensional `float32` vector:

| Index | Field | Normalisation |
|-------|-------|---------------|
| 0 | player x | / 417 |
| 1 | lives | / 3 |
| 2 | red laser in-flight | 0 or 1 |
| 3 | red laser y | / 500, clipped |
| 4–5 | enemy1 relative x, y | (ex−px)/500, ey/500 |
| 6–7 | enemy2 relative x, y | same |
| 8–9 | enemy3 relative x, y | same |
| 10–11 | blue laser relative x, y | same |
| 12–13 | heart relative x, y | same |
| 14–16 | enemy 1/2/3 fall speed | / 7 (constants) |
| 17 | blue laser in-flight | 0 or 1 |
| 18 | blue laser velocity | speed/12 if in-flight |

**Action** — `MultiDiscrete([3, 2])`:
- `move`: 0 = LEFT, 1 = STAY, 2 = RIGHT
- `fire`: 0 = NO, 1 = YES

The agent can move and shoot simultaneously, matching what a human player does.

---

## Project journey

This project was built iteratively, de-risking at each phase:

1. **NumPy sim first** — ported the Java game logic to NumPy, got PPO training
   working on one enemy before adding complexity.
2. **C++ port under parity** — ported the sim to C++ and locked it down with
   tick-exact parity tests. The C++ sim is never modified without the parity
   tests passing.
3. **Scaled to full game** — added all three enemies, the blue laser, and the
   heart. Both sims were extended in lockstep.
4. **Diagnosed failure modes** — the initial agent camped the slow enemy and
   ignored the dangerous ones. This was fixed iteratively:
   - **Reward shaping**: per-enemy kill rewards (10 / 25 / 30) so engaging
     riskier enemies pays off.
   - **Observation redesign**: added explicit velocity fields (indices 14–18)
     after frame stacking failed to convey motion.
   - **Action space upgrade**: `Discrete(4)` → `MultiDiscrete([3, 2])` so the
     agent can move and shoot in the same tick.
5. **Optimised throughput** — SoA batching + persistent thread pool, benchmarked
   honestly.

**Known limitations & next steps:**
- The agent does not reliably dodge the blue laser (speed 12, ~1-tick window).
  A proximity-penalty reward term or curriculum training could help.
- Training was capped at 4M steps; longer runs (10M+) with tuned hyperparameters
  would likely improve performance.
- The batched C++ env is built but not yet wired into training (the agent trains
  on the NumPy sim via Gymnasium).

---

## Credits

Based on the original Java arcade game by **Srini Perisetla**, **Cyrus**,
**Ryan**, and **D2 Mo**.
