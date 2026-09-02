#pragma once

struct GameState {
    int player_x = 0;
    int lives    = 0;
    int score    = 0;
    int laser_x  = 0;
    int laser_y  = 0;
    int enemy_x  = 0;
    int enemy_y  = 0;
    int steps    = 0;
};
