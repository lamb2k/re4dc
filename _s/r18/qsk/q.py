"""RAM-only host check using pinned actual compiled actor inputs; no SDK/media."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

HERE = Path('/root/work/lanes/cast-ps2-25/port/dreamcast/tools/d367/gc_port23')
GAME = HERE.parents[2] / 'game'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', type=Path, required=True)
    parser.add_argument('--profile-sha', required=True)
    parser.add_argument('--runtime-sha', required=True)
    parser.add_argument('--hair-sha', required=True)
    args = parser.parse_args()
    if sha(args.profile) != args.profile_sha:
        raise ValueError('profile pin mismatch')
    knobs = dict(line.split('=', 1) for line in args.profile.read_text().splitlines() if '=' in line)
    for name, value in {'COARSE_LEON': '1', 'ACTOR_TRANSACTION': '1', 'LEON_HAND_PACK': '1', 'LEON_LOD': '0'}.items():
        if knobs.get(name) != value:
            raise ValueError('unsupported actual profile: '+name)
    runtime = Path(knobs['LEON_HAND_PACK_HDR'])
    hair = Path(knobs['PS2_LEON_DIR']) / 'ps2leon_hair_runs.h'
    pins = {args.profile: args.profile_sha, runtime: args.runtime_sha, hair: args.hair_sha}
    for path, expected in pins.items():
        if sha(path) != expected:
            raise ValueError('input pin mismatch: '+str(path))
    fixture = r'''
#include "gc_asset_actor.h"
#include "coarse_actor_preflight.h"
#include <cassert>
#include <cstdio>
#include <initializer_list>
#include RUNTIME
#include HAIR
#define RE4DC_OWNER_SPAN(a) {reinterpret_cast<const unsigned char*>(a),sizeof(a)}
#define RE4DC_OWNER_INPUT(ns,prefix,c,bones) re4dc_source::ChunkInput{RE4DC_OWNER_SPAN(ns::prefix##_pos),RE4DC_OWNER_SPAN(ns::prefix##_nrm),RE4DC_OWNER_SPAN(ns::prefix##_uv),RE4DC_OWNER_SPAN(ns::prefix##_gx),RE4DC_OWNER_SPAN(ns::prefix##_weights),c.position_count,c.normal_count,c.palette_count,c.triangles,bones}
#define RE4DC_LEON_HAIR_UV_DATA leon_hair_runs::uv
#define RE4DC_LEON_HAIR_UV_SIZE sizeof(leon_hair_runs::uv)
extern "C" void re4dc_log(const char*,...){}
namespace re4dc_gcasset{bool ensure_disc_catalog(){return true;}}
#include "gc_asset_actor_compiled.inc"
int main(){using namespace re4dc_gcasset;assert(install(nullptr,0));begin_startup_closed(1,Required);re4dc_gcasset_actor_startup();assert(gcasset_compiled_actor.serial);AssetDescription row;assert(describe_checked(gcasset_compiled_actor.asset,&row));assert(row.provenance==Unknown);for(unsigned k=0;k<8;++k)if(k!=5 && k!=6)assert(gcasset_compiled_current(k));for(auto b:row.digest.bytes)printf("%02x",b);putchar(32);AssetDescription sk;assert(describe_checked(gcasset_compiled_actor.layout_asset,&sk));for(auto b:sk.digest.bytes)printf("%02x",b);puts("");}
'''.replace('RUNTIME', json.dumps(str(runtime))).replace('HAIR\n', json.dumps(str(hair))+'\n')
    dependencies = [GAME / 'platform/include/gc_asset_actor_compiled.inc', GAME / 'platform/gc_asset_payloads.cpp',
                    GAME / 'platform/include/gc_asset_payloads.h', GAME / 'platform/include/coarse_actor_preflight.h']
    before = {str(path): sha(path) for path in dependencies}
    with tempfile.TemporaryDirectory(prefix='gc-port23-real-actor-', dir='/dev/shm') as temporary:
        root = Path(temporary);(root / 'fixture.cpp').write_text(fixture)
        command = ['g++', '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror', '-DRE4DC_GC_ASSET_GATE=1',
                   '-DRE4DC_ACTOR_TRANSACTION=1', '-DRE4DC_LEON_HAND_PACK=1', '-DRE4DC_LEON_LOD=0',
                   '-I', str(GAME / 'platform/include'), str(root / 'fixture.cpp')]
        command += [str(GAME / ('platform/gc_asset_'+part+'.cpp')) for part in ('gate', 'members', 'payloads')]
        subprocess.run(command+['-o', str(root / 'fixture')], check=True)
        result = subprocess.run(['/lib64/ld-linux-x86-64.so.2', str(root / 'fixture')], check=True, capture_output=True, text=True)
    for path, expected in pins.items():
        if sha(path) != expected:
            raise ValueError('input changed during qualification: '+str(path))
    if before != {str(path): sha(path) for path in dependencies}:
        raise ValueError('source changed during qualification')
    print(json.dumps({'qualification': 'host actual compiled sources only', 'provenance': 'unknown',
                      'geometry_sha256': result.stdout.strip(), 'inputs': {str(k): v for k, v in pins.items()},
                      'source': before, 'target_or_gate_acceptance': False}, sort_keys=True))


if __name__ == '__main__':
    main()
