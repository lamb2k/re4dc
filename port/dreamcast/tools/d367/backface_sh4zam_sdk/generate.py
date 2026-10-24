#!/usr/bin/env python3
"""Compile actual pinned SH4ZAM APIs into the fused strip emitter's area macro.

This is a fail-closed register adapter, not a hand-written replacement SDK body.
The compiler selects and schedules the arithmetic; the adapter verifies every
selected opcode, maps float argument registers to the emitter's live values,
removes the return and two ABI-only moves, and preserves the live coordinates.
"""
import argparse, hashlib, json, os, re, subprocess, tempfile
from pathlib import Path

PIN = '33fa4850cacb30dd0ad35485ef035526ec4ce782'
VERSION = '15.2.0'
FLAGS = ['-m4-single', '-ml', '-O2', '-std=gnu++17', '-DNDEBUG',
         '-fno-exceptions', '-fno-rtti', '-ffp-contract=fast', '-fno-fast-math']
EXPECTED = [
 'fsub fr4,fr6', 'fsub fr5,fr9', 'fsub fr5,fr7', 'fsub fr4,fr8',
 'fmul fr9,fr6', 'fmov fr7,fr0', 'fneg fr6', 'fmac fr0,fr8,fr6',
 'rts', 'fmov fr6,fr0']
ARGS = dict(a='fr5', b='fr4', c='fr7', d='fr6', e='fr9', f='fr8')
MAPPING = dict(fr4='fr9', fr5='fr8', fr6='fr2', fr7='fr0', fr8='fr1', fr9='fr3', fr0='fr0')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
def function(text, name):
    body = text.split('_' + name + ':\n', 1)[1].split('\n\t.size', 1)[0]
    return [' '.join(x.split()) for x in body.splitlines() if x.strip() and not x.strip().startswith('.')]
def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--compiler', default=os.getenv('SH4_CXX', '/opt/toolchains/dc/sh-elf/bin/sh-elf-g++'))
    p.add_argument('--check', action='store_true', help='Validate committed macro without writing it')
    p.add_argument('--receipt', type=Path)
    p.add_argument('--objects', type=Path, help='Keep target probe objects/disassembly in this owned directory')
    a = p.parse_args()
    here = Path(__file__).resolve().parent
    dc = here.parents[2]
    sdk = dc / 'game/third_party/sh4zam'
    include = sdk / 'include'
    target = dc / 'game/platform/backface_sh4zam_area.inc'
    pin = subprocess.check_output(['git', '-C', str(sdk), 'rev-parse', 'HEAD'], text=True).strip()
    if pin != PIN: raise SystemExit('SH4ZAM pin differs: ' + pin)
    if subprocess.check_output(['git','-C',str(sdk),'status','--porcelain'],text=True).strip():
        raise SystemExit('SH4ZAM checkout has local changes')
    version = subprocess.check_output([a.compiler, '-dumpfullversion'], text=True).strip()
    if version != VERSION: raise SystemExit('Unqualified SH-4 compiler: ' + version)
    with tempfile.TemporaryDirectory(prefix='bf-sdk-') as temporary:
        out = a.objects.resolve() if a.objects else Path(temporary)
        out.mkdir(parents=True, exist_ok=True)
        for source in ['area_probe', 'abi_probe']:
            subprocess.run([a.compiler, *FLAGS, '-I'+str(include), '-S', str(here/(source+'.cpp')),
                            '-o', str(out/(source+'.s'))], check=True)
            subprocess.run([a.compiler, *FLAGS, '-I'+str(include), '-c', str(here/(source+'.cpp')),
                            '-o', str(out/(source+'.o'))], check=True)
        area = function((out/'area_probe.s').read_text(), 'sdk_area_probe')
        if area != EXPECTED: raise SystemExit('Unqualified SDK area body: ' + repr(area))
        abi = (out/'abi_probe.s').read_text()
        for name, reg in ARGS.items():
            if function(abi, 'sdk_arg_' + name) != ['rts', 'fmov '+reg+',fr0']:
                raise SystemExit('Unqualified SH4 float argument ABI: ' + name)
        # Seed each mutable argument into scratch; preserve FR8..FR13 inputs.
        body = ['fmov fr11,fr2', 'fmov fr12,fr3', 'fmov fr10,fr0', 'fmov fr13,fr1']
        for line in area[:-2]:
            adapted = re.sub(r'fr\d+', lambda m: MAPPING[m[0]], line)
            if adapted != 'fmov fr0,fr0': body.append(adapted)
        files = [Path(__file__).resolve(), here/'area_probe.cpp', here/'abi_probe.cpp', dc/'room/backface_sh4zam.hpp',
                 include/'sh4zam/shz_vector.h', include/'sh4zam/shz_scalar.h',
                 include/'sh4zam/inline/shz_vector.inl.h', include/'sh4zam/inline/shz_scalar.inl.h']
        provenance = {str(f.relative_to(dc)): sha(f) for f in files}
        digest = hashlib.sha256(json.dumps(provenance, sort_keys=True).encode()).hexdigest()
        # FAST_STEP already has B in FR1/2 and C in FR12/13. Partition the
        # SAME compiler-selected DAG into stages around the existing SQ writes.
        # Only independent SUBs and the register move/FNEG swap are reordered.
        fast_map = dict(fr4=r'fr\ay', fr5=r'fr\ax', fr6='fr2', fr7='fr1',
                        fr8='fr13', fr9='fr12', fr0='fr0')
        fast = [re.sub(r'fr\d+', lambda m: fast_map[m[0]], line) for line in area[:-2]]
        stages = [('SH4ZAM_BACKFACE_CX ax', [1]),
                  ('SH4ZAM_BACKFACE_CY ay', [3]),
                  ('SH4ZAM_BACKFACE_BX ax', [2]),
                  ('SH4ZAM_BACKFACE_PRODUCT ay', [0, 4, 6]),
                  ('SH4ZAM_BACKFACE_FMAC', [5, 7])]
        fast_text = ''.join('        .macro '+name+'\n'+
                            ''.join('        '+fast[i]+'\n' for i in selected)+
                            '        .endm\n' for name, selected in stages)
        text = ('/* Generated by backface_sh4zam_sdk/generate.py from real SH4ZAM APIs.\n'
                ' * SDK ' + PIN + '; GCC ' + VERSION + '.\n'
                ' * Source/header identity ' + digest + '.\n'
                ' * FR8/9=A, FR10/11=B, FR12/13=C; result FR2.\n'
                ' * Clobbers FR0..3 only; preserves live coordinates and XMTRX.\n'
                ' * Build must run generate.py --check; never hand-edit this file. */\n'
                '        .macro SH4ZAM_BACKFACE_AREA\n' +
                ''.join('        '+line+'\n' for line in body) + '        .endm\n' + fast_text)
        if a.check:
            if not target.exists() or target.read_text() != text:
                raise SystemExit('Generated SH4ZAM area macro is stale')
        else: target.write_text(text)
        receipt = dict(sdk_pin=pin, compiler=version, compiler_path=str(Path(a.compiler).resolve()), compiler_sha256=sha(Path(a.compiler).resolve()), flags=FLAGS,
                       source_hashes=provenance, source_digest=digest,
                       target_macro_sha256=hashlib.sha256(text.encode()).hexdigest(),
                       actual_compiler_area=area, actual_float_abi=ARGS,
                       register_mapping=MAPPING, macro_body=body, fast_mapping=fast_map, fast_stages=stages,
                       scope='Target object and generated runtime arithmetic; no Flycast or hardware acceptance')
        if a.receipt:
            a.receipt.write_text(json.dumps(receipt, indent=2)+'\n')
        print(json.dumps(dict(sdk_pin=pin, compiler=version, instructions=len(body),
                              macro_sha256=receipt['target_macro_sha256'], checked=a.check)))
if __name__ == '__main__': main()
