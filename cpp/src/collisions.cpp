// Collision logic is inlined in environment.cpp (step method, section 4) to
// keep the C++ a verbatim 1:1 mirror of the Python step() function.
//
// The three checks, applied in B-A-C order:
//   B) enemy_y > GAME_HEIGHT            — enemy reaches bottom
//   A) laser box test                   — laser hits enemy
//   C) enemy box test vs player_x, 335  — enemy hits player
//
// See environment.cpp for the exact operators and constants.
