#include <algorithm>
#include <cstdint>
#include <memory>
#include <utility>
#include <vector>

#include <pybind11/numpy.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "shooter/constants.hpp"
#include "shooter/environment.hpp"
#include "shooter/game_state.hpp"
#include "shooter/types.hpp"

namespace py = pybind11;

static py::array_t<float> make_obs(const GameState& s) {
    auto obs = py::array_t<float>(6);
    auto buf = obs.mutable_unchecked<1>();

    buf(0) = static_cast<float>(s.player_x) / static_cast<float>(PLAYER_X_MAX);
    buf(1) = static_cast<float>(s.lives) / static_cast<float>(START_LIVES);
    buf(2) = (LASER_REFIRE_Y < s.laser_y && s.laser_y <= GAME_HEIGHT) ? 1.0f
                                                                      : 0.0f;
    float ly = static_cast<float>(s.laser_y) / static_cast<float>(GAME_HEIGHT);
    buf(3) = std::clamp(ly, 0.0f, 1.0f);
    buf(4) = static_cast<float>(s.enemy_x - s.player_x) / 500.0f;
    float ey = static_cast<float>(s.enemy_y) / static_cast<float>(GAME_HEIGHT);
    buf(5) = std::clamp(ey, 0.0f, 1.0f);

    return obs;
}

PYBIND11_MODULE(shooter_cpp, m) {
    m.doc() = "C++ SpaceShooter one-enemy simulation";

    py::class_<Environment>(m, "Environment")
        // Normal play: seeded RNG spawn source
        .def(py::init([](int max_steps, uint32_t seed) {
                 auto src = std::make_shared<RngSpawnSource>(seed);
                 return Environment(max_steps, std::move(src));
             }),
             py::arg("max_steps") = 0, py::arg("seed") = 42u)
        // Parity test: pre-computed spawn list
        .def(py::init(
                 [](int max_steps,
                    std::vector<std::pair<int, int>> spawns) {
                     auto src = std::make_shared<VectorSpawnSource>(
                         std::move(spawns));
                     return Environment(max_steps, std::move(src));
                 }),
             py::arg("max_steps"), py::arg("spawns"))
        .def("reset",
             [](Environment& env) {
                 env.reset();
                 return make_obs(env.get_state());
             })
        .def("step",
             [](Environment& env, int action) {
                 auto res = env.step(action);
                 return py::make_tuple(make_obs(env.get_state()), res.reward,
                                       res.done);
             },
             py::arg("action"))
        .def("get_state", [](const Environment& env) {
            const auto& s = env.get_state();
            py::dict d;
            d["player_x"] = s.player_x;
            d["lives"]    = s.lives;
            d["score"]    = s.score;
            d["laser_x"]  = s.laser_x;
            d["laser_y"]  = s.laser_y;
            d["enemy_x"]  = s.enemy_x;
            d["enemy_y"]  = s.enemy_y;
            d["steps"]    = s.steps;
            return d;
        });
}
