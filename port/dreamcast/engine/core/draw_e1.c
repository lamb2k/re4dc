/* E1 picture (lane eng-e1): the E0 renderer drawing the village from its whole-room bake and Leon from the engine
   actor table (services/actor_e1.inc), with the camera the hosted camera code set this tick.
   Static inputs from the pack's first recorded picture: the room's light set (stream 2), Leon's light record
   (stream 8), the environment (fog, ambient) and the HUD widget layout; the HUD's life and weapon words are the
   live ones. Not drawn in E1: effects, foot shadows (recorded inputs), the handgun model (not in the pack). */
#include "replay.h"
#include "native_scene.h"
#include "e1_skel_view.h"
#include <kos.h>
#include <dc/pvr.h>
#include <string.h>
#include <stdio.h>

volatile uint32_t m1_frame;
/* eng-look's run-time content steps (render/content.h), read by the shared actor pass since that lane's merge: the
   E1 image draws at step 0 of every item with the glow on, the bench's defaults (lane eng-e1b: the E1 image did not
   link without them). */
#include "content.h"
volatile uint32_t m1_content[CS_COUNT] = {[CS_GLOW] = 1};
volatile uint32_t m1_content_counts[8];
/* phase stamps for the hardware model (core/e1_core.h e1_stamp) */
volatile uint32_t m1_timing[600][8];
unsigned e1_stamp_pic;
void e1_stamp_c(unsigned k) { m1_timing[e1_stamp_pic % 600][k & 7] = (uint32_t) timer_us_gettime64(); }
volatile uint32_t m1_state[8];
static NativeScene scene;
static int open_ok, stills;
/* STILLS boot option: every 40th tick (and tick 1) the finished picture is handed to the host runner
   (s/stills.py reads the frame buffer from Flycast's memory; m1_state 2 request, 3 acknowledge, 4 frame buffer). */
void e1_actor_pass(NativeScene* s, const void* model_record, const E1SkelView* skel, unsigned model, unsigned identity,
                   unsigned translucent);
#ifdef E2_FIGHT
/* lane eng-e2: the fight's Ganados and native effect sprites (engine/fight/fight_draw.inc) */
void e2_draw_open(void);
void e2_draw_actors(NativeScene* s);
void e2_draw_effects(NativeScene* s);
#endif

int e1_draw_open_c(void)
{
    pvr_init_params_t params = {.opb_sizes = {PVR_BINSIZE_16, PVR_BINSIZE_8, PVR_BINSIZE_16, 0, PVR_BINSIZE_16},
                                .vertex_buf_size = 1024 * 1024, .vbuf_doublebuf_disabled = 0};
    if (pvr_init(&params) < 0 || pvr_set_vbuf_doublebuf(true) < 0) return 0;
    PVR_SET(PVR_PT_ALPHA_REF, 128);
    pvr_set_zclip(0.0f);
    pvr_set_shadow_scale(true, 0.5f);
    m1_state[5] = 2;
    if (!native_open(&scene, "/cd/CROSS.PAK")) { printf("E1 draw: pack refused (stage %lu)\n", 0ul); return 0; }
    native_update(&scene, 0);
#ifdef E2_FIGHT
    e2_draw_open();
#endif
    open_ok = 1;
    file_t f = fs_open("/cd/STILLS", O_RDONLY);
    if (f >= 0) { fs_close(f); stills = 1; }
    m1_state[5] = 3;
    return 1;
}

/* The partner (lane eng-e1b), PLACEHOLDER form: her mesh is not in any engine pack yet (no bake holds Ashley), so
   the renderer marks each of her bones with a flat square, read in place from her native skeleton table's world
   records (lane eng-e1c; written once a tick by the skeleton service). Nothing is converted or copied per tick; the
   squares are projected with the camera the hosted camera set. */
static unsigned partner_marks;
static void e1_partner_pass(const float* c, const E1SkelView* sk)
{
    if (!sk) return;
    pvr_poly_cxt_t cxt; pvr_poly_hdr_t hdr;
    pvr_poly_cxt_col(&cxt, PVR_LIST_OP_POLY);
    cxt.gen.culling = PVR_CULLING_NONE;
    pvr_poly_compile(&hdr, &cxt);
    pvr_prim(&hdr, sizeof(hdr));
    unsigned n = 0;
    for (; n < sk->n && n < 128; n++) {
        const float* m = sk->world + 16 * n;
        const float x = m[3], y = m[7], z = m[11];
        const float vx = c[0] * x + c[1] * y + c[2] * z + c[3];
        const float vy = c[4] * x + c[5] * y + c[6] * z + c[7];
        const float vz = c[8] * x + c[9] * y + c[10] * z + c[11];
        const float w = -vz;
        if (w < 50.0f) continue;
        const float iw = 1.0f / w;
        const float sx = 320.0f + 320.0f * (c[13] * vx + c[14] * vz) * iw;
        const float sy = 240.0f - 240.0f * (c[15] * vy + c[16] * vz) * iw;
        const float r = 22.0f * c[13] * 320.0f * iw + 1.0f;
        if (sx < -r || sx > 640.0f + r || sy < -r || sy > 480.0f + r) continue;
        pvr_vertex_t v[4];
        const float qx[4] = {sx - r, sx - r, sx + r, sx + r}, qy[4] = {sy + r, sy - r, sy + r, sy - r};
        for (int i = 0; i < 4; i++) {
            v[i].flags = i == 3 ? PVR_CMD_VERTEX_EOL : PVR_CMD_VERTEX;
            v[i].x = qx[i]; v[i].y = qy[i]; v[i].z = iw;
            v[i].u = v[i].v = 0.0f;
            v[i].argb = (n & 1) ? 0xffe0409cu : 0xfff070c0u;
            v[i].oargb = 0;
            pvr_prim(&v[i], sizeof(v[i]));
        }
    }
    partner_marks = n;
}

/* One off-screen triangle in a list that may otherwise stay empty (the hill scene has no world: its punch-through
   list can be empty, and an empty list never reports done, so every picture waited for the chip's 100 ms timeout). */
static void list_keepalive(int list)
{
    pvr_poly_cxt_t cxt; pvr_poly_hdr_t hdr;
    pvr_poly_cxt_col(&cxt, list);
    pvr_poly_compile(&hdr, &cxt);
    pvr_prim(&hdr, sizeof(hdr));
    pvr_vertex_t v = {0};
    for (int i = 0; i < 3; i++) {
        v.flags = i == 2 ? PVR_CMD_VERTEX_EOL : PVR_CMD_VERTEX;
        v.x = -64.0f + (i & 1) * 8.0f; v.y = -64.0f + (i >> 1) * 8.0f; v.z = 0.0001f; v.argb = 0;
        pvr_prim(&v, sizeof(v));
    }
}

/* camera: 26 words (view 3x4, GX projection type + 6 terms, viewport x y w h near far, far plane), as the pack's
   camera stream; hud: life, life max, weapon, stance; partner: the partner's model record or 0; world: draw the
   village bake (0 in the hill scene: r11d has no engine bake yet; its sky and fog are the village's) */
void e1_draw_picture_c(const float* camera, const uint32_t* hud, const void* leon, const E1SkelView* leon_skel, unsigned identity,
                       uint32_t* wait_us, uint32_t* draw_us, const E1SkelView* partner, int world)
{
    if (!open_ok) { *wait_us = *draw_us = 0; return; }
    m1_frame++;
    m1_state[1] = (m1_state[1] % 300) + 1;
    uint64_t t0 = timer_us_gettime64();
    pvr_wait_ready();
    e1_stamp_c(5);
    uint64_t t1 = timer_us_gettime64();
    memcpy(scene.state[0], camera, 26 * 4);
    if (scene.words[5] >= 4) memcpy(scene.state[5], hud, 16);
    const float* cam = (const float*) scene.state[0];
    native_vis_select(&scene.world, cam);   /* also the frame's view state the actor pass and the HUD read */
    native_prepare_world(&scene.world, cam, scene.assets.header.n);
    pvr_scene_begin();
    pvr_list_begin(PVR_LIST_OP_POLY);
    native_sky(&scene);   /* also the fog table every header reads (the hill scene: the village sky and fog) */
    if (world) native_world_pass(&scene.assets, &scene.world, cam, 0);
#ifdef E2_FIGHT
    e2_draw_actors(&scene);   /* before Leon: his translucent pass below reads the opaque pass's part state */
#endif
    e1_actor_pass(&scene, leon, leon_skel, 0, identity, 0);
    e1_partner_pass(cam, partner);
    pvr_list_finish();
    pvr_list_begin(PVR_LIST_PT_POLY);
    if (world) native_world_pass(&scene.assets, &scene.world, cam, 1);
    else list_keepalive(PVR_LIST_PT_POLY);
    e1_actor_pass(&scene, leon, leon_skel, 0, identity, 1);
    pvr_list_finish();
    pvr_list_begin(PVR_LIST_TR_POLY);
    if (world) native_world_pass(&scene.assets, &scene.world, cam, 2);
#ifdef E2_FIGHT
    e2_draw_effects(&scene);
#endif
    native_hud(&scene);
    pvr_list_finish();
    pvr_scene_finish();
    e1_stamp_c(7);
    uint64_t t2 = timer_us_gettime64();
    *wait_us = (uint32_t) (t1 - t0);
    *draw_us = (uint32_t) (t2 - t1);
    if (stills && (m1_frame == 1 || m1_frame % 40 == 0)) {
        pvr_wait_render_done(); vid_waitvbl(); vid_waitvbl();
        m1_state[4] = 0xa5000000 + 2 * (*(volatile uint32_t*) 0xa05f8050 & 0x7ffffc);
        m1_state[2] = m1_frame;
        while (m1_state[3] != m1_state[2]) thd_pass();
    }
}
