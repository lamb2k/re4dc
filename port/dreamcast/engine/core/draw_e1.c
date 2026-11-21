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
#include <math.h>

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
void e1_light_tables(const NativeScene* s);
/* render/native_scene.h (included above): hud_blend_control, the HUD control (lane eng-e1h); hud_ammo_drawn (eng-e1i) */
unsigned e1_hud_magazine(void);   /* services/draw.cpp: the loaded count (lane eng-e1i) */
#ifdef E2_FIGHT
/* lane eng-e2: the fight's Ganados and native effect sprites (engine/fight/fight_draw.inc) */
void e2_draw_open(void);
void e2_draw_actors(NativeScene* s);
void e2_draw_effects(NativeScene* s);
#endif

/* Lane eng-e1d: the scene's pack. The village route reads CROSS.PAK (eng-look's lkg bake); the hill scene reads
   HILL.PAK (bake/hill_pack.py: the r11d whole-room bake with its visibility HILL.VIS, the room's lights, fog and HUD
   from an old-game capture of r11d, Leon in his chapter-2 costume, Ashley at catalogue 6). */
#define E1_ASHLEY_MODEL 6
extern volatile uint32_t m1_load_status[8];   /* render/native_scene.inc: the pack loader's stage */
static unsigned partner_model;
int e1_draw_open_c(const char* pack)
{
    pvr_init_params_t params = {.opb_sizes = {PVR_BINSIZE_16, PVR_BINSIZE_8, PVR_BINSIZE_16, 0, PVR_BINSIZE_16},
                                .vertex_buf_size = 1024 * 1024, .vbuf_doublebuf_disabled = 0};
    if (pvr_init(&params) < 0 || pvr_set_vbuf_doublebuf(true) < 0) return 0;
    PVR_SET(PVR_PT_ALPHA_REF, 128);
    pvr_set_zclip(0.0f);
    pvr_set_shadow_scale(true, 0.5f);
    m1_state[5] = 2;
    if (!native_open(&scene, pack)) { printf("E1 draw: pack %s refused (stage %lu)\n", pack, (unsigned long) m1_load_status[0]); return 0; }
    native_update(&scene, 0);
    e1_light_tables(&scene);   /* lane eng-e1e: each TEV group's scale, once a pack (services/actor_e1.inc) */
    /* Ashley's body is catalogue 6 of the hill pack only (other packs hold props there) */
    partner_model = strstr(pack, "HILL") && scene.models.n > E1_ASHLEY_MODEL ? E1_ASHLEY_MODEL : 0;
    printf("E1 draw: pack %s, %u catalogue models, partner %s\n", pack, scene.models.n, partner_model ? "drawn from catalogue 6" : "bone marks");
#ifdef E2_FIGHT
    e2_draw_open();
#endif
    open_ok = 1;
    file_t f = fs_open("/cd/STILLS", O_RDONLY);
    if (f >= 0) { fs_close(f); stills = 1; }
    /* lane eng-e1h: HUDOLD (run-time lab arm and the HUD control): every HUD widget with the one blend the pack bakes */
    f = fs_open("/cd/HUDOLD", O_RDONLY);
    if (f >= 0) { fs_close(f); hud_blend_control = 1; printf("E1 HUDOLD: every HUD widget with blend 0 (control)\n"); }
    m1_state[5] = 3;
    return 1;
}

/* The partner (lane eng-e1b), PLACEHOLDER form, kept for a pack without her body (lane eng-e1d: the hill pack draws
   her mesh, catalogue 6, through the E1 actor pass): the renderer marks each of her bones with a flat square, read in place from her native skeleton table's world
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

/* The weapon's laser sight (lane eng-e1h, H-014.3): the line and the dot cObjWep::drawLaserSight set this tick through
   the engine's setters (services/laser.cpp), read in place from e1_laser and drawn additive in the translucent list:
   the line as a screen-space band (1.5 pixels a width unit) from the muzzle, faded to nothing over its fade length and
   clipped at the near plane; the dot as a small glow (a fan, bright at the centre). Nothing is drawn for a tick in
   which the behaviour set nothing (no aiming). */
#include "e1_laser.h"
extern volatile uint32_t e1_tick;
#define LASER_NEAR 20.0f
static uint32_t laser_argb(uint32_t rgb, float k)
{
    if (k < 0.0f) k = 0.0f;
    if (k > 1.0f) k = 1.0f;
    const uint32_t r = (uint32_t) (((rgb >> 16) & 255) * k), g = (uint32_t) (((rgb >> 8) & 255) * k),
                   b = (uint32_t) ((rgb & 255) * k);
    return 0xff000000u | r << 16 | g << 8 | b;
}
static void laser_hdr(int ztest)
{
    pvr_poly_cxt_t cxt; pvr_poly_hdr_t hdr;
    pvr_poly_cxt_col(&cxt, PVR_LIST_TR_POLY);
    cxt.gen.culling = PVR_CULLING_NONE;
    cxt.blend.src = PVR_BLEND_ONE;
    cxt.blend.dst = PVR_BLEND_ONE;
    cxt.depth.write = PVR_DEPTHWRITE_DISABLE;
    cxt.depth.comparison = ztest ? PVR_DEPTHCMP_GEQUAL : PVR_DEPTHCMP_ALWAYS;
    pvr_poly_compile(&hdr, &cxt);
    pvr_prim(&hdr, sizeof(hdr));
}
static void laser_vert(float x, float y, float z, uint32_t argb, int eol)
{
    pvr_vertex_t v;
    v.flags = eol ? PVR_CMD_VERTEX_EOL : PVR_CMD_VERTEX;
    v.x = x; v.y = y; v.z = z; v.u = v.v = 0.0f; v.argb = argb; v.oargb = 0;
    pvr_prim(&v, sizeof(v));
}
static void laser_view(const float* c, const float* p, float* v)
{
    v[0] = c[0] * p[0] + c[1] * p[1] + c[2] * p[2] + c[3];
    v[1] = c[4] * p[0] + c[5] * p[1] + c[6] * p[2] + c[7];
    v[2] = c[8] * p[0] + c[9] * p[1] + c[10] * p[2] + c[11];
}
static void e1_laser_pass(const float* c)
{
    E1Laser* l = &e1_laser;
    const unsigned lines = l->tick == e1_tick ? l->lines : 0;
    for (unsigned i = 0; i < lines && i < E1_LASER_LINES; i++) {
        const E1LaserLine* s = &l->line[i];
        float a[3], b[3];
        if (s->view) { memcpy(a, s->p[0], 12); memcpy(b, s->p[1], 12); }
        else { laser_view(c, s->p[0], a); laser_view(c, s->p[1], b); }
        float d[3] = {b[0] - a[0], b[1] - a[1], b[2] - a[2]};
        float len = sqrtf(d[0] * d[0] + d[1] * d[1] + d[2] * d[2]);
        if (len <= 0.0f || s->fade <= 0.0f) continue;
        if (len > s->fade) {
            const float k = s->fade / len;
            for (int j = 0; j < 3; j++) { d[j] *= k; b[j] = a[j] + d[j]; }
            len = s->fade;
        }
        float k0 = 1.0f, k1 = 1.0f - len / s->fade;   /* brightness at the two ends */
        const float w0 = -a[2], w1 = -b[2];
        if (w0 < LASER_NEAR && w1 < LASER_NEAR) continue;
        if (w0 < LASER_NEAR || w1 < LASER_NEAR) {   /* clip at the near plane, the brightness along with it */
            const float t = (LASER_NEAR - w0) / (w1 - w0);
            float* q = w0 < LASER_NEAR ? a : b;
            for (int j = 0; j < 3; j++) q[j] = a[j] + (b[j] - a[j]) * t;
            const float kt = k0 + (k1 - k0) * t;
            if (w0 < LASER_NEAR) k0 = kt; else k1 = kt;
        }
        const float iw0 = 1.0f / -a[2], iw1 = 1.0f / -b[2];
        const float x0 = 320.0f + 320.0f * (c[13] * a[0] + c[14] * a[2]) * iw0;
        const float y0 = 240.0f - 240.0f * (c[15] * a[1] + c[16] * a[2]) * iw0;
        const float x1 = 320.0f + 320.0f * (c[13] * b[0] + c[14] * b[2]) * iw1;
        const float y1 = 240.0f - 240.0f * (c[15] * b[1] + c[16] * b[2]) * iw1;
        const float sx = x1 - x0, sy = y1 - y0, sl = sqrtf(sx * sx + sy * sy);
        if (sl < 0.5f) continue;
        const float hw = 0.75f * (s->width > 0.0f ? s->width : 1.0f);
        const float nx = -sy / sl * hw, ny = sx / sl * hw;
        const uint32_t c0 = laser_argb(s->rgb, k0), c1 = laser_argb(s->rgb, k1);
        laser_hdr(s->ztest);
        laser_vert(x0 + nx, y0 + ny, iw0, c0, 0);
        laser_vert(x0 - nx, y0 - ny, iw0, c0, 0);
        laser_vert(x1 + nx, y1 + ny, iw1, c1, 0);
        laser_vert(x1 - nx, y1 - ny, iw1, c1, 1);
        l->drawn++;
    }
    if (l->dot_tick == e1_tick) {
        float v[3];
        laser_view(c, l->dot, v);
        const float w = -v[2];
        if (w >= LASER_NEAR) {
            const float iw = 1.0f / w;
            const float x = 320.0f + 320.0f * (c[13] * v[0] + c[14] * v[2]) * iw;
            const float y = 240.0f - 240.0f * (c[15] * v[1] + c[16] * v[2]) * iw;
            float r = l->dot_r * c[13] * 320.0f * iw;
            if (r < 1.5f) r = 1.5f;
            const uint32_t mid = laser_argb(l->dot_rgb, 1.0f), rim = 0xff000000u;
            laser_hdr(1);
            for (int k = 0; k < 8; k++) {   /* eight triangles round the centre */
                const float a0 = (float) k * 0.785398163f, a1 = (float) (k + 1) * 0.785398163f;
                laser_vert(x, y, iw, mid, 0);
                laser_vert(x + r * cosf(a0), y + r * sinf(a0), iw, rim, 0);
                laser_vert(x + r * cosf(a1), y + r * sinf(a1), iw, rim, 1);
            }
            l->dots_drawn++;
        }
    }
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

/* Presented fields (lane eng-e1f; core/frame.cpp e1_fields_*): a vblank handler counts the 60 Hz fields and records
   the field number of every change of the display address (FB_R_SOF1, the chip's page flip), as the bench's. */
#include <dc/vblank.h>
#include <dc/video.h>
static volatile uint32_t vbl_fields, flip_n, last_sof;
static volatile uint32_t flip_field[1040];
/* Fixed-field presentation (lane eng-e1g, H-014.1): with the field pacer (core/frame.cpp e1_pace_end) every picture is
   shown on a set field, not whenever the chip finishes it. KOS's manual flip holds a rendered picture back; the pacer
   queues each picture's release field (the field after its tick's target), and this handler, which runs after KOS's
   own vblank handler (registered at pvr_init, the list is in order), releases the oldest queued picture when that field
   begins, so KOS flips it at the next field: two fields after the next tick starts, one picture of latency. The chip
   renders picture k while the CPU runs tick k + 1; a picture whose render ends after its release field is flipped when
   it ends (a late picture: a long interval, then two-field intervals again). Off (KOS's automatic flip, the picture shown
   at the first field after its render) for the headless image and for the lab arm PACETMU. */
static int manual_flip;
static volatile uint32_t pres_q[8], pres_head, pres_tail, pres_drop;
static void on_vblank(uint32_t code, void* data)
{
    (void) code; (void) data;
    vbl_fields++;
    uint32_t sof = *(volatile uint32_t*) 0xa05f8050;
    if (sof != last_sof) { last_sof = sof; if (flip_n < 1040) flip_field[flip_n] = vbl_fields; flip_n++; }
    if (manual_flip && pres_head != pres_tail && (int32_t) (vbl_fields - pres_q[pres_head & 7]) >= 0 &&
        pvr_present_async(true) == 0)
        pres_head++;
}
/* The picture just submitted is released at field `field` (shown at field + 1). Queue full (eight pictures behind):
   counted, released at once. */
void e1_present_at_c(uint32_t field)
{
    if (!manual_flip) return;
    if (pres_tail - pres_head >= 8) { pres_drop++; field = vbl_fields; }
    pres_q[pres_tail & 7] = field;
    pres_tail++;
}
static int stills_queued;   /* the STILLS option released this tick's picture itself */
void e1_present_next_c(uint32_t field)
{
    if (stills_queued) { stills_queued = 0; return; }
    e1_present_at_c(field);
}
unsigned e1_present_drops_c(void) { return pres_drop; }
/* manual: 1 for the field pacer's fixed-field presentation (the drawing images), 0 for KOS's automatic flip */
int e1_fields_start_c(int manual)
{
    vblank_handler_add(on_vblank, NULL);
    if (open_ok) { pvr_wait_ready(); pvr_wait_render_done(); }
    vid_waitvbl(); vid_waitvbl();
    if (open_ok && manual) manual_flip = pvr_set_manual_flip(true) == 0;
    flip_n = 0;
    return manual_flip;
}
uint32_t e1_fields_now_c(void) { return vbl_fields; }
unsigned e1_fields_finish_c(const volatile uint32_t** field)
{
    if (open_ok) { pvr_wait_ready(); pvr_wait_render_done(); }
    vid_waitvbl(); vid_waitvbl(); vid_waitvbl();
    *field = flip_field;
    return flip_n < 1040 ? flip_n : 1040;
}

/* The camera stream (26 words: view 3x4, GX projection type + 6 terms, viewport x y w h near far, far plane) and the
   HUD stream's first four words (life, life max, weapon, stance) are written in place by the engine's tick steps
   (services/draw.cpp e1_camera_draw_tick / e1_hud_draw_tick, lane eng-e1e): the picture reads them as they are.
   partner: the partner's skeleton view or 0, partner_record her model record; world: draw the pack's whole-room bake
   (the scene's own room since lane eng-e1d) */
float* e1_draw_cam_stream(void) { return (float*) scene.state[0]; }
uint32_t* e1_draw_hud_stream(void) { return scene.words[5] >= 4 ? (uint32_t*) scene.state[5] : 0; }
void e1_draw_picture_c(const void* leon, const E1SkelView* leon_skel, unsigned identity,
                       uint32_t* wait_us, uint32_t* draw_us, const E1SkelView* partner, int world, const void* partner_record)
{
    if (!open_ok) { *wait_us = *draw_us = 0; return; }
    m1_frame++;
    m1_state[1] = (m1_state[1] % 300) + 1;
    uint64_t t0 = timer_us_gettime64();
    pvr_wait_ready();
    e1_stamp_c(5);
    uint64_t t1 = timer_us_gettime64();
    const float* cam = (const float*) scene.state[0];
    native_vis_select(&scene.world, cam);   /* also the frame's view state the actor pass and the HUD read */
    native_prepare_world(&scene.world, cam, scene.assets.header.n);
    pvr_scene_begin();
    pvr_list_begin(PVR_LIST_OP_POLY);
    native_sky(&scene);   /* also the fog table every header reads (the hill scene: the village sky and fog) */
    if (world) native_world_pass(&scene.assets, &scene.world, cam, 0);
#ifdef E2_FIGHT
    e2_draw_actors(&scene);   /* the Ganados (lane eng-e2); each character keeps its own slot since lane eng-e1d */
#endif
    e1_actor_pass(&scene, leon, leon_skel, 0, identity, 0);
    if (partner && partner_model && partner_record) e1_actor_pass(&scene, partner_record, partner, partner_model, identity, 0);
    else e1_partner_pass(cam, partner);
    pvr_list_finish();
    pvr_list_begin(PVR_LIST_PT_POLY);
    if (world) native_world_pass(&scene.assets, &scene.world, cam, 1);
    else list_keepalive(PVR_LIST_PT_POLY);
    pvr_list_finish();
    pvr_list_begin(PVR_LIST_TR_POLY);
    if (world) native_world_pass(&scene.assets, &scene.world, cam, 2);
    e1_actor_pass(&scene, leon, leon_skel, 0, identity, 1);   /* Leon's hair run (role 8), as the bench since eng-look */
#ifdef E2_FIGHT
    e2_draw_effects(&scene);
#endif
    e1_laser_pass(cam);   /* lane eng-e1h: the laser sight the behaviour set this tick */
    native_hud(&scene);
    pvr_list_finish();
    pvr_scene_finish();
    e1_stamp_c(7);
    uint64_t t2 = timer_us_gettime64();
    *wait_us = (uint32_t) (t1 - t0);
    *draw_us = (uint32_t) (t2 - t1);
    if (stills && (m1_frame == 1 || m1_frame % 40 == 0)) {
        /* fixed-field presentation: release this picture now (behind any queued one), then wait for it to show; the
           pacer then does not queue it again (e1_present_take_c) */
        if (manual_flip) { e1_present_at_c(vbl_fields); stills_queued = 1; vid_waitvbl(); vid_waitvbl(); }
        pvr_wait_render_done(); vid_waitvbl(); vid_waitvbl();
        m1_state[4] = 0xa5000000 + 2 * (*(volatile uint32_t*) 0xa05f8050 & 0x7ffffc);
        m1_state[2] = m1_frame;
        while (m1_state[3] != m1_state[2]) thd_pass();
        /* lane eng-e1i: the ammo check's facts for this still (s/hudcheck.py reads the digit cells from the still) */
        printf("E1 STILL %lu tick %lu magazine %u digits drawn %d %d %d\n", (unsigned long) m1_frame,
               (unsigned long) e1_tick, e1_hud_magazine(), hud_ammo_drawn[2] == 0xff ? -1 : hud_ammo_drawn[2],
               hud_ammo_drawn[1] == 0xff ? -1 : hud_ammo_drawn[1], hud_ammo_drawn[0] == 0xff ? -1 : hud_ammo_drawn[0]);
    }
}
