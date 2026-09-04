#pragma once

#include <cstdint>
#include <random>
#include <vector>

struct BatchedState {
    std::vector<int> player_x;
    std::vector<int> lives;
    std::vector<int> score;
    std::vector<int> laser_x;
    std::vector<int> laser_y;
    std::vector<int> enemy1_x;
    std::vector<int> enemy1_y;
    std::vector<int> enemy2_x;
    std::vector<int> enemy2_y;
    std::vector<int> enemy3_x;
    std::vector<int> enemy3_y;
    std::vector<int> blue_x;
    std::vector<int> blue_y;
    std::vector<int> heart_x;
    std::vector<int> heart_y;
    std::vector<int> steps;

    std::vector<std::mt19937> rng;

    void resize(int n) {
        player_x.resize(n);  lives.resize(n);   score.resize(n);
        laser_x.resize(n);   laser_y.resize(n);
        enemy1_x.resize(n);  enemy1_y.resize(n);
        enemy2_x.resize(n);  enemy2_y.resize(n);
        enemy3_x.resize(n);  enemy3_y.resize(n);
        blue_x.resize(n);    blue_y.resize(n);
        heart_x.resize(n);   heart_y.resize(n);
        steps.resize(n);
        rng.resize(n);
    }
};
