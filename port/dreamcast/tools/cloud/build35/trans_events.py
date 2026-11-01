#!/usr/bin/env python3
"""Run Build35 events in extracted production texture and skin decision bodies.

The complete commonScreenMatSub body and all three native texture-init blocks
run against explicit allocator/defer/matrix/skinning edge doubles. Palette
tests execute their production admission/event prefixes, not matrix arithmetic.
No private data, whole-game replay, target timing or image proof is claimed.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
OLD = HERE.parent / 'build34'
sys.path.insert(0, str(OLD))
import front_sources as source


def body_at(text, opening):
    depth = 1
    end = opening + 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[opening:end]


def extraction():
    trans = source.TRANS.read_text()
    values = source.source_values()
    types = source.render((OLD / 'front_fixture_types.hpp.in').read_text(), values)
    callers = []
    for i, name in enumerate(('static void frontNativeModelTrans(', 'static int sceneryGate(', 'static int propGate(')):
        function = source.function(trans, name)
        start = function.index('#if RE4DC_FRONT_TEXOBJ\n            if (!frontTexInit(')
        opening = function.index('{', start)
        fragment = function[start:opening] + body_at(function, opening)
        callers.append('static void caller' + str(i) + '(cModel* m,cModelInfo* info,ModelData* d) {\n'
                       'u32 i=0;ModelData* id=d;GxWork* gx=GXWORK();\n' + fragment + '\n}\n')
    macros = trans[trans.index('#define UV_WRAP_HI'):trans.index('// For every model info of the list:')]
    start = trans.index('int commonScreenMatSub(cModel* m, cModelInfo* info)\n{')
    skin = trans[start:trans.index('\n#if defined(RE4DC_CROWD_INVIS_SKIP)', start)]
    start = trans.index('static int MakeWeightPalette(Weight* w0, int n)\n{')
    ordinary = trans[start:trans.index('#if defined(RE4DC_SKIN_SH4ZAM)', start)]
    start = trans.index('static int MakeWeightPaletteExt(WeightExt* w0, int n)\n{')
    extended = trans[start:trans.index('    for (i = 0; i < n; i++', start)]
    palette = ordinary + '\n#undef w\n++palette_calls;return n;\n}\n' + extended + '\n#undef w\n++palette_calls;return n;\n}\n'
    return dict(TYPES=types, CALLERS=''.join(callers), UV=macros, SKIN=skin, PALETTE=palette)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--sanitize', action='store_true')
    args = parser.parse_args()
    out = args.output.resolve(); out.mkdir(parents=True, exist_ok=False)
    headers = ROOT / 'port/dreamcast/game/platform/include'
    inputs = [Path(__file__), HERE / 'trans_front_events.cpp.in', HERE / 'trans_skin_events.cpp.in',
              *source.source_files(), headers / 'fallback_audit35.h', headers / 'fallback_audit35.def',
              headers / 'fallback_audit29.h', headers / 'fallback_audit29.def']
    frozen = {str(path.relative_to(ROOT)): source.sha(path) for path in inputs}
    values = extraction()
    prelude = '''#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include "fallback_audit35.h"
static std::uint64_t events[re4dc::fa29::ReasonCount];
namespace re4dc { namespace fa29 { void hit(Reason r,std::uint32_t n){events[r]+=n;} } }
using namespace re4dc::fa35;
static unsigned checks=0,cases=0;
static const char* scenario="startup";
static void check(bool ok,const char* why){++checks;if(!ok){std::fprintf(stderr,"%s: %s\\n",scenario,why);std::exit(31);}}
static void clear_events(const char* label){scenario=label;++cases;std::memset(events,0,sizeof(events));}
static void expect(Reason r,std::uint64_t n){check(events[r]==n,"event amount");}
static std::uint64_t total(){std::uint64_t n=0;for(auto v:events)n+=v;return n;}
'''
    flags = ['-std=c++20', '-O2', '-fpermissive', '-Wall', '-Wextra', '-Wno-unused-function',
             '-Wno-unused-variable', '-I' + str(headers), '-DRE4DC_FALLBACK_AUDIT35=1']
    if args.sanitize:
        flags[1:2] = ['-O1', '-g', '-fsanitize=address,undefined', '-fno-omit-frame-pointer', '-no-pie']
    profiles = [('front-off', 'front', ['RE4DC_FRONT_TEXOBJ=0']),
                ('front-on', 'front', ['RE4DC_FRONT_TEXOBJ=1'])]
    for lazy, palette, face, native in ((1, 1, 1, 1), (1, 0, 0, 1), (0, 0, 0, 1), (0, 0, 0, 0)):
        for census in (0, 1):
            profiles.append((f'skin-l{lazy}-p{palette}-f{face}-n{native}-c{census}', 'skin',
                [f'RE4DC_NATIVE_ACTOR_SKIN_LAZY={lazy}', f'RE4DC_SKIN_PALETTE_LAZY={palette}',
                 f'RE4DC_LEON_FACE_LAZY={face}', f'RE4DC_NATIVE_ACTOR_SKIN={native}', f'RE4DC_SKIN_CENSUS={census}']))
    rows = []
    for name, kind, definitions in profiles:
        cpp = out / (name + '.cpp')
        cpp.write_text(prelude + source.render((HERE / f'trans_{kind}_events.cpp.in').read_text(), values))
        binary = out / name
        command = ['g++', *flags, *['-D' + v for v in definitions], str(cpp), '-o', str(binary)]
        run = subprocess.run(command, capture_output=True)
        (out / (name + '-compile.log')).write_bytes(run.stdout + run.stderr)
        if run.returncode: raise RuntimeError(run.stderr.decode())
        env = dict(os.environ)
        if args.sanitize:
            env.update(ASAN_OPTIONS='detect_leaks=0', UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
        run = subprocess.run([str(binary)], capture_output=True, env=env)
        (out / (name + '-run.log')).write_bytes(run.stdout + run.stderr)
        assert run.returncode == 0, (name, run.returncode, run.stderr.decode())
        rows.append(dict(profile=name, definitions=definitions, **json.loads(run.stdout)))
    assert frozen == {name: source.sha(ROOT / name) for name in frozen}, 'Source changed during gate'
    report = dict(status='PASS', scope=__doc__, sanitize=args.sanitize, source_sha256=frozen,
                  extraction_sha256={key: hashlib.sha256(value.encode()).hexdigest() for key,value in values.items()},
                  profiles=rows, cases=sum(row['cases'] for row in rows), checks=sum(row['checks'] for row in rows),
                  limits='External allocation, matrix arithmetic and rendering edges are doubles. '
                         'Palette prefixes stop before arithmetic; the complete production TU is compiled separately on SH-4. '
                         'ASan leak inspection is disabled because sandbox /proc traversal is unavailable.')
    receipt = out / 'trans-events.json'; receipt.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(status='PASS', profiles=len(rows), cases=report['cases'], checks=report['checks'], receipt=str(receipt))))


if __name__ == '__main__': main()
