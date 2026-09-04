"""Pure-numpy reference simulation — full Java SpaceShooter game.

Three enemies (NORMAL / FAST / SHOOTER), red laser (player), blue laser
(enemy3), and a heart pickup.  Framework-agnostic, raw pixel space [0..500].
The sim is ENDLESS — it ends only on death (lives <= 0) or an optional
step cap.
"""

import numpy as np

# ---------------------------------------------------------------------------
# Constants — mirror constants.hpp; values from Java GamePanel.java
# ---------------------------------------------------------------------------
GAME_WIDTH = 500
GAME_HEIGHT = 500

PLAYER_START_X = 200
PLAYER_Y = 415
PLAYER_SPEED = 10
PLAYER_X_MIN = 0
PLAYER_X_MAX = 417

# Enemy1 / NORMAL
ENEMY1_FALL_SPEED = 3
ENEMY1_SPAWN_X_MAX = 415

# Enemy2 / FAST
ENEMY2_FALL_SPEED = 7
ENEMY2_SPAWN_X_MAX = 417

# Enemy3 / SHOOTER
ENEMY3_FALL_SPEED = 1
ENEMY3_SPAWN_X_MAX = 405

# Red laser (player)
LASER_SPEED = 12
LASER_SPAWN_Y = 400
LASER_SPAWN_X_OFFSET = 32
LASER_REFIRE_Y = 0
LASER_PARK_X = 600
LASER_PARK_Y = -100

# Blue laser (enemy3)
BLUE_LASER_SPEED = 12

# Heart
HEART_SPEED = 2
HEART_SPAWN_X_MAX = 471
HEART_INITIAL_Y = 2000

START_LIVES = 3
KILL_SCORE = 10

# RL reward shaping (per-enemy; KILL_SCORE stays 10 for all — Java-faithful)
KILL_REWARD_ENEMY1 = 10.0
KILL_REWARD_ENEMY2 = 25.0
KILL_REWARD_ENEMY3 = 30.0
HIT_PENALTY = -10.0
SURVIVE_BONUS = 0.01
HEART_REWARD = 15.0

# Legacy single-int action constants (kept for reference / imports)
LEFT = 0
RIGHT = 1
STAY = 2
SHOOT = 3

# MultiDiscrete([3, 2]) action encoding: [move, fire]
MOVE_LEFT = 0
MOVE_STAY = 1
MOVE_RIGHT = 2
FIRE_NO = 0
FIRE_YES = 1


class SpaceShooterSim:
    """Full Java SpaceShooter ported to numpy.

    KNOWN DEVIATION: Discrete(4) forces one action per tick (Java allows
    simultaneous move+shoot via separate key events).
    """

    def __init__(self, seed=None, max_steps=None, spawn_source=None):
        """
        Args:
            spawn_source: None for normal play (uses internal RNG), or a dict
                ``{"enemy1": iter, "enemy2": iter, "enemy3": iter, "heart": iter}``
                of iterators yielding ``(x, y)`` pairs — consumed in place of
                RNG draws for parity testing.
        """
        self._init_seed = seed
        self._max_steps = max_steps if (max_steps is not None and max_steps > 0) else None
        self._spawn_source = spawn_source
        self._rng = np.random.default_rng(seed)
        self.reset()

    def reset(self, seed=None):
        if seed is not None:
            self._rng = np.random.default_rng(seed)

        self.player_x = PLAYER_START_X
        self.lives = START_LIVES
        self.score = 0
        self.steps = 0

        # Red laser — parked
        self.laser_x = LASER_PARK_X
        self.laser_y = LASER_PARK_Y

        # Enemy1 / NORMAL — initial range: y from [100, 600)
        if self._spawn_source is not None:
            self.enemy1_x, self.enemy1_y = next(self._spawn_source["enemy1"])
        else:
            self.enemy1_x = int(self._rng.integers(0, ENEMY1_SPAWN_X_MAX))
            self.enemy1_y = -int(self._rng.integers(100, 600))

        # Enemy2 / FAST — initial range: y from [1000, 6000)
        if self._spawn_source is not None:
            self.enemy2_x, self.enemy2_y = next(self._spawn_source["enemy2"])
        else:
            self.enemy2_x = int(self._rng.integers(0, ENEMY2_SPAWN_X_MAX))
            self.enemy2_y = -int(self._rng.integers(1000, 6000))

        # Enemy3 / SHOOTER — initial range: y from [300, 1000)
        if self._spawn_source is not None:
            self.enemy3_x, self.enemy3_y = next(self._spawn_source["enemy3"])
        else:
            self.enemy3_x = int(self._rng.integers(0, ENEMY3_SPAWN_X_MAX))
            self.enemy3_y = -int(self._rng.integers(300, 1000))

        # Blue laser — starts at (600, -100), moves +12/tick from game start
        self.blue_x = LASER_PARK_X
        self.blue_y = LASER_PARK_Y

        # Heart — starts at y=2000 (off-screen below; immediately recycled)
        if self._spawn_source is not None:
            self.heart_x, self.heart_y = next(self._spawn_source["heart"])
        else:
            self.heart_x = int(self._rng.integers(0, HEART_SPAWN_X_MAX))
            self.heart_y = HEART_INITIAL_Y

        return self._state()

    # ===================================================================
    # step — one game tick
    # ===================================================================
    def step(self, action):
        reward = 0.0
        move = int(action[0])
        fire = int(action[1])

        # 1. Apply action — move first, then fire -----------------------
        if move == MOVE_LEFT:
            self.player_x -= PLAYER_SPEED
        elif move == MOVE_RIGHT:
            self.player_x += PLAYER_SPEED

        if self.player_x < PLAYER_X_MIN:
            self.player_x = PLAYER_X_MIN
        elif self.player_x > PLAYER_X_MAX:
            self.player_x = PLAYER_X_MAX

        if fire == FIRE_YES and self.laser_y <= LASER_REFIRE_Y:
            self.laser_y = LASER_SPAWN_Y
            self.laser_x = self.player_x + LASER_SPAWN_X_OFFSET

        # 2. Move red laser if in flight --------------------------------
        if self.laser_y > LASER_REFIRE_Y:
            self.laser_y -= LASER_SPEED

        # 3. Move enemies -----------------------------------------------
        self.enemy1_y += ENEMY1_FALL_SPEED
        self.enemy2_y += ENEMY2_FALL_SPEED
        self.enemy3_y += ENEMY3_FALL_SPEED

        # 4. Move heart; move blue laser --------------------------------
        self.heart_y += HEART_SPEED
        self.blue_y += BLUE_LASER_SPEED

        # 5. Collisions (order mirrors Java checkCollision exactly) ------

        # --- blue laser refire (Java line 125) ---
        if self.blue_y >= 1000 and self.enemy3_y > -90:
            self.blue_x = self.enemy3_x + 39
            self.blue_y = self.enemy3_y + 20

        # --- enemy1 bottom (Java line 129) ---
        if self.enemy1_y > GAME_HEIGHT:
            self.lives -= 1
            reward += HIT_PENALTY
            self._recycle_enemy1()

        # --- enemy2 bottom (Java line 136) ---
        if self.enemy2_y > GAME_HEIGHT:
            self.lives -= 1
            reward += HIT_PENALTY
            self._recycle_enemy2(bottom=True)

        # --- enemy3 bottom (Java line 141) ---
        if self.enemy3_y > GAME_HEIGHT:
            self.lives -= 1
            reward += HIT_PENALTY
            self._recycle_enemy3()

        # --- heart missed (Java line 147) ---
        if self.heart_y > 700:
            self._recycle_heart(missed=True)

        # --- laser hits enemy1 (Java line 154) ---
        if (self.laser_x >= self.enemy1_x - 15
                and self.laser_x <= self.enemy1_x + 86
                and self.laser_y <= self.enemy1_y + 75
                and self.laser_y >= self.enemy1_y):
            self.score += KILL_SCORE
            reward += KILL_REWARD_ENEMY1
            self.laser_x = LASER_PARK_X
            self.laser_y = LASER_PARK_Y
            self._recycle_enemy1()

        # --- laser hits enemy2 (Java line 163) ---
        if (self.laser_x >= self.enemy2_x - 15
                and self.laser_x <= self.enemy2_x + 84
                and self.laser_y <= self.enemy2_y + 75
                and self.laser_y >= self.enemy2_y):
            self.score += KILL_SCORE
            reward += KILL_REWARD_ENEMY2
            self.laser_x = LASER_PARK_X
            self.laser_y = LASER_PARK_Y
            self._recycle_enemy2(bottom=False)

        # --- laser hits enemy3 (Java line 171) ---
        if (self.laser_x >= self.enemy3_x - 15
                and self.laser_x <= self.enemy3_x + 96
                and self.laser_y <= self.enemy3_y + 75
                and self.laser_y >= self.enemy3_y):
            self.score += KILL_SCORE
            reward += KILL_REWARD_ENEMY3
            self.laser_x = LASER_PARK_X
            self.laser_y = LASER_PARK_Y
            self._recycle_enemy3()

        # --- enemy1 hits player (Java line 179) ---
        if (self.enemy1_x >= self.player_x - 75
                and self.enemy1_x <= self.player_x + 75
                and self.enemy1_y >= 335):
            self.lives -= 1
            reward += HIT_PENALTY
            self._recycle_enemy1()

        # --- enemy2 hits player (Java line 185) ---
        if (self.enemy2_x >= self.player_x - 75
                and self.enemy2_x <= self.player_x + 75
                and self.enemy2_y >= 335):
            self.lives -= 1
            reward += HIT_PENALTY
            self._recycle_enemy2(bottom=False)

        # --- enemy3 hits player (Java line 191) ---
        if (self.enemy3_x >= self.player_x - 90
                and self.enemy3_x <= self.player_x + 90
                and self.enemy3_y >= 335):
            self.lives -= 1
            reward += HIT_PENALTY
            self._recycle_enemy3()

        # --- blue laser hits player (Java line 196) ---
        if (self.blue_x >= self.player_x - 15
                and self.blue_x <= self.player_x + 82
                and self.blue_y >= 415
                and self.blue_y <= 430):
            self.lives -= 1
            reward += HIT_PENALTY
            self.blue_x = self.enemy3_x + 39
            self.blue_y = self.enemy3_y + 20

        # --- heart pickup (Java line 203) ---
        if (self.heart_x >= self.player_x - 25
                and self.heart_x <= self.player_x + 80
                and self.heart_y >= 405):
            self.lives += 1
            reward += HEART_REWARD
            self._recycle_heart(missed=False)

        # 6. Increment step counter --------------------------------------
        self.steps += 1

        # 7. Terminal check -----------------------------------------------
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

    # ===================================================================
    # Recycle helpers (per-entity, with reason-dependent ranges)
    # ===================================================================

    def _recycle_enemy1(self):
        if self._spawn_source is not None:
            self.enemy1_x, self.enemy1_y = next(self._spawn_source["enemy1"])
        else:
            self.enemy1_x = int(self._rng.integers(0, ENEMY1_SPAWN_X_MAX))
            self.enemy1_y = -int(self._rng.integers(100, 500))

    def _recycle_enemy2(self, bottom):
        if self._spawn_source is not None:
            self.enemy2_x, self.enemy2_y = next(self._spawn_source["enemy2"])
        else:
            self.enemy2_x = int(self._rng.integers(0, ENEMY2_SPAWN_X_MAX))
            if bottom:
                self.enemy2_y = -int(self._rng.integers(1000, 5000))
            else:
                self.enemy2_y = -int(self._rng.integers(1000, 6000))

    def _recycle_enemy3(self):
        if self._spawn_source is not None:
            self.enemy3_x, self.enemy3_y = next(self._spawn_source["enemy3"])
        else:
            self.enemy3_x = int(self._rng.integers(0, ENEMY3_SPAWN_X_MAX))
            self.enemy3_y = -int(self._rng.integers(300, 1000))

    def _recycle_heart(self, missed):
        if self._spawn_source is not None:
            self.heart_x, self.heart_y = next(self._spawn_source["heart"])
        else:
            self.heart_x = int(self._rng.integers(0, HEART_SPAWN_X_MAX))
            if missed:
                self.heart_y = -int(self._rng.integers(3500, 11000))
            else:
                self.heart_y = -int(self._rng.integers(2000, 3000))

    def _state(self):
        return {
            "player_x": self.player_x,
            "lives": self.lives,
            "score": self.score,
            "laser_x": self.laser_x,
            "laser_y": self.laser_y,
            "enemy1_x": self.enemy1_x,
            "enemy1_y": self.enemy1_y,
            "enemy2_x": self.enemy2_x,
            "enemy2_y": self.enemy2_y,
            "enemy3_x": self.enemy3_x,
            "enemy3_y": self.enemy3_y,
            "blue_x": self.blue_x,
            "blue_y": self.blue_y,
            "heart_x": self.heart_x,
            "heart_y": self.heart_y,
            "steps": self.steps,
        }
