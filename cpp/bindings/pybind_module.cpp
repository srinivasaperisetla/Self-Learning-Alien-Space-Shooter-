#include <algorithm>
#include <chrono>
#include <cstdint>
#include <memory>
#include <random>
#include <string>
#include <utility>
#include <vector>

#include <pybind11/numpy.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "shooter/batched_environment.hpp"
#include "shooter/constants.hpp"
#include "shooter/environment.hpp"
#include "shooter/game_state.hpp"
#include "shooter/types.hpp"

namespace py = pybind11;

static constexpr int OBS_DIM = 19;

// ---- single-env obs (unchanged) ------------------------------------

static py::array_t<float> make_obs(const GameState& s) {
    auto obs = py::array_t<float>(OBS_DIM);
    auto buf = obs.mutable_unchecked<1>();

    const float px = static_cast<float>(s.player_x);
    const float gh = static_cast<float>(GAME_HEIGHT);

    buf(0)  = px / static_cast<float>(PLAYER_X_MAX);
    buf(1)  = static_cast<float>(s.lives) / static_cast<float>(START_LIVES);
    buf(2)  = (LASER_REFIRE_Y < s.laser_y && s.laser_y <= GAME_HEIGHT)
                  ? 1.0f : 0.0f;
    buf(3)  = std::clamp(static_cast<float>(s.laser_y) / gh, 0.0f, 1.0f);

    buf(4)  = (static_cast<float>(s.enemy1_x) - px) / 500.0f;
    buf(5)  = std::clamp(static_cast<float>(s.enemy1_y) / gh, 0.0f, 1.0f);
    buf(6)  = (static_cast<float>(s.enemy2_x) - px) / 500.0f;
    buf(7)  = std::clamp(static_cast<float>(s.enemy2_y) / gh, 0.0f, 1.0f);
    buf(8)  = (static_cast<float>(s.enemy3_x) - px) / 500.0f;
    buf(9)  = std::clamp(static_cast<float>(s.enemy3_y) / gh, 0.0f, 1.0f);

    buf(10) = (static_cast<float>(s.blue_x) - px) / 500.0f;
    buf(11) = std::clamp(static_cast<float>(s.blue_y) / gh, 0.0f, 1.0f);
    buf(12) = (static_cast<float>(s.heart_x) - px) / 500.0f;
    buf(13) = std::clamp(static_cast<float>(s.heart_y) / gh, 0.0f, 1.0f);

    buf(14) = static_cast<float>(ENEMY1_FALL_SPEED) / 7.0f;
    buf(15) = static_cast<float>(ENEMY2_FALL_SPEED) / 7.0f;
    buf(16) = static_cast<float>(ENEMY3_FALL_SPEED) / 7.0f;

    const bool blue_active = (s.blue_y >= 0 && s.blue_y <= GAME_HEIGHT);
    buf(17) = blue_active ? 1.0f : 0.0f;
    buf(18) = blue_active ? (static_cast<float>(BLUE_LASER_SPEED) / 12.0f)
                          : 0.0f;
    return obs;
}

// =====================================================================
PYBIND11_MODULE(shooter_cpp, m) {
    m.doc() = "C++ SpaceShooter simulation (single + batched)";

    // ---- single Environment (parity reference, unchanged) -----------
    py::class_<Environment>(m, "Environment")
        .def(py::init([](int max_steps, uint32_t seed) {
                 return Environment(max_steps, seed);
             }),
             py::arg("max_steps") = 0, py::arg("seed") = 42u)
        .def(py::init(
                 [](int max_steps, py::dict spawns_dict) {
                     auto e1 = spawns_dict["enemy1"]
                                   .cast<std::vector<std::pair<int, int>>>();
                     auto e2 = spawns_dict["enemy2"]
                                   .cast<std::vector<std::pair<int, int>>>();
                     auto e3 = spawns_dict["enemy3"]
                                   .cast<std::vector<std::pair<int, int>>>();
                     auto h = spawns_dict["heart"]
                                  .cast<std::vector<std::pair<int, int>>>();
                     SpawnSources sources{
                         std::make_shared<VectorSpawnSource>(std::move(e1)),
                         std::make_shared<VectorSpawnSource>(std::move(e2)),
                         std::make_shared<VectorSpawnSource>(std::move(e3)),
                         std::make_shared<VectorSpawnSource>(std::move(h)),
                     };
                     return Environment(max_steps, std::move(sources));
                 }),
             py::arg("max_steps"), py::arg("spawns"))
        .def("reset",
             [](Environment& env) {
                 env.reset();
                 return make_obs(env.get_state());
             })
        .def("step",
             [](Environment& env, int move, int fire) {
                 auto res = env.step(move, fire);
                 return py::make_tuple(make_obs(env.get_state()), res.reward,
                                       res.done);
             },
             py::arg("move"), py::arg("fire"))
        .def("get_state", [](const Environment& env) {
            const auto& s = env.get_state();
            py::dict d;
            d["player_x"]  = s.player_x;
            d["lives"]     = s.lives;
            d["score"]     = s.score;
            d["laser_x"]   = s.laser_x;
            d["laser_y"]   = s.laser_y;
            d["enemy1_x"]  = s.enemy1_x;
            d["enemy1_y"]  = s.enemy1_y;
            d["enemy2_x"]  = s.enemy2_x;
            d["enemy2_y"]  = s.enemy2_y;
            d["enemy3_x"]  = s.enemy3_x;
            d["enemy3_y"]  = s.enemy3_y;
            d["blue_x"]    = s.blue_x;
            d["blue_y"]    = s.blue_y;
            d["heart_x"]   = s.heart_x;
            d["heart_y"]   = s.heart_y;
            d["steps"]     = s.steps;
            return d;
        });

    // ---- BatchedEnvironment (SoA + threading) -----------------------
    py::class_<BatchedEnvironment>(m, "BatchedEnvironment")
        .def(py::init<int, int, uint32_t, int>(),
             py::arg("n_envs"),
             py::arg("max_steps") = 0,
             py::arg("base_seed") = 42u,
             py::arg("n_threads") = 0)
        .def("reset_all",
             [](BatchedEnvironment& b) {
                 int n = b.n_envs();
                 auto obs = py::array_t<float>({n, OBS_DIM});
                 b.reset_all_obs(obs.mutable_data());
                 return obs;
             })
        .def("step",
             [](BatchedEnvironment& b,
                py::array_t<int, py::array::c_style | py::array::forcecast> moves,
                py::array_t<int, py::array::c_style | py::array::forcecast> fires) {
                 int n = b.n_envs();
                 auto obs = py::array_t<float>({n, OBS_DIM});
                 auto rew = py::array_t<float>(n);
                 auto dones = py::array_t<uint8_t>(n);

                 b.step(moves.data(), fires.data(),
                        obs.mutable_data(), rew.mutable_data(),
                        dones.mutable_data());

                 return py::make_tuple(obs, rew, dones);
             },
             py::arg("moves"), py::arg("fires"))
        .def_property_readonly("n_envs", &BatchedEnvironment::n_envs)
        .def_property_readonly("n_threads", &BatchedEnvironment::n_threads);

    // ---- benchmark helpers (pure C++, no Python overhead) -----------

    m.def("benchmark_single_env",
          [](int n_steps, uint32_t seed) -> double {
              Environment env(0, seed);
              std::mt19937 rng(seed + 99);
              std::uniform_int_distribution<int> m_dist(0, 2);
              std::uniform_int_distribution<int> f_dist(0, 1);

              auto t0 = std::chrono::high_resolution_clock::now();
              for (int i = 0; i < n_steps; ++i) {
                  auto res = env.step(m_dist(rng), f_dist(rng));
                  if (res.done) env.reset();
              }
              auto t1 = std::chrono::high_resolution_clock::now();
              return std::chrono::duration<double>(t1 - t0).count();
          },
          py::arg("n_steps"), py::arg("seed") = 42u,
          "Step a single Environment n_steps times in a tight C++ loop, "
          "return elapsed seconds.");

    m.def("benchmark_batched_env",
          [](int n_envs, int n_iters, int n_threads, uint32_t seed) -> double {
              BatchedEnvironment batch(n_envs, 0, seed, n_threads);

              std::vector<int> moves(n_envs);
              std::vector<int> fires(n_envs);
              std::vector<float> obs(n_envs * OBS_DIM);
              std::vector<float> rewards(n_envs);
              std::vector<uint8_t> dones(n_envs);

              std::mt19937 rng(seed + 99);
              std::uniform_int_distribution<int> m_dist(0, 2);
              std::uniform_int_distribution<int> f_dist(0, 1);

              auto t0 = std::chrono::high_resolution_clock::now();
              for (int it = 0; it < n_iters; ++it) {
                  for (int i = 0; i < n_envs; ++i) {
                      moves[i] = m_dist(rng);
                      fires[i] = f_dist(rng);
                  }
                  batch.step(moves.data(), fires.data(),
                             obs.data(), rewards.data(), dones.data());
              }
              auto t1 = std::chrono::high_resolution_clock::now();
              return std::chrono::duration<double>(t1 - t0).count();
          },
          py::arg("n_envs"), py::arg("n_iters"),
          py::arg("n_threads") = 0, py::arg("seed") = 42u,
          "Step a BatchedEnvironment (n_envs × n_iters) in C++, "
          "return elapsed seconds.");
}
