T = '/root/probe/lanes-20261016/ch4found/tree/'
def sub(s, old, new):
    assert s.count(old) == 1, old[:70]
    return s.replace(old, new)

p = T + 'port/dreamcast/game/platform/audio_aica.cpp'; s = open(p).read()
s = sub(s, """    g_strEntN = h[1];
    memcpy(g_strEnt, h + 4, g_strEntN * sizeof(StrEnt));""", """#if RE4DC_STR_ENT_MAX > 63
    // A file with more than 63 entries has a header of whole 2 KB sectors (16 + 32 x count bytes, aica_banks.py
    // build_streams; lane ch4found16: the castle disc's ch3 + ch4 file, 73 entries); the rest is read once, here.
    static_assert(RE4DC_STR_ENT_MAX <= 255, "the stream header must fit the 8 KB stream cache");
    if (h[1] > 63) {
        const u32 hdr = (16 + h[1] * (u32) sizeof(StrEnt) + 2047) / 2048 * 2048;
        if (fs_read(g_strFile, g_strCache + 2048, hdr - 2048) != (ssize_t) (hdr - 2048)) {
            re4dc_log("aica: bgm/aica_str.dat header (%u entries) short, disc streams stay silent\\n", (unsigned) h[1]);
            fs_close(g_strFile);
            g_strFile = -1;
            return false;
        }
    }
#endif
    g_strEntN = h[1];
    memcpy(g_strEnt, h + 4, g_strEntN * sizeof(StrEnt));""")
open(p, 'w').write(s)

p = T + 'port/dreamcast/game/Makefile'; s = open(p).read()
s = sub(s, "# AICA_STR_ENT_MAX=48 ship together. 32 bytes of .bss per entry (48: +512 B). The 2 KB header holds up to 63.\n",
"""# AICA_STR_ENT_MAX=48 ship together. 32 bytes of .bss per entry (48: +512 B). The 2 KB header holds up to 63; above
# 63 (lane ch4found16: the castle disc's ch3 + ch4 file, 73 entries, AICA_STR_ENT_MAX=80) the header is whole 2 KB
# sectors and the reader reads the rest once at boot (the 8 KB stream cache holds up to 255 entries).
""")
open(p, 'w').write(s)

p = T + 'port/dreamcast/tools/aica_banks.py'; s = open(p).read()
s = sub(s, "    pos = 2048   # header sector\n",
"""    # header: 16 + 32 x count bytes in whole 2 KB sectors (one sector up to 63 entries; more need AICA_STR_ENT_MAX > 63)
    hsz = max(STR_BLOCK, (16 + STR_ENT.size * len(keys) + STR_BLOCK - 1) // STR_BLOCK * STR_BLOCK)
    pos = hsz
""")
s = sub(s, """    assert len(hdr) <= 2048
""", """    assert len(hdr) <= hsz
""")
s = sub(s, "        f.write(hdr + bytes(2048 - len(hdr)))\n", "        f.write(hdr + bytes(hsz - len(hdr)))\n")
s = sub(s, "STREAM_PRESETS = {", """# The castle disc (three-disc layout: disc 2 = chapters 3 and 4; coordinator 10-16): one file, CH3_STREAMS (entries
# 0..54 in their order) + the chapter 4 streams it lacks (18). 73 entries: a two-sector header, AICA_STR_ENT_MAX >= 73
# (80). `--streams castle`. Measured against swapping a ch3 and a ch4 file at the chapter 4 save: 100,765,696 B on
# disc vs 114,851,840 B (the shared streams twice), +768 B of .bss (56 -> 80 entries) and one 2 KB read at boot.
CASTLE_STREAMS = CH3_STREAMS + [k for k in CH4_STREAMS if k not in CH3_STREAMS]
STREAM_PRESETS = {""")
s = sub(s, "                  'ch4': CH4_STREAMS}", "                  'ch4': CH4_STREAMS, 'castle': CASTLE_STREAMS}")
open(p, 'w').write(s)
print('ok')
