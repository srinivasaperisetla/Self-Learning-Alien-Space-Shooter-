"""Pure-numpy reference simulation (built first, before C++).

One-enemy (enemy1 / NORMAL) subset of the Java SpaceShooter game, ported
exactly from GamePanel.java.  Framework-agnostic, raw pixel space [0..500].
The sim is ENDLESS — it knows nothing about "winning."  It ends only on
death (lives <= 0) or an optional step cap.
"""

import numpy as np

# ---------------------------------------------------------------------------
# Constants — mirror the future constants.hpp; values from Java GamePanel.java
# ---------------------------------------------------------------------------
GAME_WIDTH = 500
GAME_HEIGHT = 500

PLAYER_START_X = 200
PLAYER_Y = 415
PLAYER_SPEED = 10
PLAYER_X_MIN = 0
PLAYER_X_MAX = 417

ENEMY_FALL_SPEED = 3

LASER_SPEED = 12
LASER_SPAWN_Y = 400
LASER_SPAWN_X_OFFSET = 32
LASER_REFIRE_Y = 0
LASER_PARK_X = 600
LASER_PARK_Y = -100

START_LIVES = 3
KILL_SCORE = 10

KILL_REWARD = 10.0
HIT_PENALTY = -10.0
SURVIVE_BONUS = 0.01

# Action encoding
LEFT = 0
RIGHT = 1
STAY = 2
SHOOT = 3


class SpaceShooterSim:
    """One-enemy subset of the Java SpaceShooter.

    All coordinates are raw pixels (0..500).  No normalisation, no win logic.

    KNOWN DEVIATION: Java lets the player move AND shoot in the same frame
    (separate keys).  Discrete(4) forces one action per tick.  Acceptable for
    Phase 1 — the laser flies independently once fired.  Can upgrade to
    MultiDiscrete([3,2]) later for full fidelity.
    """

    def __init__(self, seed=None, max_steps=None):
        self._init_seed = seed
        self._max_steps = max_steps if (max_steps is not None and max_steps > 0) else None
        self._rng = np.random.default_rng(seed)
        self.reset()

    def reset(self, seed=None):
        if seed is not None:
            self._rng = np.random.default_rng(seed)

        self.player_x = PLAYER_START_X
        self.lives = START_LIVES
        self.score = 0
        self.steps = 0

        self.laser_x = LASER_PARK_X
        self.laser_y = LASER_PARK_Y

        # Initial spawn uses newEntities range (y drawn from [100, 600))
        self.enemy_x = int(self._rng.integers(0, 415))
        self.enemy_y = -int(self._rng.integers(100, 600))

        return self._state()

    def step(self, action):
        reward = 0.0

        # 1. Apply action -----------------------------------------------
        if action == LEFT:
            self.player_x -= PLAYER_SPEED
        elif action == RIGHT:
            self.player_x += PLAYER_SPEED
        elif action == SHOOT:
            if self.laser_y <= LASER_REFIRE_Y:
                self.laser_y = LASER_SPAWN_Y
                self.laser_x = self.player_x + LASER_SPAWN_X_OFFSET

        # Clamp player (mirrors Java checkCollision lines 119-123)
        if self.player_x < PLAYER_X_MIN:
            self.player_x = PLAYER_X_MIN
        elif self.player_x > PLAYER_X_MAX:
            self.player_x = PLAYER_X_MAX

        # 2. Move laser if in flight ------------------------------------
        if self.laser_y > LASER_REFIRE_Y:
            self.laser_y -= LASER_SPEED

        # 3. Move enemy -------------------------------------------------
        self.enemy_y += ENEMY_FALL_SPEED

        # 4. Resolve collisions (order matches Java checkCollision) ------

        # B — enemy reaches bottom (Java line 129)
        if self.enemy_y > GAME_HEIGHT:
            self.lives -= 1
            reward += HIT_PENALTY
            self._recycle_enemy()

        # A — laser hits enemy (Java line 154)
        if (self.laser_x >= self.enemy_x - 15
                and self.laser_x <= self.enemy_x + 86
                and self.laser_y <= self.enemy_y + 75
                and self.laser_y >= self.enemy_y):
            self.score += KILL_SCORE
            reward += KILL_REWARD
            self.laser_x = LASER_PARK_X
            self.laser_y = LASER_PARK_Y
            self._recycle_enemy()

        # C — enemy hits player (Java line 179)
        if (self.enemy_x >= self.player_x - 75
                and self.enemy_x <= self.player_x + 75
                and self.enemy_y >= 335):
            self.lives -= 1
            reward += HIT_PENALTY
            self._recycle_enemy()

        # 5. Increment step counter --------------------------------------
        self.steps += 1

        # 6. Terminal check -----------------------------------------------
        death = self.lives <= 0
        hit_cap = self._max_steps is not None and self.steps >= self._max_steps
        done = death or hit_cap

        if not done:
            reward += SURVIVE_BONUS

        info = {
            "score": self.score,
            "lives": self.lives,
            "steps": self.steps,
            "death": death,
            "hit_cap": hit_cap,
        }

        return self._state(), reward, done, info

    # -------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------

    def _recycle_enemy(self):
        """Recycle enemy using the RECYCLE range (y drawn from [100, 500))."""
        self.enemy_x = int(self._rng.integers(0, 415))
        self.enemy_y = -int(self._rng.integers(100, 500))

    def _state(self):
        return {
            "player_x": self.player_x,
            "lives": self.lives,
            "score": self.score,
            "laser_x": self.laser_x,
            "laser_y": self.laser_y,
            "enemy_x": self.enemy_x,
            "enemy_y": self.enemy_y,
            "steps": self.steps,
        }
