#pragma once

#include <memory>
#include <random>

#include "shooter/constants.hpp"
#include "shooter/game_state.hpp"
#include "shooter/types.hpp"

class Environment {
    GameState    state_;
    int          max_steps_;
    bool         has_max_steps_;

    // Parity-test injection (all nullptr for normal play)
    SpawnSources sources_;
    bool         use_injected_;

    // Internal RNG for normal play
    std::mt19937 rng_;

    // Recycle helpers
    void recycle_enemy1();
    void recycle_enemy2(bool bottom);
    void recycle_enemy3();
    void recycle_heart(bool missed);

public:
    // Normal play — seeded internal RNG
    Environment(int max_steps, uint32_t seed);

    // Parity test — injected per-entity spawn sources
    Environment(int max_steps, SpawnSources sources);

    GameState  reset();
    StepResult step(int action);

    const GameState& get_state() const { return state_; }
};
