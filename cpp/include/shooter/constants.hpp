#pragma once

// All constants match shooter_rl/prototype/env_py.py exactly.

inline constexpr int GAME_WIDTH  = 500;
inline constexpr int GAME_HEIGHT = 500;

inline constexpr int PLAYER_START_X = 200;
inline constexpr int PLAYER_Y      = 415;
inline constexpr int PLAYER_SPEED  = 10;
inline constexpr int PLAYER_X_MIN  = 0;
inline constexpr int PLAYER_X_MAX  = 417;

inline constexpr int ENEMY_FALL_SPEED = 3;

inline constexpr int LASER_SPEED          = 12;
inline constexpr int LASER_SPAWN_Y        = 400;
inline constexpr int LASER_SPAWN_X_OFFSET = 32;
inline constexpr int LASER_REFIRE_Y       = 0;
inline constexpr int LASER_PARK_X         = 600;
inline constexpr int LASER_PARK_Y         = -100;

inline constexpr int START_LIVES = 3;
inline constexpr int KILL_SCORE  = 10;

inline constexpr double KILL_REWARD    = 10.0;
inline constexpr double HIT_PENALTY   = -10.0;
inline constexpr double SURVIVE_BONUS  = 0.01;
