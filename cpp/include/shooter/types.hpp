#pragma once

#include <memory>
#include <random>
#include <utility>
#include <vector>

enum class Action : int { LEFT = 0, RIGHT = 1, STAY = 2, SHOOT = 3 };

enum class EnemyType { NORMAL };

struct StepResult {
    double reward;
    bool   done;
};

struct SpawnSource {
    virtual ~SpawnSource() = default;
    virtual std::pair<int, int> next(bool initial) = 0;
};

class VectorSpawnSource : public SpawnSource {
    std::vector<std::pair<int, int>> spawns_;
    size_t idx_ = 0;

public:
    explicit VectorSpawnSource(std::vector<std::pair<int, int>> spawns)
        : spawns_(std::move(spawns)) {}

    std::pair<int, int> next(bool /*initial*/) override {
        return spawns_.at(idx_++);
    }
};

class RngSpawnSource : public SpawnSource {
    std::mt19937 rng_;

public:
    explicit RngSpawnSource(uint32_t seed) : rng_(seed) {}
    std::pair<int, int> next(bool initial) override;
};
