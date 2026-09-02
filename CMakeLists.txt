cmake_minimum_required(VERSION 3.15)
project(shooter_sim LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(pybind11 CONFIG REQUIRED)

pybind11_add_module(shooter_cpp
    cpp/src/environment.cpp
    cpp/src/rng.cpp
    cpp/bindings/pybind_module.cpp
)

target_include_directories(shooter_cpp PRIVATE cpp/include)

install(TARGETS shooter_cpp LIBRARY DESTINATION .)
