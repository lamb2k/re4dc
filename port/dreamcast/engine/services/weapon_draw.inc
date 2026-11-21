/* weapon_draw.inc (lane eng-look1), included by services/actor_e1.inc: Leon's weapons drawn as the hosted code says.

   Each picture, after Leon's body: the player's weapon objects (services/weapon.cpp e1_weapon_views: the object, its
   native skeleton table, the hosted draw gate, the archive slot of its model). A weapon the hosted gate draws goes
   through the E1 actor pass (e1_actor_pass_one) with the catalogue model the pack holds for its archive slot
   (bake/weapon_model.py), skinned from its own skeleton palette (the skeleton service hangs its root on Leon's hand
   bone) and lit by its own model record in place (services/light_view.h). Nothing is copied or converted per picture.

   At pack open (e1_weapon_open, from e1_light_tables): the catalogue's weapon entries are mapped (archive slot ->
   catalogue model), and a world placement that is a static copy of the weapon is retired: the r101 PS2 world package
   holds the Punisher (the old port's STATIC_OBJ_BAKE, origin/t15/int game/model_bridge.cpp sobake kTable: room 0x101,
   kind 1 id 0x21, placement 209) at Leon's warp-start pose; the old port drew it only while the live gun's matrices
   equalled that pose, the engine drew it always (the gun fixed in the world). The placement is recognised by its
   index, centre and size, and marked as the selection's skipped kind (NativePlacement.sky: never selected). */
#include "weapon_view.h"
extern volatile uint32_t m1_frame;   /* core/draw_e1.c: the picture number */
extern volatile uint32_t e1_tick;
int e1_draw_stills_c(void);
static int16_t wep_catalogue[256];   /* archive slot of em/wep02 -> catalogue model + 1 (0: the pack holds none) */
#define WEP_TAG 0x5745u
#define WEP_FILE_SLOT 2u
static const struct { uint16_t index; float center[3], size[3]; } wep_world_copies[] = {
    {209, {-7763.f, 1587.f, 2272.f}, {184.f, 290.f, 72.f}},   /* r101: the Punisher at Leon's warp start (mm) */
};
static void e1_weapon_open(const NativeScene* s)
{
    memset(wep_catalogue, 0, sizeof(wep_catalogue));
    const RtCatalog* cat = s->runtime;
    unsigned mapped = 0;
    for (unsigned i = 0; cat && i < cat->n; i++) {
        const RtModel* m = cat->m + i;
        if (!m->h[4]) continue;
        const unsigned role = m->parts[0].src->role;
        if ((role >> 16) != WEP_TAG || (role >> 8 & 255) != WEP_FILE_SLOT) continue;
        if (!wep_catalogue[role & 255]) mapped++;
        wep_catalogue[role & 255] = (int16_t) (i + 1);
    }
    unsigned retired = 0;
    NativePlacement* p = (NativePlacement*) s->world.places;
    for (unsigned j = 0; p && j < s->world.place_count; j++)
        for (unsigned k = 0; k < sizeof(wep_world_copies) / sizeof(wep_world_copies[0]); k++) {
            int same = p[j].index == wep_world_copies[k].index && !p[j].sky;
            for (unsigned a = 0; a < 3 && same; a++)
                same = fabsf(p[j].center[a] - wep_world_copies[k].center[a]) < 2.f &&
                       fabsf(2.f * p[j].half[a] - wep_world_copies[k].size[a]) < 2.f;
            if (same) { p[j].sky = 1; retired++; }
        }
    e1_weapon_world_retired = retired;
    file_t f = fs_open("/cd/NOWEP", O_RDONLY);
    if (f >= 0) { fs_close(f); e1_weapon_off = 1; printf("E1 NOWEP: no weapon drawn (control)\n"); }
    printf("E1 WEP open: %u weapon models in the catalogue (Punisher %d, upgraded %d), %u world copies retired\n", mapped,
           wep_catalogue[6] - 1, wep_catalogue[7] - 1, retired);
}

/* The weapon's projected box on screen from its parts' bone spheres (the actor pass's own sphere test input, read on
   the palette in place): x0 y0 x1 y1 in pixels; 0 when it is behind the camera or off the screen. */
static int e1_weapon_box(const NativeScene* s, const RtModel* m, const float* pal, int* box)
{
    const float* c = (const float*) s->state[0];
    float x0 = 1e9f, y0 = 1e9f, x1 = -1e9f, y1 = -1e9f;
    int any = 0;
    for (unsigned p = 0; p < m->h[4]; p++) {
        const RtPart* rp = m->parts + p;
        for (unsigned k = 0; k < rp->sphere_count; k++) {
            const PartSphere* sp = m->spheres + rp->sphere_first + k;
            const float* r = pal + 16 * sp->bone;
            float w[3];
            for (unsigned a = 0; a < 3; a++) w[a] = r[4 * a] * sp->c[0] + r[4 * a + 1] * sp->c[1] + r[4 * a + 2] * sp->c[2] + r[4 * a + 3];
            const float vx = c[0] * w[0] + c[1] * w[1] + c[2] * w[2] + c[3];
            const float vy = c[4] * w[0] + c[5] * w[1] + c[6] * w[2] + c[7];
            const float vz = c[8] * w[0] + c[9] * w[1] + c[10] * w[2] + c[11];
            if (-vz < 20.f) continue;
            const float iw = 1.0f / -vz, rad = sp->r * r[12];
            const float sx = 320.0f + 320.0f * (c[13] * vx + c[14] * vz) * iw;
            const float sy = 240.0f - 240.0f * (c[15] * vy + c[16] * vz) * iw;
            const float rx = rad * c[13] * 320.0f * iw, ry = rad * c[15] * 240.0f * iw;
            if (sx - rx < x0) x0 = sx - rx;
            if (sy - ry < y0) y0 = sy - ry;
            if (sx + rx > x1) x1 = sx + rx;
            if (sy + ry > y1) y1 = sy + ry;
            any = 1;
        }
    }
    if (!any) return 0;
    box[0] = (int) x0; box[1] = (int) y0; box[2] = (int) x1; box[3] = (int) y1;
    return x1 >= 0.f && y1 >= 0.f && x0 < 640.f && y0 < 480.f;
}

static void e1_weapon_pass(NativeScene* s)
{
    E1WeaponView v[E1_WEAPON_MAX];
    const unsigned n = e1_weapon_views(v, E1_WEAPON_MAX);
    const int still = e1_draw_stills_c() && (m1_frame == 1 || m1_frame % 40 == 0);
    unsigned drawn_n = 0;
    int box[4] = {-1, -1, -1, -1};
    for (unsigned i = 0; i < n; i++) {
        unsigned drawn = 0, on = 0;
        const int cm = v[i].file_slot == WEP_FILE_SLOT && v[i].arc_slot >= 0 && v[i].arc_slot < 256 ?
                       wep_catalogue[v[i].arc_slot] - 1 : -1;
        if (v[i].visible && !e1_weapon_off && cm >= 0 && v[i].has_skel)
            drawn = (unsigned) e1_actor_pass_one(s, v[i].model, &v[i].skel, (unsigned) cm, 0, 0);
        if (drawn) {
            int b[4];
            on = (unsigned) e1_weapon_box(s, ((const RtCatalog*) s->runtime)->m + cm, v[i].skel.pal, b);
            if (on && box[0] == -1) memcpy(box, b, sizeof(b));
        }
        drawn_n += drawn;
        e1_weapon_note(i, drawn, on);
    }
    /* STILLS runs only (never a timing run): the facts tools/engine/wepcheck.py checks each still against */
    if (still)
        printf("E1 WEPSTILL %lu tick %lu present %u visible %u drawn %u box %d %d %d %d\n", (unsigned long) m1_frame,
               (unsigned long) e1_tick, n, n ? v[0].visible : 0u, drawn_n, box[0], box[1], box[2], box[3]);
}
