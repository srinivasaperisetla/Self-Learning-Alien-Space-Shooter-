#include "shooter/batched_environment.hpp"

#include <algorithm>
#include <random>
#include <thread>

#include "shooter/constants.hpp"
#include "shooter/thread_pool.hpp"

static constexpr int OBS_DIM = 19;

// =====================================================================
// Constructor / destructor
// =====================================================================

BatchedEnvironment::BatchedEnvironment(int n_envs, int max_steps,
                                       uint32_t base_seed, int n_threads)
    : n_envs_(n_envs),
      max_steps_(max_steps),
      has_max_steps_(max_steps > 0),
      n_threads_(n_threads > 0 ? n_threads
                               : std::max(1, static_cast<int>(
                                     std::thread::hardware_concurrency()))) {
    s_.resize(n_envs);
    for (int i = 0; i < n_envs; ++i)
        s_.rng[i].seed(base_seed + static_cast<uint32_t>(i));

    if (n_threads_ > 1)
        pool_ = std::make_unique<ThreadPool>(n_threads_);

    reset_all();
}

BatchedEnvironment::~BatchedEnvironment() = default;

// =====================================================================
// Reset
// =====================================================================

void BatchedEnvironment::reset_env(int i) {
    auto& rng = s_.rng[i];
    s_.player_x[i] = PLAYER_START_X;
    s_.lives[i]    = START_LIVES;
    s_.score[i]    = 0;
    s_.steps[i]    = 0;
    s_.laser_x[i]  = LASER_PARK_X;
    s_.laser_y[i]  = LASER_PARK_Y;

    s_.enemy1_x[i] = std::uniform_int_distribution<int>(0, ENEMY1_SPAWN_X_MAX - 1)(rng);
    s_.enemy1_y[i] = -std::uniform_int_distribution<int>(100, 599)(rng);

    s_.enemy2_x[i] = std::uniform_int_distribution<int>(0, ENEMY2_SPAWN_X_MAX - 1)(rng);
    s_.enemy2_y[i] = -std::uniform_int_distribution<int>(1000, 5999)(rng);

    s_.enemy3_x[i] = std::uniform_int_distribution<int>(0, ENEMY3_SPAWN_X_MAX - 1)(rng);
    s_.enemy3_y[i] = -std::uniform_int_distribution<int>(300, 999)(rng);

    s_.blue_x[i] = LASER_PARK_X;
    s_.blue_y[i] = LASER_PARK_Y;

    s_.heart_x[i] = std::uniform_int_distribution<int>(0, HEART_SPAWN_X_MAX - 1)(rng);
    s_.heart_y[i] = HEART_INITIAL_Y;
}

void BatchedEnvironment::reset_all() {
    for (int i = 0; i < n_envs_; ++i) reset_env(i);
}

void BatchedEnvironment::reset_all_obs(float* out_obs) {
    reset_all();
    for (int i = 0; i < n_envs_; ++i) write_obs(i, out_obs + i * OBS_DIM);
}

// =====================================================================
// Recycle helpers (identical to Environment, using SoA + per-env RNG)
// =====================================================================

void BatchedEnvironment::recycle_enemy1(int i) {
    auto& rng = s_.rng[i];
    s_.enemy1_x[i] = std::uniform_int_distribution<int>(0, ENEMY1_SPAWN_X_MAX - 1)(rng);
    s_.enemy1_y[i] = -std::uniform_int_distribution<int>(100, 499)(rng);
}

void BatchedEnvironment::recycle_enemy2(int i, bool bottom) {
    auto& rng = s_.rng[i];
    s_.enemy2_x[i] = std::uniform_int_distribution<int>(0, ENEMY2_SPAWN_X_MAX - 1)(rng);
    if (bottom) {
        s_.enemy2_y[i] = -std::uniform_int_distribution<int>(1000, 4999)(rng);
    } else {
        s_.enemy2_y[i] = -std::uniform_int_distribution<int>(1000, 5999)(rng);
    }
}

void BatchedEnvironment::recycle_enemy3(int i) {
    auto& rng = s_.rng[i];
    s_.enemy3_x[i] = std::uniform_int_distribution<int>(0, ENEMY3_SPAWN_X_MAX - 1)(rng);
    s_.enemy3_y[i] = -std::uniform_int_distribution<int>(300, 999)(rng);
}

void BatchedEnvironment::recycle_heart(int i, bool missed) {
    auto& rng = s_.rng[i];
    s_.heart_x[i] = std::uniform_int_distribution<int>(0, HEART_SPAWN_X_MAX - 1)(rng);
    if (missed) {
        s_.heart_y[i] = -std::uniform_int_distribution<int>(3500, 10999)(rng);
    } else {
        s_.heart_y[i] = -std::uniform_int_distribution<int>(2000, 2999)(rng);
    }
}

// =====================================================================
// Obs — identical formula to pybind make_obs
// =====================================================================

void BatchedEnvironment::write_obs(int i, float* buf) const {
    const float px = static_cast<float>(s_.player_x[i]);
    const float gh = static_cast<float>(GAME_HEIGHT);

    buf[0]  = px / static_cast<float>(PLAYER_X_MAX);
    buf[1]  = static_cast<float>(s_.lives[i]) / static_cast<float>(START_LIVES);
    buf[2]  = (LASER_REFIRE_Y < s_.laser_y[i] && s_.laser_y[i] <= GAME_HEIGHT)
                  ? 1.0f : 0.0f;
    buf[3]  = std::clamp(static_cast<float>(s_.laser_y[i]) / gh, 0.0f, 1.0f);

    buf[4]  = (static_cast<float>(s_.enemy1_x[i]) - px) / 500.0f;
    buf[5]  = std::clamp(static_cast<float>(s_.enemy1_y[i]) / gh, 0.0f, 1.0f);
    buf[6]  = (static_cast<float>(s_.enemy2_x[i]) - px) / 500.0f;
    buf[7]  = std::clamp(static_cast<float>(s_.enemy2_y[i]) / gh, 0.0f, 1.0f);
    buf[8]  = (static_cast<float>(s_.enemy3_x[i]) - px) / 500.0f;
    buf[9]  = std::clamp(static_cast<float>(s_.enemy3_y[i]) / gh, 0.0f, 1.0f);

    buf[10] = (static_cast<float>(s_.blue_x[i]) - px) / 500.0f;
    buf[11] = std::clamp(static_cast<float>(s_.blue_y[i]) / gh, 0.0f, 1.0f);
    buf[12] = (static_cast<float>(s_.heart_x[i]) - px) / 500.0f;
    buf[13] = std::clamp(static_cast<float>(s_.heart_y[i]) / gh, 0.0f, 1.0f);

    buf[14] = static_cast<float>(ENEMY1_FALL_SPEED) / 7.0f;
    buf[15] = static_cast<float>(ENEMY2_FALL_SPEED) / 7.0f;
    buf[16] = static_cast<float>(ENEMY3_FALL_SPEED) / 7.0f;

    const bool blue_active = (s_.blue_y[i] >= 0 && s_.blue_y[i] <= GAME_HEIGHT);
    buf[17] = blue_active ? 1.0f : 0.0f;
    buf[18] = blue_active ? (static_cast<float>(BLUE_LASER_SPEED) / 12.0f)
                          : 0.0f;
}

// =====================================================================
// step_env — identical logic to Environment::step(), SoA layout
// =====================================================================

void BatchedEnvironment::step_env(int i, int move, int fire,
                                   float* obs, float& reward,
                                   uint8_t& done_flag) {
    double rew = 0.0;

    // 1. Apply action — move first, then fire -------------------------
    if (move == 0)      s_.player_x[i] -= PLAYER_SPEED;
    else if (move == 2) s_.player_x[i] += PLAYER_SPEED;

    if (s_.player_x[i] < PLAYER_X_MIN)       s_.player_x[i] = PLAYER_X_MIN;
    else if (s_.player_x[i] > PLAYER_X_MAX)  s_.player_x[i] = PLAYER_X_MAX;

    if (fire == 1 && s_.laser_y[i] <= LASER_REFIRE_Y) {
        s_.laser_y[i] = LASER_SPAWN_Y;
        s_.laser_x[i] = s_.player_x[i] + LASER_SPAWN_X_OFFSET;
    }

    // 2. Move red laser -----------------------------------------------
    if (s_.laser_y[i] > LASER_REFIRE_Y) s_.laser_y[i] -= LASER_SPEED;

    // 3. Move enemies -------------------------------------------------
    s_.enemy1_y[i] += ENEMY1_FALL_SPEED;
    s_.enemy2_y[i] += ENEMY2_FALL_SPEED;
    s_.enemy3_y[i] += ENEMY3_FALL_SPEED;

    // 4. Move heart, move blue laser ----------------------------------
    s_.heart_y[i] += HEART_SPEED;
    s_.blue_y[i]  += BLUE_LASER_SPEED;

    // 5. Collisions (order mirrors Java / Environment::step) ----------

    // blue laser refire
    if (s_.blue_y[i] >= 1000 && s_.enemy3_y[i] > -90) {
        s_.blue_x[i] = s_.enemy3_x[i] + 39;
        s_.blue_y[i] = s_.enemy3_y[i] + 20;
    }

    // enemy1 bottom
    if (s_.enemy1_y[i] > GAME_HEIGHT) {
        s_.lives[i] -= 1; rew += HIT_PENALTY; recycle_enemy1(i);
    }
    // enemy2 bottom
    if (s_.enemy2_y[i] > GAME_HEIGHT) {
        s_.lives[i] -= 1; rew += HIT_PENALTY; recycle_enemy2(i, true);
    }
    // enemy3 bottom
    if (s_.enemy3_y[i] > GAME_HEIGHT) {
        s_.lives[i] -= 1; rew += HIT_PENALTY; recycle_enemy3(i);
    }

    // heart missed
    if (s_.heart_y[i] > 700) { recycle_heart(i, true); }

    // laser hits enemy1
    if (s_.laser_x[i] >= s_.enemy1_x[i] - 15 &&
        s_.laser_x[i] <= s_.enemy1_x[i] + 86 &&
        s_.laser_y[i] <= s_.enemy1_y[i] + 75 &&
        s_.laser_y[i] >= s_.enemy1_y[i]) {
        s_.score[i] += KILL_SCORE; rew += KILL_REWARD_ENEMY1;
        s_.laser_x[i] = LASER_PARK_X; s_.laser_y[i] = LASER_PARK_Y;
        recycle_enemy1(i);
    }
    // laser hits enemy2
    if (s_.laser_x[i] >= s_.enemy2_x[i] - 15 &&
        s_.laser_x[i] <= s_.enemy2_x[i] + 84 &&
        s_.laser_y[i] <= s_.enemy2_y[i] + 75 &&
        s_.laser_y[i] >= s_.enemy2_y[i]) {
        s_.score[i] += KILL_SCORE; rew += KILL_REWARD_ENEMY2;
        s_.laser_x[i] = LASER_PARK_X; s_.laser_y[i] = LASER_PARK_Y;
        recycle_enemy2(i, false);
    }
    // laser hits enemy3
    if (s_.laser_x[i] >= s_.enemy3_x[i] - 15 &&
        s_.laser_x[i] <= s_.enemy3_x[i] + 96 &&
        s_.laser_y[i] <= s_.enemy3_y[i] + 75 &&
        s_.laser_y[i] >= s_.enemy3_y[i]) {
        s_.score[i] += KILL_SCORE; rew += KILL_REWARD_ENEMY3;
        s_.laser_x[i] = LASER_PARK_X; s_.laser_y[i] = LASER_PARK_Y;
        recycle_enemy3(i);
    }

    // enemy1 hits player
    if (s_.enemy1_x[i] >= s_.player_x[i] - 75 &&
        s_.enemy1_x[i] <= s_.player_x[i] + 75 &&
        s_.enemy1_y[i] >= 335) {
        s_.lives[i] -= 1; rew += HIT_PENALTY; recycle_enemy1(i);
    }
    // enemy2 hits player
    if (s_.enemy2_x[i] >= s_.player_x[i] - 75 &&
        s_.enemy2_x[i] <= s_.player_x[i] + 75 &&
        s_.enemy2_y[i] >= 335) {
        s_.lives[i] -= 1; rew += HIT_PENALTY; recycle_enemy2(i, false);
    }
    // enemy3 hits player
    if (s_.enemy3_x[i] >= s_.player_x[i] - 90 &&
        s_.enemy3_x[i] <= s_.player_x[i] + 90 &&
        s_.enemy3_y[i] >= 335) {
        s_.lives[i] -= 1; rew += HIT_PENALTY; recycle_enemy3(i);
    }

    // blue laser hits player
    if (s_.blue_x[i] >= s_.player_x[i] - 15 &&
        s_.blue_x[i] <= s_.player_x[i] + 82 &&
        s_.blue_y[i] >= 415 &&
        s_.blue_y[i] <= 430) {
        s_.lives[i] -= 1; rew += HIT_PENALTY;
        s_.blue_x[i] = s_.enemy3_x[i] + 39;
        s_.blue_y[i] = s_.enemy3_y[i] + 20;
    }

    // heart pickup
    if (s_.heart_x[i] >= s_.player_x[i] - 25 &&
        s_.heart_x[i] <= s_.player_x[i] + 80 &&
        s_.heart_y[i] >= 405) {
        s_.lives[i] += 1; rew += HEART_REWARD; recycle_heart(i, false);
    }

    // 6. Steps --------------------------------------------------------
    s_.steps[i] += 1;

    // 7. Terminal check -----------------------------------------------
    bool death   = s_.lives[i] <= 0;
    bool hit_cap = has_max_steps_ && s_.steps[i] >= max_steps_;
    bool is_done = death || hit_cap;

    if (!is_done) rew += SURVIVE_BONUS;

    reward = static_cast<float>(rew);
    done_flag = is_done ? 1 : 0;

    if (is_done) reset_env(i);

    write_obs(i, obs);
}

// =====================================================================
// step_range / step (parallelised via ThreadPool)
// =====================================================================

void BatchedEnvironment::step_range(int lo, int hi,
                                     const int* moves, const int* fires,
                                     float* obs, float* rewards,
                                     uint8_t* dones) {
    for (int i = lo; i < hi; ++i) {
        step_env(i, moves[i], fires[i],
                 obs + i * OBS_DIM, rewards[i], dones[i]);
    }
}

void BatchedEnvironment::step(const int* moves, const int* fires,
                               float* out_obs, float* out_rewards,
                               uint8_t* out_dones) {
    if (n_threads_ <= 1 || !pool_) {
        step_range(0, n_envs_, moves, fires, out_obs, out_rewards, out_dones);
    } else {
        pool_->run(n_envs_, [&](int lo, int hi) {
            step_range(lo, hi, moves, fires, out_obs, out_rewards, out_dones);
        });
    }
}
