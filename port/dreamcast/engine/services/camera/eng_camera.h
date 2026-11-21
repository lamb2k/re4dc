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
