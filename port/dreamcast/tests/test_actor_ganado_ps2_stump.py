#!/usr/bin/env python3
"""Private-input tests of the actual lifetime, owner, palette and cull consumers.

Appearance 2 (the em13 / em15 fixture) of the v3 variant package (lane stump17 10-17): --stump-dir is
ps2_ganado_stump.py --out (ganado_ps2_stump_runtime.h + ganado_var.re4gv). The loader reads the package through a
host fs seam (kos/fs.h shim) into a host "heap 4" cell. Covered: the stump (BIN 479) and the hand poses 450 (role 2)
and 454 (role 3) through bind, plan, palettes and the stump gate; package refusals (missing file, one flipped byte),
room leave and the movie lend / return. The other appearances share every consumer; the game gate covers them.

The fixture uses normalized pinned GC BIN bytes before actual archive adoption.
Only 32-bit pointer encoding, SDK matrices and SH4 assembly have host adapters;
production role lookup, digest, live info check, owner plan, immutable proof,
group stream construction and pregate code are compiled from the source tree.
No source data is included in this test or its committed support file.
"""
import argparse
import json
from pathlib import Path
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
GAME = ROOT / 'port/dreamcast/game'
sys.path.insert(0, str(ROOT / 'port/dreamcast/tools/d367'))
import model_registry as mr
from ps2_ganado_stump import PINS
from test_actor_ganado_app0_grip import function


BINS = (448, 450, 453, 454, 476, 478, 479)


def fixtures(inputs, out):
    archive, parse_tpl, le_mirror = mr.archive_facts(str(ROOT))
    result = {}
    for name in ('em13', 'em15'):
        path = inputs / (name + '.drs')
        assert mr.sha(path.read_bytes()) == PINS[path.name]
        arc = archive.Archive(str(path))
        # Empty tagged-less entries remain real archive-index slots. Exact BIN
        # payloads are copied without geometry or material simplification.
        count = 480
        data = bytearray(16 + count * 8)
        struct.pack_into('<I', data, 0, count)
        digest_rows = {}
        for i in range(count):
            no = i + 4
            struct.pack_into('<I', data, 16 + i * 4, len(data))
            if no in BINS:
                b = bytearray(arc.entry(i).data)
                swap = le_mirror.Swapper(b, name)
                with swap.bounded(0, len(b)):
                    le_mirror.fmt_bin(swap, 0, len(b), name)
                data[16 + count * 4 + i * 4:19 + count * 4 + i * 4] = b'BIN'
                digest_rows[no] = mr.sha(b)
                data += b
            elif no in (445, 477):
                facts = mr.tpl_facts(arc, parse_tpl, name, no)
                # Exact source TPL facts in the runtime's relocated R4NREF form.
                # Host offsets are absolute arena offsets; descriptor identity
                # is checked by the actual texture() and tpl_owned() consumers.
                b = bytearray(512)
                base = len(data)
                struct.pack_into('<3I', b, 0, 0x20af30, len(facts['textures']), base + 12)
                for k, t in enumerate(facts['textures']):
                    assert t['palette'] is None
                    th, px = 40 + k * 36, 180 + k * 32
                    struct.pack_into('<2I', b, 12 + k * 8, base + th, 0)
                    w, h, fmt = t['whf']
                    struct.pack_into('<HH7I3B', b, th, h, w, fmt, base + px, *t['sampler'])
                    b[px:px + 8] = b'R4NREF\0\0'
                    struct.pack_into('<5I', b, px + 8, *t['key'], w, h, fmt)
                data[16 + count * 4 + i * 4:19 + count * 4 + i * 4] = b'TPL'
                data += b
        struct.pack_into('<I', data, 4, len(data))
        target = out / (name + '-fixture.bin')
        target.write_bytes(data)
        result[name] = dict(path=str(target), sha256=mr.sha(data), normalized_bins=digest_rows)
    return result


def harness():
    material = (GAME / 'coarse_actor_material.inc').read_text()
    cast = (GAME / 'coarse_ganado_cast.cpp').read_text()
    definitions = material[material.index('namespace re4dc_material {'):material.index('\ninline bool readable')]
    checks = '\n'.join(function(material, s) for s in (
        'bool digest(', 'inline bool base_level_sampler(', 'Error texture(', 'inline bool source_appearance_type('))
    live = function(material, 'Error info(cModelInfo* i,const Role& row,Result& out,bool diagnostic)')
    live = live.replace('\n#endif\n', '\n', 1)  # closes the excluded alternate signature
    # The production field is a native pointer; the host preserves its four-byte
    # BIN ABI with Ptr32. This accessor is the sole pointer-cast adaptation.
    live = live.replace('reinterpret_cast<const unsigned char*>(d.pParts)',
                        'static_cast<const unsigned char*>(d.pParts.get())')
    start = material.index('#if RE4DC_ACTOR_GANADO_APP0_GRIP\n// Appearance 0 may use')
    source_material = material[start:material.index('extern "C" int re4dc_actor_material_certificate(', start)]
    native = cast[cast.index('namespace {\nnamespace gc'):cast.index('\nunsigned fingerprint(')]
    support = (Path(__file__).with_suffix('.inc')).read_text()
    before, after = support.split('// INSERT ACTUAL CONSUMERS HERE')
    return before + definitions + '\n' + r'''
bool readable(const void* p,unsigned n) { return host_readable(p,n); }
unsigned u32at(const void* p,unsigned at) {unsigned x;std::memcpy(&x,static_cast<const char*>(p)+at,4);return x;}
unsigned u16at(const void* p,unsigned at) {unsigned short x;std::memcpy(&x,static_cast<const char*>(p)+at,2);return x;}
const void* ptrat(const void* p,unsigned at) {unsigned x=u32at(p,at);return x && x<arena.size()?arena.data()+x:nullptr;}
''' + checks + '\n}\n#include "actor_lifetime.inc"\nnamespace re4dc_material {\n' + live + '\n}\n' + source_material + '\n' + native + '\n' + function(cast, 'bool visible(const cModelInfo* info) {') + '\n}\n#include "coarse_actor_owner_ganado.inc"\n#include "coarse_actor_geometry_once.inc"\n' + after


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('inputs', 'cast-dir', 'far-dir', 'extras-dir', 'stump-dir', 'out'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--sanitize', action='store_true')
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    fs = fixtures(a.inputs, a.out)
    bad = bytearray((a.stump_dir / 'ganado_var.re4gv').read_bytes())
    bad[4512 + 100] ^= 1  # one byte of geometry 2 (the 479 stump): digest refusal
    (a.out / 'bad.re4gv').write_bytes(bad)
    source = a.out / 'consumer.cpp'
    shim = a.out / 'hostinc' / 'kos'
    shim.mkdir(parents=True, exist_ok=True)
    # The package loader's only platform calls: KOS file reads, served from --stump-dir.
    (shim / 'fs.h').write_text('''#pragma once
#include <cstdio>
#include <cstring>
#include <sys/types.h>
typedef std::FILE* file_t;
#define FILEHND_INVALID nullptr
extern const char* host_package;
static unsigned host_opens;
inline file_t fs_open(const char* p,int) {
    ++host_opens;return std::strcmp(p,"/cd/dc/native/ganado/ganado_var.re4gv")?nullptr:std::fopen(host_package,"rb");
}
inline ssize_t fs_total(file_t f) {const long at=std::ftell(f);std::fseek(f,0,SEEK_END);const long n=std::ftell(f);std::fseek(f,at,SEEK_SET);return n;}
inline ssize_t fs_read(file_t f,void* b,size_t n) {return ssize_t(std::fread(b,1,n,f));}
inline int fs_close(file_t f) {return std::fclose(f);}
''')
    source.write_text(harness())
    result = []
    for far, reuse in ((0, 0), (1, 0), (1, 1), (1, 2)):
        binary = a.out / f'consumer-far{far}-reuse{reuse}'
        command = ['g++', '-std=c++17', '-O2', '-g', '-Wall', '-Wextra', '-Wno-unused-variable', '-Wno-unused-function',
                   '-Wno-misleading-indentation', '-DRE4DC_CROWD_FAR=' + str(far), '-DRE4DC_ACTOR_BIND_REUSE=' + str(reuse),
                   '-I' + str(a.out / 'hostinc'), '-I' + str(GAME), '-I' + str(GAME / 'platform/include'), '-I' + str(a.cast_dir),
                   '-I' + str(a.stump_dir), '-I' + str(a.extras_dir), '-I' + str(a.far_dir), str(source), '-o', str(binary)]
        if a.sanitize:
            command += ['-O1', '-fsanitize=address,undefined', '-fno-omit-frame-pointer', '-fno-pie', '-no-pie']
        build = subprocess.run(command, text=True, capture_output=True)
        (binary.with_suffix('.build.log')).write_text(build.stdout + build.stderr)
        if build.returncode:
            print(build.stderr[-14000:]); raise SystemExit(build.returncode)
        run = subprocess.run([str(binary), fs['em13']['path'], fs['em15']['path'], str(a.stump_dir / 'ganado_var.re4gv'),
                              str(a.out / 'bad.re4gv')], text=True, capture_output=True)
        (binary.with_suffix('.run.log')).write_text(run.stdout + run.stderr)
        print(run.stdout + run.stderr, end='')
        assert run.returncode == 0, (far, reuse, run.returncode)
        result.append(dict(far=far, bind_reuse=reuse, output=run.stdout, command=command))
    (a.out / 'summary.json').write_text(json.dumps(dict(status='PASS', sanitized=a.sanitize, fixtures=fs, consumers=result), indent=2) + '\n')


if __name__ == '__main__':
    main()
