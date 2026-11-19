// Diagnostic Disc 2 pad-script instructions. Only the returned PAD button
// mask influences play. Use native-alive room observation to avoid the old
// room's actors during card load, overlays and door teardown.
char* re4dc_disc2_next_page();
static float disc2_heading_error(float x, float z)
{
    float error = atan2f(x-pPL->pos.x, z-pPL->pos.z) - pPL->ang.y;
    while (error > 3.141593f) error -= 6.283185f;
    while (error < -3.141593f) error += 6.283185f;
    return error;
}

// The original shooting and reload paths consume R+A and R+B. Observation
// selects a target and the replay drives the same aim stick as a player.
static cEm* disc2_target(int radius, bool carried)
{
    const Vec& origin = carried ? pSubEm->pos : pPL->pos;
    cEm* nearest = nullptr;
    float limit = float(radius)*radius;
    for (u32 i=0; i<EmMgr.nArray; ++i) {
        cEm* enemy = (cEm*) EmMgr.workAt(i);
        if (!enemy || enemy == pSubEm || (enemy->id & 0xff) >= 0x40 ||
            enemy->hp <= 0 || SceCheckEmAlive(enemy)!=1 ||
            fabsf(enemy->pos.y-origin.y)>1500.0f) continue;
        float dx=enemy->pos.x-origin.x, dz=enemy->pos.z-origin.z;
        float distance=dx*dx+dz*dz;
        if (distance < limit) { nearest=enemy; limit=distance; }
    }
    return nearest;
}

unsigned short re4dc_disc2_pad_step(char** cursor, unsigned long source_frame)
{
    static bool running;
    // Restoring a native save restores its source frame counter as well.
    static unsigned long previous_frame, tick;
    if (source_frame >= previous_frame) tick += source_frame - previous_frame;
    else ++tick;
    previous_frame = source_frame;
    static char op[16];
    static int a, b, c, expected_room, combat_radius;
    static bool sprint, rescue;
    static unsigned long start, timeout;
    const bool ready = pG && pPL && wp.observe_ready && wp.observe_room == pG->room_id
        && pG->Rno0 == 3 && pG->Rno1 == 0 && !pG->Stop_flg && !wp.active;
    if (!running) {
        char* line = *cursor;
        while (*line == '\n' || *line == '\r') ++line;
        if (!*line) {
            re4dc_log("padroute: end of script\n");
            *cursor = nullptr;
            return 0;
        }
        char* next = strchr(line, '\n');
        if (next) *next++ = 0;
        else next = line + strlen(line);
        *cursor = next;
        a = b = c = 0;
        if (sscanf(line, "%15s %d %d %d", op, &a, &b, &c) < 2) {
            re4dc_log("padroute: invalid instruction %s\n", line);
            *cursor = nullptr;
            return 0;
        }
        re4dc_log("padroute: %s at %lu\n", line, tick);
        start = tick;
        timeout = !strcmp(op,"room") || combat_radius ? 2400 : 800;
        running = true;
    }
    const unsigned long age = tick-start;
    bool done = false;
    unsigned short buttons = 0;
    if (!strcmp(op,"run")) {
        sprint = a != 0;
        done = true;
    } else if (!strcmp(op,"rescue")) {
        rescue = a != 0;
        done = true;
    } else if (!strcmp(op,"mash")) {
        buttons = age%6 < 3 ? a : 0;
        done = age >= unsigned(b);
    } else if (!strcmp(op,"combat")) {
        combat_radius = a;
        done = true;
    } else if (!strcmp(op,"page") && a==2) {
        *cursor = re4dc_disc2_next_page();
        if (!*cursor) re4dc_log("padroute: missing second script page\n");
        done = true;
    } else if (!strcmp(op,"room")) {
        done = ready && pG->room_id == a;
        if (done) expected_room = a;
    } else if (!strcmp(op,"pad")) {
        // Decimal mask, hold frames, then neutral frames. Menus accept pad input.
        done = age >= unsigned(b+c);
        if (age < unsigned(b)) buttons = a;
    } else if (ready && pG->room_id == expected_room) {
        if (!strcmp(op,"walk") || !strcmp(op,"face")) {
            const float dx = a-pPL->pos.x, dz = b-pPL->pos.z;
            const float err = disc2_heading_error(a,b);
            const bool walk = op[0]=='w';
            done = walk ? dx*dx+dz*dz <= float(c)*c : fabsf(err)<0.09f;
            if (!done) {
                if (err>0.09f) buttons |= 1;
                if (err< -0.09f) buttons |= 2;
                if (walk && fabsf(err)<0.65f) buttons |= 8;
                if (walk && sprint && fabsf(err)<0.30f && dx*dx+dz*dz>2250000.0f) buttons |= 512;
                const bool carried = rescue && pSubEm && (pG->Status_flg[1] & 0x10000);
                cEm* target = walk && (combat_radius || carried)
                    ? disc2_target(carried ? 2500 : combat_radius, carried) : nullptr;
                if (target) {
                    const float aim = disc2_heading_error(target->pos.x,target->pos.z);
                    const float tx = target->pos.x-pPL->pos.x;
                    const float tz = target->pos.z-pPL->pos.z;
                    const float dist2 = tx*tx+tz*tz;
                    const ItemWork* gun = ItemMgr.pArm;
                    const int loaded = gun ? gun->bullet & 0x1fff : 0;
                    buttons = 32;
                    if (carried && dist2 > 16000000.0f)
                        buttons = fabsf(aim)<0.65f ? 520 : 0;
                    if (aim>0.08f) buttons |= 1;
                    if (aim< -0.08f) buttons |= 2;
                    if ((buttons & 32) && fabsf(aim)<=0.12f && tick%15 < 3)
                        buttons |= loaded ? 256 : 512;
                    if (tick%120==0)
                        re4dc_log("padroute: aim room=%03x target=%02x hp=%d ammo=%d carry=%d\n",
                                  unsigned(pG->room_id),unsigned(target->id),int(target->hp),loaded,int(carried));
                }
            }
        } else if (!strcmp(op,"rsf")) {
            done = RsfCheck(pG->room_id,a) != 0;
        } else if (!strcmp(op,"unlock")) {
            done = (pG->door_unlock[0] & unsigned(a)) == unsigned(a);
        } else {
            re4dc_log("padroute: invalid operation %s\n",op);
            *cursor = nullptr;
        }
    }
    static unsigned long last_sample;
    if (ready && pG->room_id == 0x207 && tick-last_sample>=90) {
        last_sample=tick;
        re4dc_log("padroute: swords flags=%d/%d/%d/%d items=%d/%d ammo=%d\n",
            !!RsfCheck(0x207,4), !!RsfCheck(0x207,5), !!RsfCheck(0x207,6), !!RsfCheck(0x207,7),
            int(ItemMgr.num(0x80)),int(ItemMgr.num(0xc4)),ItemMgr.pArm ? int(ItemMgr.pArm->bullet&0x1fff) : -1);
    }
    if (done) {
        running = false;
        re4dc_log("padroute: complete %s room=%03x frame=%lu\n",op,pG ? unsigned(pG->room_id):0u,tick);
    } else if (age > timeout && strcmp(op,"pad")) {
        re4dc_log("padroute: STUCK %s %d %d room=%03x elapsed=%lu\n",op,a,b,pG ? unsigned(pG->room_id):0u,age);
        *cursor = nullptr;
        return 0;
    }
    return buttons;
}
