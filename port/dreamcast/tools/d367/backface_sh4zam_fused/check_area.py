#!/usr/bin/env python3
"""Bind rotating/pipelined SDK arithmetic to the real compiler-selected DAG."""
import argparse,re,json,hashlib
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--overlay',type=Path,required=True);a=p.parse_args();here=Path(__file__).resolve().parent;dc=here.parents[2]
base=(dc/'game/platform/backface_sh4zam_area.inc').read_text();macro=base.split('        .macro SH4ZAM_BACKFACE_AREA\n')[1].split('        .endm')[0]
raw={8:'ax',9:'ay',10:'bx',11:'by',12:'cx',13:'cy'}
expected=re.sub(r'fr(\d+)',lambda m:'fr\\'+raw[int(m[1])] if int(m[1]) in raw else m[0],macro)
area=(a.overlay/'source/shz_strip_area.inc').read_text();actual=area.split('        .macro SHZ_STRIP_AREA ax,ay,bx,by,cx,cy\n')[1].split('        .endm')[0]
normalize=lambda s:[' '.join(x.split()) for x in s.splitlines() if x.strip()]
assert normalize(expected)==normalize(actual),'rotating determinant differs from compiler DAG'
s=(a.overlay/'source/shz_strip_fused.inc').read_text();phase=s.split('        .macro SHZ_PHASE',1)[1].split('.Lphase_terminal\\@:',1)[0]
ops=[x for x in normalize(phase) if x.startswith(('fmov ','fsub ','fmul ','fneg ','fmac '))]
compiler=normalize(expected)
carried=compiler[4:]+[r'fmov fr\cy,fr2',r'fmov fr\cx,fr0',r'fmov fr\ax,fr3',r'fmov fr\ay,fr1']
if ops==compiler:
    scheme='ordered compiler DAG'
else:
    assert ops==carried,('pipeline determinant/carry seeds differ',ops,carried)
    scheme='exact compiler DAG with four next-phase carry seeds'
    assert phase.index('fcmp/gt')<phase.index(r'fmov fr\cy,fr2'),'FR2 overwritten before compare'
    warm=s.split('        .macro SHZ_START',1)[1].split('.Lbatch_dispatch:',1)[0]
    seed=r"""        fmov fr11,fr2
        fmov fr12,fr3
        fmov fr10,fr0
        fmov fr13,fr1"""
    assert seed in warm,'first triangle is not seeded from original B/C'
if '        .macro SHZ_FULL_PHASE' in s:
    full=s.split('        .macro SHZ_FULL_PHASE',1)[1].split('        .endm',1)[0]
    fullops=[x for x in normalize(full) if x.startswith(('fmov ','fsub ','fmul ','fneg ','fmac '))]
    assert fullops==carried,('full-block determinant differs',fullops,carried)
    assert full.index('fcmp/gt')<full.index(r'fmov fr\cy,fr2'),'full FR2 overwritten before compare'
assert phase.index(r'fsub fr\ay,fr1')<phase.index(r'fmov.s @r0+,fr\ax'),'overwrote raw A before last dependency'
print(json.dumps(dict(rotating_and_pipelined_exact_compiler_DAG=True,arithmetic_instructions=len(compiler),scheme=scheme,baseline_sha256=hashlib.sha256(base.encode()).hexdigest(),sdk_area_sha256=hashlib.sha256(area.encode()).hexdigest(),scope='Instruction dataflow binding; exact opcodes separately executed against target-lowered C oracle.')))
