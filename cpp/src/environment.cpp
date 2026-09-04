#include "shooter/environment.hpp"

#include <random>

#include "shooter/constants.hpp"
#include "shooter/types.hpp"

// =====================================================================
// Constructors
// =====================================================================

Environment::Environment(int max_steps, uint32_t seed)
    : max_steps_(max_steps),
      has_max_steps_(max_steps > 0),
      use_injected_(false),
      rng_(seed) {
    reset();
}

Environment::Environment(int max_steps, SpawnSources sources)
    : max_steps_(max_steps),
      has_max_steps_(max_steps > 0),
      sources_(std::move(sources)),
      use_injected_(true),
      rng_(0) {
    reset();
}

// =====================================================================
// Recycle helpers
// =====================================================================

void Environment::recycle_enemy1() {
    if (use_injected_) {
        auto [x, y] = sources_.enemy1->next();
        state_.enemy1_x = x;
        state_.enemy1_y = y;
    } else {
        state_.enemy1_x = std::uniform_int_distribution<int>(0, ENEMY1_SPAWN_X_MAX - 1)(rng_);
        state_.enemy1_y = -std::uniform_int_distribution<int>(100, 499)(rng_);
    }
}

void Environment::recycle_enemy2(bool bottom) {
    if (use_injected_) {
        auto [x, y] = sources_.enemy2->next();
        state_.enemy2_x = x;
        state_.enemy2_y = y;
    } else {
        state_.enemy2_x = std::uniform_int_distribution<int>(0, ENEMY2_SPAWN_X_MAX - 1)(rng_);
        if (bottom) {
            state_.enemy2_y = -std::uniform_int_distribution<int>(1000, 4999)(rng_);
        } else {
            state_.enemy2_y = -std::uniform_int_distribution<int>(1000, 5999)(rng_);
        }
    }
}

void Environment::recycle_enemy3() {
    if (use_injected_) {
        auto [x, y] = sources_.enemy3->next();
        state_.enemy3_x = x;
        state_.enemy3_y = y;
    } else {
        state_.enemy3_x = std::uniform_int_distribution<int>(0, ENEMY3_SPAWN_X_MAX - 1)(rng_);
        state_.enemy3_y = -std::uniform_int_distribution<int>(300, 999)(rng_);
    }
}

void Environment::recycle_heart(bool missed) {
    if (use_injected_) {
        auto [x, y] = sources_.heart->next();
        state_.heart_x = x;
        state_.heart_y = y;
    } else {
        state_.heart_x = std::uniform_int_distribution<int>(0, HEART_SPAWN_X_MAX - 1)(rng_);
        if (missed) {
            state_.heart_y = -std::uniform_int_distribution<int>(3500, 10999)(rng_);
        } else {
            state_.heart_y = -std::uniform_int_distribution<int>(2000, 2999)(rng_);
        }
    }
}

// =====================================================================
// reset
// =====================================================================

GameState Environment::reset() {
    state_.player_x = PLAYER_START_X;
    state_.lives    = START_LIVES;
    state_.score    = 0;
    state_.steps    = 0;
    state_.laser_x  = LASER_PARK_X;
    state_.laser_y  = LASER_PARK_Y;

    // Enemy1 / NORMAL — initial y from [100, 600)
    if (use_injected_) {
        auto [x, y] = sources_.enemy1->next();
        state_.enemy1_x = x;
        state_.enemy1_y = y;
    } else {
        state_.enemy1_x = std::uniform_int_distribution<int>(0, ENEMY1_SPAWN_X_MAX - 1)(rng_);
        state_.enemy1_y = -std::uniform_int_distribution<int>(100, 599)(rng_);
    }

    // Enemy2 / FAST — initial y from [1000, 6000)
    if (use_injected_) {
        auto [x, y] = sources_.enemy2->next();
        state_.enemy2_x = x;
        state_.enemy2_y = y;
    } else {
        state_.enemy2_x = std::uniform_int_distribution<int>(0, ENEMY2_SPAWN_X_MAX - 1)(rng_);
        state_.enemy2_y = -std::uniform_int_distribution<int>(1000, 5999)(rng_);
    }

    // Enemy3 / SHOOTER — initial y from [300, 1000)
    if (use_injected_) {
        auto [x, y] = sources_.enemy3->next();
        state_.enemy3_x = x;
        state_.enemy3_y = y;
    } else {
        state_.enemy3_x = std::uniform_int_distribution<int>(0, ENEMY3_SPAWN_X_MAX - 1)(rng_);
        state_.enemy3_y = -std::uniform_int_distribution<int>(300, 999)(rng_);
    }

    // Blue laser — starts at (600, -100)
    state_.blue_x = LASER_PARK_X;
    state_.blue_y = LASER_PARK_Y;

    // Heart — starts at y=2000
    if (use_injected_) {
        auto [x, y] = sources_.heart->next();
        state_.heart_x = x;
        state_.heart_y = y;
    } else {
        state_.heart_x = std::uniform_int_distribution<int>(0, HEART_SPAWN_X_MAX - 1)(rng_);
        state_.heart_y = HEART_INITIAL_Y;
    }

    return state_;
}

// =====================================================================
// step — one game tick (mirrors env_py.py exactly)
// =====================================================================

StepResult Environment::step(int move, int fire) {
    double reward = 0.0;

    // 1. Apply action — move first, then fire -------------------------
    if (move == 0) {
        state_.player_x -= PLAYER_SPEED;
    } else if (move == 2) {
        state_.player_x += PLAYER_SPEED;
    }

    if (state_.player_x < PLAYER_X_MIN) {
        state_.player_x = PLAYER_X_MIN;
    } else if (state_.player_x > PLAYER_X_MAX) {
        state_.player_x = PLAYER_X_MAX;
    }

    if (fire == 1 && state_.laser_y <= LASER_REFIRE_Y) {
        state_.laser_y = LASER_SPAWN_Y;
        state_.laser_x = state_.player_x + LASER_SPAWN_X_OFFSET;
    }

    // 2. Move red laser -----------------------------------------------
    if (state_.laser_y > LASER_REFIRE_Y) {
        state_.laser_y -= LASER_SPEED;
    }

    // 3. Move enemies -------------------------------------------------
    state_.enemy1_y += ENEMY1_FALL_SPEED;
    state_.enemy2_y += ENEMY2_FALL_SPEED;
    state_.enemy3_y += ENEMY3_FALL_SPEED;

    // 4. Move heart, move blue laser ----------------------------------
    state_.heart_y += HEART_SPEED;
    state_.blue_y  += BLUE_LASER_SPEED;

    // 5. Collisions (order mirrors Java checkCollision) ----------------

    // --- blue laser refire ---
    if (state_.blue_y >= 1000 && state_.enemy3_y > -90) {
        state_.blue_x = state_.enemy3_x + 39;
        state_.blue_y = state_.enemy3_y + 20;
    }

    // --- enemy1 bottom ---
    if (state_.enemy1_y > GAME_HEIGHT) {
        state_.lives -= 1;
        reward += HIT_PENALTY;
        recycle_enemy1();
    }

    // --- enemy2 bottom ---
    if (state_.enemy2_y > GAME_HEIGHT) {
        state_.lives -= 1;
        reward += HIT_PENALTY;
        recycle_enemy2(/*bottom=*/true);
    }

    // --- enemy3 bottom ---
    if (state_.enemy3_y > GAME_HEIGHT) {
        state_.lives -= 1;
        reward += HIT_PENALTY;
        recycle_enemy3();
    }

    // --- heart missed ---
    if (state_.heart_y > 700) {
        recycle_heart(/*missed=*/true);
    }

    // --- laser hits enemy1 ---
    if (state_.laser_x >= state_.enemy1_x - 15 &&
        state_.laser_x <= state_.enemy1_x + 86 &&
        state_.laser_y <= state_.enemy1_y + 75 &&
        state_.laser_y >= state_.enemy1_y) {
        state_.score += KILL_SCORE;
        reward += KILL_REWARD_ENEMY1;
        state_.laser_x = LASER_PARK_X;
        state_.laser_y = LASER_PARK_Y;
        recycle_enemy1();
    }

    // --- laser hits enemy2 ---
    if (state_.laser_x >= state_.enemy2_x - 15 &&
        state_.laser_x <= state_.enemy2_x + 84 &&
        state_.laser_y <= state_.enemy2_y + 75 &&
        state_.laser_y >= state_.enemy2_y) {
        state_.score += KILL_SCORE;
        reward += KILL_REWARD_ENEMY2;
        state_.laser_x = LASER_PARK_X;
        state_.laser_y = LASER_PARK_Y;
        recycle_enemy2(/*bottom=*/false);
    }

    // --- laser hits enemy3 ---
    if (state_.laser_x >= state_.enemy3_x - 15 &&
        state_.laser_x <= state_.enemy3_x + 96 &&
        state_.laser_y <= state_.enemy3_y + 75 &&
        state_.laser_y >= state_.enemy3_y) {
        state_.score += KILL_SCORE;
        reward += KILL_REWARD_ENEMY3;
        state_.laser_x = LASER_PARK_X;
        state_.laser_y = LASER_PARK_Y;
        recycle_enemy3();
    }

    // --- enemy1 hits player ---
    if (state_.enemy1_x >= state_.player_x - 75 &&
        state_.enemy1_x <= state_.player_x + 75 &&
        state_.enemy1_y >= 335) {
        state_.lives -= 1;
        reward += HIT_PENALTY;
        recycle_enemy1();
    }

    // --- enemy2 hits player ---
    if (state_.enemy2_x >= state_.player_x - 75 &&
        state_.enemy2_x <= state_.player_x + 75 &&
        state_.enemy2_y >= 335) {
        state_.lives -= 1;
        reward += HIT_PENALTY;
        recycle_enemy2(/*bottom=*/false);
    }

    // --- enemy3 hits player ---
    if (state_.enemy3_x >= state_.player_x - 90 &&
        state_.enemy3_x <= state_.player_x + 90 &&
        state_.enemy3_y >= 335) {
        state_.lives -= 1;
        reward += HIT_PENALTY;
        recycle_enemy3();
    }

    // --- blue laser hits player ---
    if (state_.blue_x >= state_.player_x - 15 &&
        state_.blue_x <= state_.player_x + 82 &&
        state_.blue_y >= 415 &&
        state_.blue_y <= 430) {
        state_.lives -= 1;
        reward += HIT_PENALTY;
        state_.blue_x = state_.enemy3_x + 39;
        state_.blue_y = state_.enemy3_y + 20;
    }

    // --- heart pickup ---
    if (state_.heart_x >= state_.player_x - 25 &&
        state_.heart_x <= state_.player_x + 80 &&
        state_.heart_y >= 405) {
        state_.lives += 1;
        reward += HEART_REWARD;
        recycle_heart(/*missed=*/false);
    }

    // 6. Increment steps ----------------------------------------------
    state_.steps += 1;

    // 7. Terminal check -----------------------------------------------
    bool death   = state_.lives <= 0;
    bool hit_cap = has_max_steps_ && state_.steps >= max_steps_;
    bool done    = death || hit_cap;

    if (!done) {
        reward += SURVIVE_BONUS;
    }

    return {reward, done};
}
