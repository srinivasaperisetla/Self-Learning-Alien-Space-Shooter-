#pragma once

#include <cstdint>
#include <memory>

#include "shooter/batched_state.hpp"
#include "shooter/constants.hpp"

class ThreadPool;

class BatchedEnvironment {
    BatchedState s_;
    int n_envs_;
    int max_steps_;
    bool has_max_steps_;
    int n_threads_;
    std::unique_ptr<ThreadPool> pool_;

    void reset_env(int i);
    void step_env(int i, int move, int fire,
                  float* obs, float& reward, uint8_t& done_flag);
    void step_range(int lo, int hi,
                    const int* moves, const int* fires,
                    float* obs, float* rewards, uint8_t* dones);

    void recycle_enemy1(int i);
    void recycle_enemy2(int i, bool bottom);
    void recycle_enemy3(int i);
    void recycle_heart(int i, bool missed);

public:
    BatchedEnvironment(int n_envs, int max_steps,
                       uint32_t base_seed, int n_threads);
    ~BatchedEnvironment();

    void reset_all();
    void reset_all_obs(float* out_obs);
    void step(const int* moves, const int* fires,
              float* out_obs, float* out_rewards, uint8_t* out_dones);
    void write_obs(int i, float* buf) const;

    int n_envs() const { return n_envs_; }
    int n_threads() const { return n_threads_; }
};
