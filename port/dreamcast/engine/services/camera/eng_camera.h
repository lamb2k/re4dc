/* eng_camera.h: the camera service's record, which is the renderer's camera (lane eng-e1j, ruling H-016.1 / .2).
 *
 * The camera service (services/camera/camera_svc.cpp, CameraMove) writes this record once a tick, after the hosted
 * controller has chosen the camera: the view matrix and the projection terms the renderer uses, then the camera it
 * evaluated. The renderer reads it in place (core/draw_e1.c points the scene's camera stream at it once, at open):
 * nothing copies the camera into another layout. The first 26 words are the renderer's camera stream layout (the
 * E0 bench's, render/native_scene.inc checks a pack's stream 0 is 26 words). C and C++. */
#ifndef ENG_CAMERA_H
#define ENG_CAMERA_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif

typedef struct EngCamera {
    float view[3][4];     /* [0..11] world to view, rows right / up / look, the last column the translation */
    float proj_type;      /* [12] 0: perspective (the renderer draws perspective only) */
    float p00, p02, p11, p12, p22, p23;   /* [13..18] the projection's terms: x scale, x shift, y scale, y shift,
                                             depth scale, depth offset (near = p23 / (p22 - 1)) */
    float viewport[6];    /* [19..24] x, y, width, height, near depth, far depth */
    float zfar;           /* [25] the far plane */
    /* the camera the service evaluated this tick (past the renderer's words) */
    float eye[3], target[3], roll, fovy;
    uint32_t tick;        /* writes so far (one a tick while the camera is live) */
    uint32_t frozen;      /* CAMSTALE lab arm (control): the record keeps the room's first camera */
} EngCamera;

extern EngCamera eng_cam;

/* The renderer's near and far planes (lane eng-e1l): engine design constants, not the game's ZNEAR / ZFAR (100 and
 * 1,000,000, core/globals.cpp, which the behaviour and the camera's evaluation read). The record's depth terms (p22,
 * p23) and its far plane come from these: the renderer reads near = p23 / (p22 - 1) and far = word 25. The near plane
 * is the original's 100 (the game's own projection clips there); the far plane is the engine's draw distance. */
#define ENG_RENDERER_NEAR 100.0f
#define ENG_RENDERER_FAR 18750.0f

/* The record's finite check (lane eng-e1l): at the end of every tick every word of the record (the renderer's 26 and
 * the evaluated eye, target, roll and fov) is tested for a not-a-number or an infinity by its exponent bits (the
 * renderer is built -ffast-math, where isfinite() may fold to true). The report's E1 CAMREC line gives the counts; the
 * selector fails a scene with a non-finite tick or without the line. Lab arm RNEARFAR (boot file, control): the
 * renderer's far plane equals its near, the depth terms divide by zero, the scene must fail. */
typedef struct EngCamCheck {
    uint32_t ticks, nonfinite_ticks, first_tick, first_word, first_bits;
} EngCamCheck;
extern EngCamCheck eng_cam_check;
extern int eng_cam_nearfar_control;   /* RNEARFAR (control) */
void eng_cam_check_tick(uint32_t tick);
/* The trace line of the record (trace runs only, core/frame.cpp): "CAMLOG t=<tick> e=<eye> g=<target> r=<roll>
 * f=<fov> d=<area>,<cut>,<routine>,<blend frames left>", floats as bit patterns (hostref/svc/camengine.py). Returns
 * its length (0: the record not written yet). */
int eng_cam_trace_line(char* buf, unsigned size, uint32_t tick);
/* The camera's diagnosis lines (lane eng-e1m): "CD n=<CameraMove calls> <tag> <words as hex>", the camera's inputs and
 * each evaluation step's output, written only when a sink is set: the image's trace runs with the CAMDIAG boot file
 * (core/frame.cpp), the PC reference's native build with RE4_CAMDIAG (hostref/svc/svc4_dump.cpp). The same lines from
 * the same code on both, so the first quantity apart names where the two cameras part. */
extern void (*eng_cam_diag_sink)(const char* line, unsigned n);
void eng_cam_diag(const char* tag, const void* words, unsigned n);

/* Conversions of game state into a draw record, counted per scene (the selector fails a scene where one is not 0;
 * the E1 PUB line): the camera, the HUD words, the light inputs' compares. The PUBCOPY lab arm (control) makes the
 * camera service copy its record once a tick and count it. */
typedef struct EngPubCounters { uint32_t camera, hud, light_compares; } EngPubCounters;
extern EngPubCounters eng_pub;
extern int eng_pub_copy;   /* PUBCOPY (control) */

#ifdef __cplusplus
}
#endif
#endif
