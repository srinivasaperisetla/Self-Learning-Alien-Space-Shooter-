#pragma once

#include <memory>

#include "shooter/constants.hpp"
#include "shooter/game_state.hpp"
#include "shooter/types.hpp"

class Environment {
    GameState                    state_;
    std::shared_ptr<SpawnSource> source_;
    int                          max_steps_;
    bool                         has_max_steps_;

    void recycle_enemy();

public:
    Environment(int max_steps, std::shared_ptr<SpawnSource> source);

    GameState  reset();
    StepResult step(int action);

    const GameState& get_state() const { return state_; }
};
