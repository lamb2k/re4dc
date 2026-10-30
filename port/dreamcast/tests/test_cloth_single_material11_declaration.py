#!/usr/bin/env python3
"""Compile actual Esp4e include scope with project headers; no modeled globals."""
from pathlib import Path
import argparse, hashlib, json, subprocess

ROOT=Path(__file__).resolve().parents[3]
OLD='6d7ee8035cd9ede21a88cf23a4cb2ecb3a99d683'

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',required=True,type=Path)
    out=p.parse_args().output.resolve();out.mkdir(parents=True,exist_ok=False)
    path='src/game/esp4e.cpp';current=(ROOT/path).read_text()
    old=subprocess.check_output(['git','show',OLD+':'+path],cwd=ROOT,text=True)
    assert '#include "espgen.h"' in current
    missing=current.replace('#include "espgen.h"','',1)
    flags=['g++','-m32','-std=c++20','-fpermissive','-w','-fsyntax-only',
           '-I'+str(ROOT/'include'),'-I'+str(ROOT/'src'),'-x','c++','-']
    rows=[]
    for name,source,selector,accepted in [
        ('current-on',current,1,True),('missing-header-on',missing,1,False),
        ('old-on',old,1,False),('absent',current,None,True),('zero',current,0,True)]:
        # Real include block and all its actual transitive project declarations.
        # Host -m32 permits recovered unsigned-int new/delete signatures without
        # rewriting project headers. This is syntax-only, not SH4/host linkage.
        prefix=source[:source.index('struct Esp4eWork')]
        probe=prefix+'''
#if defined(RE4DC_CLOTH_MATERIAL11) && RE4DC_CLOTH_MATERIAL11
auto declaration_scope11() { return g_pEspSys; }
static_assert(sizeof(decltype(g_pEspSys)) == 4);
#else
#ifdef ESPGEN_H
#error Material0 must not import the new effect-system header
#endif
#endif
'''
        cmd=flags if selector is None else flags+['-DRE4DC_CLOTH_MATERIAL11='+str(selector)]
        result=subprocess.run(cmd,input=probe,text=True,capture_output=True)
        (out/(name+'.cpp')).write_text(probe)
        (out/(name+'.log')).write_text(result.stdout+result.stderr)
        assert (result.returncode==0)==accepted,(name,result.stderr)
        if not accepted:
            assert 'g_pEspSys' in result.stderr and 'not declared' in result.stderr,result.stderr
        rows.append(dict(name=name,command=cmd,returncode=result.returncode,
                         input_sha256=hashlib.sha256(probe.encode()).hexdigest()))
    # The imported declaration is authoritative; no local declaration/stub is
    # inserted by this check or by the producer's synthetic global definition.
    header=(ROOT/'include/espgen.h').read_text()
    assert 'extern cEspSystem* g_pEspSys;' in header
    assert 'cEspSystem* g_pEspSys;' in (ROOT/'src/game/eff_sys.cpp').read_text()
    receipt=dict(status='PASS',rows=rows,old_missing_declaration=OLD,
                 source_sha256=hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),
                 scope='actual include block/project headers, host32 syntax only; no modeled global, link or target claim')
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt))

if __name__=='__main__':main()
