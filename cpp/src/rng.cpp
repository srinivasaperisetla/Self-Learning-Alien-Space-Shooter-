#include "shooter/types.hpp"

#include <random>

std::pair<int, int> RngSpawnSource::next(bool initial) {
    std::uniform_int_distribution<int> x_dist(0, 414);
    int x = x_dist(rng_);

    int y;
    if (initial) {
        std::uniform_int_distribution<int> y_dist(100, 599);
        y = -y_dist(rng_);
    } else {
        std::uniform_int_distribution<int> y_dist(100, 499);
        y = -y_dist(rng_);
    }

    return {x, y};
}
