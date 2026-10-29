#!/usr/bin/env python3
"""Check feature-OFF production excerpts against the recorded integration base.

This is a 32-bit host preprocessing/object gate, not a Dreamcast ABI or image
claim. No target SDK, game assets, or 32-bit host runtime libraries are needed.
"""
import argparse
import hashlib
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[3]
PRELUDE = '''typedef unsigned long u32;
typedef unsigned short u16;
typedef unsigned char u8;
typedef float f32;
extern "C" void re4dc_log(const char*, ...);
'''
LAYOUT = '''struct cAtariInfo {
    u8 prefix[16]; AtRadius m_radius2; u8 middle[6]; AtFlag16 m_flag;
};
struct cEm { cEm* pNext; cAtariInfo atari; };
'''
ENTRY = '''
extern "C" int collision_probe(cEm* head) {
    AtList list={0,0,-1}; AtCand cache={0,0,0,0,-1}; cEm* out[ATCHK_MAX];
    return atchkCandidates(&cache,&list,head,7,out);
}
'''


def excerpt(base):
    def read(path):
        if base:
            return subprocess.check_output(
                ["git", "show", f"{base}:{path}"], cwd=ROOT, text=True)
        return (ROOT / path).read_text()
    source = read("src/game/at_mod.cpp")
    header = read("include/atariInfo.h")
    wrappers = header[header.index('extern "C" u32 re4dc_atari_seq;'):
                      header.index('#define RE4DC_AT_FLAG16')]
    collect = source[source.index('#define ATCHK_MAX'):
                     source.index('#if defined(RE4DC_ATCHK_LIST)')]
    start = source.index('#if defined(RE4DC_ATLIST_512)')
    helpers = source[start:source.index('static int atchkCollectEm(', start)] + '\n#endif\n'
    return PRELUDE + wrappers + LAYOUT + collect + helpers + ENTRY


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", default="8f222fb41219f4dad889fd91c110b4b98e82aaeb")
    args = parser.parse_args()
    baseline, candidate = excerpt(args.baseline), excerpt(None)
    with tempfile.TemporaryDirectory(prefix="atchk-off29-") as directory:
        probe = Path(directory) / "off-probe.cpp"
        obj = Path(directory) / "off-probe.o"
        for cache in (1, 2):
            results = []
            for source, zero in ((baseline, False), (candidate, False), (candidate, True)):
                probe.write_text(source)
                flags = ["-m32", "-std=c++11", "-DRE4DC_ATCHK_LIST=1",
                         f"-DRE4DC_ATCHK_CACHE={cache}"]
                if zero:
                    flags.append("-DRE4DC_ATCHK_DISTINCT29=0")
                preprocessed = subprocess.check_output(
                    ["g++", *flags, "-E", "-P", str(probe)])
                subprocess.run(["g++", *flags, "-O2", "-fno-ident",
                                "-fno-asynchronous-unwind-tables", "-c", str(probe),
                                "-o", str(obj)], check=True)
                results.append((preprocessed, obj.read_bytes()))
            assert results[0] == results[1] == results[2], f"cache={cache}: OFF excerpt differs"
            print(f"cache={cache}: baseline/absent/zero preprocessing and host object identical; "
                  f"sha256={hashlib.sha256(results[0][1]).hexdigest()}")


if __name__ == "__main__":
    main()
