/* The renderer's view of a native skeleton table (lane eng-e1c): plain C, filled by services/draw.cpp from the
   actor's SkelTable (services/skeleton/skel.h) once a picture; nothing is copied, only pointers.
     world  [n] 16 floats a bone: the world matrix 3x4 row major (cCoord::mat), then r_scale and flags
     pal    [n] 16 floats a bone: the skin palette, world x bind (3x4), written once a tick by skel_publish_all
     bind[3]    the bind translation rows (x, y, z), `cap` apart: what the palette's bind is
   Bone k of the table is the k-th cParts of the model's parts chain (the E1 actor pass's bone k + 1). */
#ifndef E1_SKEL_VIEW_H
#define E1_SKEL_VIEW_H
typedef struct {
    const float* world;
    const float* pal;
    const float* bind[3];
    unsigned n;
} E1SkelView;
#endif
