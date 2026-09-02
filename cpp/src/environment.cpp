#include "shooter/environment.hpp"

#include "shooter/constants.hpp"
#include "shooter/types.hpp"

Environment::Environment(int max_steps,
                         std::shared_ptr<SpawnSource> source)
    : source_(std::move(source)),
      max_steps_(max_steps),
      has_max_steps_(max_steps > 0) {
    reset();
}

GameState Environment::reset() {
    state_.player_x = PLAYER_START_X;
    state_.lives    = START_LIVES;
    state_.score    = 0;
    state_.steps    = 0;
    state_.laser_x  = LASER_PARK_X;
    state_.laser_y  = LASER_PARK_Y;

    auto [x, y]   = source_->next(/*initial=*/true);
    state_.enemy_x = x;
    state_.enemy_y = y;

    return state_;
}

void Environment::recycle_enemy() {
    auto [x, y]   = source_->next(/*initial=*/false);
    state_.enemy_x = x;
    state_.enemy_y = y;
}

StepResult Environment::step(int action) {
    double reward = 0.0;

    // 1. Apply action -------------------------------------------------
    if (action == static_cast<int>(Action::LEFT)) {
        state_.player_x -= PLAYER_SPEED;
    } else if (action == static_cast<int>(Action::RIGHT)) {
        state_.player_x += PLAYER_SPEED;
    } else if (action == static_cast<int>(Action::SHOOT)) {
        if (state_.laser_y <= LASER_REFIRE_Y) {
            state_.laser_y = LASER_SPAWN_Y;
            state_.laser_x = state_.player_x + LASER_SPAWN_X_OFFSET;
        }
    }

    // Clamp player
    if (state_.player_x < PLAYER_X_MIN) {
        state_.player_x = PLAYER_X_MIN;
    } else if (state_.player_x > PLAYER_X_MAX) {
        state_.player_x = PLAYER_X_MAX;
    }

    // 2. Move laser if in flight --------------------------------------
    if (state_.laser_y > LASER_REFIRE_Y) {
        state_.laser_y -= LASER_SPEED;
    }

    // 3. Move enemy ---------------------------------------------------
    state_.enemy_y += ENEMY_FALL_SPEED;

    // 4. Collisions (B, A, C — matches Python order, NOT Java order) --

    // B — enemy reaches bottom
    if (state_.enemy_y > GAME_HEIGHT) {
        state_.lives -= 1;
        reward += HIT_PENALTY;
        recycle_enemy();
    }

    // A — laser hits enemy
    if (state_.laser_x >= state_.enemy_x - 15 &&
        state_.laser_x <= state_.enemy_x + 86 &&
        state_.laser_y <= state_.enemy_y + 75 &&
        state_.laser_y >= state_.enemy_y) {
        state_.score += KILL_SCORE;
        reward += KILL_REWARD;
        state_.laser_x = LASER_PARK_X;
        state_.laser_y = LASER_PARK_Y;
        recycle_enemy();
    }

    // C — enemy hits player
    if (state_.enemy_x >= state_.player_x - 75 &&
        state_.enemy_x <= state_.player_x + 75 &&
        state_.enemy_y >= 335) {
        state_.lives -= 1;
        reward += HIT_PENALTY;
        recycle_enemy();
    }

    // 5. Increment steps ----------------------------------------------
    state_.steps += 1;

    // 6. Terminal check -----------------------------------------------
    bool death   = state_.lives <= 0;
    bool hit_cap = has_max_steps_ && state_.steps >= max_steps_;
    bool done    = death || hit_cap;

    if (!done) {
        reward += SURVIVE_BONUS;
    }

    return {reward, done};
}
