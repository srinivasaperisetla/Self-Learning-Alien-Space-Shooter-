cmake_minimum_required(VERSION 3.15)
project(shooter_sim LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Release build: -O3 for throughput.  scikit-build-core sets Release by default.
if(CMAKE_BUILD_TYPE STREQUAL "Release" OR NOT CMAKE_BUILD_TYPE)
    set(CMAKE_CXX_FLAGS_RELEASE "-O3 -DNDEBUG")
endif()

option(SHOOTER_NATIVE "Enable -march=native (non-portable)" OFF)
if(SHOOTER_NATIVE)
    add_compile_options(-march=native)
endif()

find_package(pybind11 CONFIG REQUIRED)

pybind11_add_module(shooter_cpp
    cpp/src/environment.cpp
    cpp/src/rng.cpp
    cpp/src/batched_environment.cpp
    cpp/bindings/pybind_module.cpp
)

target_include_directories(shooter_cpp PRIVATE cpp/include)

# Threading support
find_package(Threads REQUIRED)
target_link_libraries(shooter_cpp PRIVATE Threads::Threads)

install(TARGETS shooter_cpp LIBRARY DESTINATION .)
