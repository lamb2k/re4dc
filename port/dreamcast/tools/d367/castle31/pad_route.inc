// Diagnostic Disc 2 pad-script instructions. Only the returned PAD button
// mask influences play. Use native-alive room observation to avoid the old
// room's actors during card load, overlays and door teardown.
unsigned short re4dc_disc2_pad_step(char** cursor, unsigned long tick)
{
    static bool running;
    static char op[16];
    static int a, b, c, expected_room;
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
        timeout = !strcmp(op,"room") ? 2400 : 800;
        running = true;
    }
    const unsigned long age = tick-start;
    bool done = false;
    unsigned short buttons = 0;
    if (!strcmp(op,"room")) {
        done = ready && pG->room_id == a;
        if (done) expected_room = a;
    } else if (!strcmp(op,"pad")) {
        // Decimal mask, hold frames, then neutral frames. Menus accept pad input.
        done = age >= unsigned(b+c);
        if (age < unsigned(b)) buttons = a;
    } else if (ready && pG->room_id == expected_room) {
        if (!strcmp(op,"walk") || !strcmp(op,"face")) {
            const float dx = a-pPL->pos.x, dz = b-pPL->pos.z;
            float err = atan2f(dx,dz)-pPL->ang.y;
            while (err > 3.141593f) err -= 6.283185f;
            while (err < -3.141593f) err += 6.283185f;
            const bool walk = op[0]=='w';
            done = walk ? dx*dx+dz*dz <= float(c)*c : fabsf(err)<0.09f;
            if (!done) {
                if (err>0.09f) buttons |= 1;
                if (err< -0.09f) buttons |= 2;
                if (walk && fabsf(err)<0.65f) buttons |= 8;
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
