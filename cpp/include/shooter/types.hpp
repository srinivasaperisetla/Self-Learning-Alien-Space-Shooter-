#pragma once

#include <memory>
#include <utility>
#include <vector>

enum class Action : int { LEFT = 0, RIGHT = 1, STAY = 2, SHOOT = 3 };

enum class EnemyType { NORMAL, FAST, SHOOTER };

struct StepResult {
    double reward;
    bool   done;
};

// Spawn source interface — only used for parity-test injection.
struct SpawnSource {
    virtual ~SpawnSource() = default;
    virtual std::pair<int, int> next() = 0;
};

class VectorSpawnSource : public SpawnSource {
    std::vector<std::pair<int, int>> spawns_;
    size_t idx_ = 0;

public:
    explicit VectorSpawnSource(std::vector<std::pair<int, int>> spawns)
        : spawns_(std::move(spawns)) {}

    std::pair<int, int> next() override {
        return spawns_.at(idx_++);
    }
};

// Per-entity spawn sources (all may be nullptr for normal play).
struct SpawnSources {
    std::shared_ptr<SpawnSource> enemy1;
    std::shared_ptr<SpawnSource> enemy2;
    std::shared_ptr<SpawnSource> enemy3;
    std::shared_ptr<SpawnSource> heart;
};
