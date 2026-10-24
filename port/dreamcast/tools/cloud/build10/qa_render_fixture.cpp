// Appended to source-extracted qa_menu.cpp framebuffer/census functions by
// qa_render_check.py. Synthetic observations exercise the real census core.
static uint64_t tick_clock = 100000;
extern "C" uint64_t re4dc_wc24_test_clock() { return tick_clock; }
extern "C" uintptr_t re4dc_wc24_test_thread() { return 1; }
extern "C" void re4dc_wc24_test_log(const char*) {}
extern "C" void re4dc_wc24_identity(unsigned out[7]) {
    for (unsigned i = 0; i < 7; ++i) out[i] = 0;
}

int main(int argc, char** argv) {
    if (argc != 4) return 1;
    using namespace re4dc::wc24;
    for (unsigned tick = 0; tick < 300; ++tick) {
        const uint64_t start = tick_clock;
        begin_tick(tick, 0x101); decision(true);
        for (unsigned path = 0; path < PathCount; ++path) {
            Scope world(Path(path), Selection); tick_clock += 120;
            world.phase(Transform); tick_clock += 500; count(Transformed, 1000 + path * 250);
            world.phase(Clip); tick_clock += 50;
            world.phase(HeaderMaterial); tick_clock += 40;
            const uint32_t header[4] = {0x80840000, path, 2, 3}; submitted_header(header);
            world.phase(Submit); tick_clock += 250; count(Corners, 1600 + path * 300);
            count(PickedIndexed, 15 + path); count(PickedPlain, 2); count(PickedEmpty, 1);
            world.phase(Other); tick_clock += 10;
        }
        { WaitScope wait(VblankWait); tick_clock += 1500; }
        scene_finished(); decision_posted(true); pvr_event(1); pvr_event(1);
        tick_clock = start + 33333;
        pvr_event(6); pvr_event(7); pvr_event(8); end_tick();
    }
    begin_tick(300, 0x101); pause();
    Snapshot snap{};
    if (!snapshot(&snap) || snap.drawn != 300 || snap.errors) return 2;
    const int width = atoi(argv[2]), height = width == 640 ? 480 : 240, bpp = atoi(argv[3]);
    if ((width != 640 && width != 320) || (bpp != 2 && bpp != 4)) return 3;
    std::vector<uint8_t> bytes(width * height * bpp + 128, 0xA5);
    Fb fb{bytes.data() + 64, width, height, bpp, width * bpp, bpp == 2};
    const unsigned pages = census_pages(fb);
    if (!pages) return 4;
    for (unsigned page = 0; page < pages; ++page) {
        draw_census(fb, page);
        char name[1024]; snprintf(name, sizeof(name), "%s-%u.ppm", argv[1], page);
        FILE* file = fopen(name, "wb");
        if (!file) return 5;
        fprintf(file, "P6\n%d %d\n255\n", width, height);
        for (unsigned i = 0; i < unsigned(width * height); ++i) {
            if (bpp == 2) {
                const unsigned c = reinterpret_cast<const uint16_t*>(fb.base)[i];
                fputc(((c >> 11) & 31) * 255 / 31, file);
                fputc(((c >> 5) & 63) * 255 / 63, file);
                fputc((c & 31) * 255 / 31, file);
            } else {
                const unsigned c = reinterpret_cast<const uint32_t*>(fb.base)[i];
                fputc(c >> 16, file); fputc(c >> 8, file); fputc(c, file);
            }
        }
        fclose(file);
    }
    for (unsigned i = 0; i < 64; ++i)
        if (bytes[i] != 0xA5 || bytes[bytes.size() - 1 - i] != 0xA5) return 6;
    printf("{\"width\":%d,\"height\":%d,\"bpp\":%d,\"rows\":%u,\"pages\":%u,\"guards\":true}\n",
           width, height, bpp, census_rows(fb, 0, false), pages);
}
