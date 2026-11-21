/* e1_laser.h (lane eng-e1h): the weapon's laser sight as the renderer draws it. cObjWep::drawLaserSight (hosted
   decision code) decides the line and the dot and calls the engine's setters (services/laser.cpp: EspDrawLaserLine,
   Draw_line3d_222 / Draw_line3d_local_222, drawPoint), which write this state once a tick; the renderer
   (core/draw_e1.c e1_laser_pass) reads it in place and draws what was set in the tick of its picture. */
#pragma once
#include <stdint.h>

#define E1_LASER_LINES 4
typedef struct {
    float p[2][3];      /* end points: world space (view = 0) or view space (view = 1, Draw_line3d_local_222) */
    uint32_t rgb;       /* 0x00RRGGBB at the start; the far end fades by 1 - length / fade */
    float fade;         /* the fade length (the line is clipped to it) */
    float width;        /* the setter's width (EspDrawLaserLine: 1, or 3 in rooms 22C / 228) */
    uint32_t view, ztest;
} E1LaserLine;
typedef struct {
    uint32_t tick;      /* the tick the lines and the dot were set in */
    uint32_t lines;
    E1LaserLine line[E1_LASER_LINES];
    uint32_t dot_tick;  /* the tick the dot was set in */
    float dot[3];       /* the dot's world position */
    float dot_r;        /* its radius, world units */
    uint32_t dot_rgb;
    uint32_t sets, drawn, dots_drawn;   /* counters for the run's report */
} E1Laser;
#ifdef __cplusplus
extern "C" {
#endif
extern E1Laser e1_laser;
#ifdef __cplusplus
}
#endif
