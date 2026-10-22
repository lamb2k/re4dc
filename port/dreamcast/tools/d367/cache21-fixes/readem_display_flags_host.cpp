// Extend the sealed H064 actual-source/SDK fixture without replacing its bodies.
#define main h064_characterization_main
#include "motion_lifetime_host.cpp"
#undef main

static void occupy_modules(int free_slot)
{
    std::memset(EmReadModule, 0, sizeof(EmReadModule));
    for (int i = 0; i < 4; ++i) {
        EmReadModule[i].pArc = i == free_slot ? nullptr : arena + 32 * i;
        EmReadModule[i].id = i + 2;
    }
}

static int display_flags_matrix()
{
    begin();
    std::vector<unsigned> patterns = {
        0, 0x800, 0xfffff7ff, 0xffffffff, 0x12340800,
        0xa5a55a5a, 0x80000000, 0x7fffffff
    };
    unsigned seed = 0x48303634;
    for (int i = 0; i < 16; ++i) {
        seed ^= seed << 13;
        seed ^= seed >> 17;
        seed ^= seed << 5;
        patterns.push_back(seed);
    }
    unsigned full_slot_calls = 0, failure_calls = 0, success_calls = 0;
    for (unsigned flags : patterns) {
        occupy_modules(-1);
        ReadModule before[4];
        std::memcpy(before, EmReadModule, sizeof(before));
        transport_calls = 0;
        global.Disp_flg = flags;
        assert(readEm(1, arena + 256, 32) == nullptr);
#if READ_EM_FLAGS_EXPECT_RESTORE
        assert(global.Disp_flg == flags);
#else
        assert(global.Disp_flg == 0xfffff7ff);
#endif
        assert(transport_calls == 0);
        assert(std::memcmp(before, EmReadModule, sizeof(before)) == 0);
        ++full_slot_calls;

        // Each physical slot can be the only free slot. A transport refusal
        // leaves it available; immediate retry uses the same source decision.
        for (int free_slot = 0; free_slot < 4; ++free_slot) {
            occupy_modules(free_slot);
            std::memcpy(before, EmReadModule, sizeof(before));
            transport_calls = 0;
            transport_ok = false;
            global.Disp_flg = flags;
            assert(readEm(1, arena + 256, 32) == nullptr);
            assert(global.Disp_flg == flags && transport_calls == 1);
            assert(std::memcmp(before, EmReadModule, sizeof(before)) == 0);
            ++failure_calls;

            transport_ok = true;
            assert(readEm(1, arena + 256, 32) == arena + 256);
            assert(global.Disp_flg == flags && transport_calls == 2);
            assert(EmReadModule[free_slot].pArc == arena + 256);
            assert(EmReadModule[free_slot].size == 32);
            for (int other = 0; other < 4; ++other) {
                if (other != free_slot)
                    assert(std::memcmp(&before[other], &EmReadModule[other], sizeof(ReadModule)) == 0);
            }
            ++success_calls;
        }
    }
    std::cout << "readEm actual-source flags matrix: restore="
              << READ_EM_FLAGS_EXPECT_RESTORE << " patterns=" << patterns.size()
              << " full-slot=" << full_slot_calls << " transport-failure="
              << failure_calls << " success-after-refusal=" << success_calls
              << " PASS\n";
    return 0;
}

int main(int argc, char** argv)
{
    if (argc == 2 && std::string(argv[1]) == "slot-failure")
        return display_flags_matrix();
    return h064_characterization_main(argc, argv);
}
