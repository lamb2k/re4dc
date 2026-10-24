#!/usr/bin/env python3
"""Exercise both actual queue admission sites, capacity drains and abort exits.

Uses the established admission fixture's real SELECT_ONLY/ordinary setup,
queue snapshot, chunk_emit and chunk_flush bodies. Controlled emit edges assert
both UV words against the intended row. A wrapper around each unmodified flush
asserts bitwise pending-owner restoration, including early/late aborts. Geometry
and material TA words are covered separately by check_geometry.py.
"""
import argparse
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
ROOT = DC.parents[1]
spec = importlib.util.spec_from_file_location("uv_admission_reference", HERE.parent / "world_replay_lean/check_admission.py")
reference = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reference)


def replace_once(text, old, new):
    assert text.count(old) == 1, old
    return text.replace(old, new)


def sources():
    source, values, files = reference.sources()
    source = replace_once(source, "#include <cstdio>", "#include <cstdio>\n#include <cstdlib>")
    source = replace_once(source, "static std::vector<unsigned> events;", """static std::vector<unsigned> events;
static unsigned snapshot_mode,verified_rows,verified_flushes;
static float expected_uv[49][2];""")
    source = replace_once(source, "const unsigned call=pick_calls++;++binds;", """const unsigned call=pick_calls++;++binds;
#if RE4DC_SCENERY_UV_SNAPSHOT
  assert(ps2);const unsigned expected=ps2[0]==0x1234?48:ps2[0]-1;
  assert(expected<49&&std::memcmp(p.uv_offset,expected_uv[expected],sizeof(p.uv_offset))==0);
  ++verified_rows;
#endif""")
    source = replace_once(source, "Part part{test.current,{.125f,-.25f}};", """Part part{test.current,{snapshot_mode? .125f:0.0f,snapshot_mode?-.25f:0.0f}};
 if(snapshot_mode>=3){const std::uint32_t special[2]={snapshot_mode==3?0x80000000U:0x7f812345U,snapshot_mode==3?0x7fc12345U:0xffc54321U};
  std::memcpy(part.uv_offset,special,sizeof(special));}
 std::memcpy(expected_uv[48],part.uv_offset,sizeof(part.uv_offset));""")
    source = replace_once(source,
        "x.cull_far=1000;x.lod_scale=2;x.index=0;x.first=j;x.count=1;",
        """x.cull_far=1000;x.lod_scale=2;x.index=0;x.first=j;x.count=1;
  if(snapshot_mode>=2){expected_uv[j][0]=float(int(j%7)-3)*.125f;
   expected_uv[j][1]=j%5?float(int(j%5)-2)*.0625f:-0.0f;}
  else std::memcpy(expected_uv[j],part.uv_offset,sizeof(part.uv_offset));
#if RE4DC_SCENERY_UV_SNAPSHOT
  std::memcpy(x.uv_offset,expected_uv[j],sizeof(x.uv_offset));
#endif""")
    actual = values['CHUNK_FLUSH']
    wrapped = actual.replace('auto chunk_flush=[&]()->int', 'auto chunk_flush_actual=[&]()->int', 1)
    wrapped += """;
 auto chunk_flush=[&]()->int{
  std::uint32_t saved[2];std::memcpy(saved,part.uv_offset,sizeof(saved));
  const int result=chunk_flush_actual();
  assert(std::memcmp(saved,part.uv_offset,sizeof(saved))==0);++verified_flushes;
  return result;
 }"""
    source = replace_once(source, actual, wrapped)
    source = replace_once(source, "// Capture queue state before final replay.", """// Model the dynamic owner scope ending after queued admission. The actual
 // per-row snapshot must survive this reset before the final replay.
 if(snapshot_mode>=2)part.uv_offset[0]=part.uv_offset[1]=0.0f;
 // Capture queue state before final replay.""")
    source = replace_once(source, "int main(){\n unsigned cases=0;", """int main(int argc,char** argv){
 snapshot_mode=argc>1?unsigned(std::strtoul(argv[1],nullptr,10)):0;
 unsigned cases=0;""")
    source = replace_once(source,
        'std::fprintf(stderr,"PASS actual queue/dispatch controls cases=%u\\n",cases);',
        'std::fprintf(stderr,"PASS actual queue/dispatch controls cases=%u verified_rows=%u verified_flushes=%u\\n",cases,verified_rows,verified_flushes);')
    return source, values, files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    source, values, files = sources()
    fixture = output / 'admission.cpp'
    fixture.write_text(source)
    rows, hashes = [], {}
    for pvs, select, batch, replay in itertools.product((0, 1), repeat=4):
        if pvs and batch:
            continue  # existing submit batch option excludes PVS
        combo = f'p{pvs}-s{select}-b{batch}-r{replay}'
        results = {}
        for snapshot in (0, 1):
            label = combo + f'-u{snapshot}'
            binary = output / label
            command = ['g++', '-std=c++20', '-O2', '-Wall', '-Wextra', '-Wno-unused-variable',
                f'-DRE4DC_SCENERY_SELECT_ONLY={select}', f'-DRE4DC_SCENERY_SUBMIT_BATCH={batch}',
                f'-DRE4DC_SCENERY_REPLAY_LEAN={replay}', f'-DRE4DC_SCENERY_UV_SNAPSHOT={snapshot}',
                f'-DRE4DC_PS2_PVS={pvs}', str(fixture), '-o', str(binary)]
            run = subprocess.run(command, cwd=ROOT, capture_output=True)
            (output / (label + '.compile.log')).write_bytes(run.stdout + run.stderr)
            assert run.returncode == 0, (label, run.stderr.decode())
            for mode in ((0, 1) if snapshot == 0 else (0, 1, 2, 3, 4)):
                run = subprocess.run([str(binary), str(mode)], cwd=ROOT, capture_output=True)
                key = label + f'-m{mode}'
                (output / (key + '.stdout')).write_bytes(run.stdout)
                (output / (key + '.stderr')).write_bytes(run.stderr)
                assert run.returncode == 0, (key, run.stderr.decode())
                assert len(run.stdout.splitlines()) == 3564 * 2, key
                hashes[key] = hashlib.sha256(run.stdout).hexdigest()
                results[snapshot, mode] = run.stdout
        for mode in (0, 1):
            assert results[0, mode] == results[1, mode], (combo, mode, 'static full event words differ')
        rows.append(dict(pvs=pvs, select=select, submit_batch=batch, replay_lean=replay,
            static_comparisons=3564*2, dynamic_and_special_word_cases=3564*3,
            pending_restore_assertions=True, both_row_uv_words_asserted=True))
    report = dict(status='PASS', baseline='28da09802ed9ff6756529bab02978230983453be',
        static_comparisons=3564*2*len(rows), dynamic_and_special_word_cases=3564*3*len(rows),
        process_cases=3564*7*len(rows), configurations=len(rows)*2,
        source_sha256={str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in files},
        fixture_sha256=hashlib.sha256(source.encode()).hexdigest(),
        extracted_sha256={name: hashlib.sha256(value.encode()).hexdigest() for name, value in values.items()},
        combinations=rows, output_sha256=hashes, scope=__doc__)
    (output / 'admission-controls.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ('status', 'configurations', 'static_comparisons', 'dynamic_and_special_word_cases', 'process_cases')}))


if __name__ == '__main__':
    main()
