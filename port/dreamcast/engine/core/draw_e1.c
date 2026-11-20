/* E1 picture (lane eng-e1): the E0 renderer drawing the village from its whole-room bake and Leon from the engine
   actor table (services/actor_e1.inc), with the camera the hosted camera code set this tick.
   Static inputs from the pack's first recorded picture: the room's light set (stream 2), Leon's light record
   (stream 8), the environment (fog, ambient) and the HUD widget layout; the HUD's life and weapon words are the
   live ones. Not drawn in E1: effects, foot shadows (recorded inputs), the handgun model (not in the pack). */
#include "replay.h"
#include "native_scene.h"
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
volatile uint32_t m1_state[8];
static NativeScene scene;
static int open_ok, stills;
/* STILLS boot option: every 40th tick (and tick 1) the finished picture is handed to the host runner
   (s/stills.py reads the frame buffer from Flycast's memory; m1_state 2 request, 3 acknowledge, 4 frame buffer). */
void e1_actor_pass(NativeScene* s, const void* model_record, unsigned model, unsigned identity, unsigned translucent);

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
    open_ok = 1;
    file_t f = fs_open("/cd/STILLS", O_RDONLY);
    if (f >= 0) { fs_close(f); stills = 1; }
    m1_state[5] = 3;
    return 1;
}

/* camera: 26 words (view 3x4, GX projection type + 6 terms, viewport x y w h near far, far plane), as the pack's
   camera stream; hud: life, life max, weapon, stance */
void e1_draw_picture_c(const float* camera, const uint32_t* hud, const void* leon, unsigned identity,
                       uint32_t* wait_us, uint32_t* draw_us)
{
    if (!open_ok) { *wait_us = *draw_us = 0; return; }
    m1_frame++;
    m1_state[1] = (m1_state[1] % 300) + 1;
    uint64_t t0 = timer_us_gettime64();
    pvr_wait_ready();
    uint64_t t1 = timer_us_gettime64();
    memcpy(scene.state[0], camera, 26 * 4);
    if (scene.words[5] >= 4) memcpy(scene.state[5], hud, 16);
    const float* cam = (const float*) scene.state[0];
    native_vis_select(&scene.world, cam);
    native_prepare_world(&scene.world, cam, scene.assets.header.n);
    pvr_scene_begin();
    pvr_list_begin(PVR_LIST_OP_POLY);
    native_sky(&scene);
    native_world_pass(&scene.assets, &scene.world, cam, 0);
    e1_actor_pass(&scene, leon, 0, identity, 0);
    pvr_list_finish();
    pvr_list_begin(PVR_LIST_PT_POLY);
    native_world_pass(&scene.assets, &scene.world, cam, 1);
    e1_actor_pass(&scene, leon, 0, identity, 1);
    pvr_list_finish();
    pvr_list_begin(PVR_LIST_TR_POLY);
    native_world_pass(&scene.assets, &scene.world, cam, 2);
    native_hud(&scene);
    pvr_list_finish();
    pvr_scene_finish();
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
