#ifndef RE4DC_CLOTH_NORMALS_DEFER01_H
#define RE4DC_CLOTH_NORMALS_DEFER01_H

// Render-only replacement for Esp4e's existing calcNormal call. Does not mark
// Cloth::move: Set's warmup intentionally retains its initialized normals.
#if defined(RE4DC_CLOTH_NORMALS_DEFER01) && RE4DC_CLOTH_NORMALS_DEFER01 && !defined(__PPC__)
class Cloth;
extern "C" void re4dc_cloth_normals_defer01(Cloth* cloth);
#endif

#endif
