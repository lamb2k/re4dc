#!/usr/bin/env python3
"""RAM-only controls for the UNAPPLIED selected-target owner proposal."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import zlib

sys.dont_write_bytecode = True
from check_queued_affine import function
from selected_target_changes import NATIVE, MAKE, CERTIFY, read_inputs, propose, proposal_patch


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def extract(native, runtime, selector):
    start = native.index('namespace dyn {')
    end = native.index('\n}\n#endif', native.index('unsigned query(unsigned id)', start))+2
    dyn = native[start:end]
    select_start = native.index('#if RE4DC_PS2_WORLD_DYNAMIC\n        const float* affine=pl.affine;')
    select_end = native.index('#if RE4DC_PS2_WORLD_LEAN\n#if RE4DC_SKY_ANY', select_start)
    early_start = native.index('#if RE4DC_PS2_PVS && !RE4DC_PS2_PVS_SELECTED_TARGETS\n        const std::uint8_t* const pvs_cur=')
    early_end = native.index('#if RE4DC_PS2_PASS_MASK==2', early_start)
    early_hidden_start = native.index('#if RE4DC_PS2_PVS && !RE4DC_PS2_PVS_SELECTED_TARGETS\n        if(pvs_cur && pvs::hidden(i))')
    area_start = native.index('#if RE4DC_PS2_AREA_HIDE', early_hidden_start)
    area_end = native.index('#if RE4DC_PS2_PASS_MASK', area_start)
    assign = re.findall(r'\b(?:x\.placement|d\.pvs_placement)=[^;]+;', native[select_end:])
    if len(assign) != 3:
        raise AssertionError('all three captured-identity assignments must remain')
    native_cut_calls = re.findall(r'\b(?:pvs::)?can_cut\([^;\n]+', native)
    # Declaration plus hidden + knob-off + knob-on callers, and no others.
    if len(native_cut_calls) != 4:
        raise AssertionError('can_cut call-site inventory drifted: '+repr(native_cut_calls))
    cluster_start = native.index('#if RE4DC_PS2_PVS\n            if(pvs_set){')
    cluster_end = native.index('\n#endif', cluster_start)+len('\n#endif')
    runtime = runtime.replace(function(runtime, 'unsigned fpscr()'), 'unsigned fpscr(){return test_fpscr;}')
    return {
        'DYN': dyn, 'INTACT': function(native, 'extern "C" int re4dc_ps2_placements_intact('),
        'EYE': function(native, 'bool eye_of(const float* v,float e[3])'),
        'HIDDEN': function(native, 'bool hidden(unsigned i)'), 'RUNTIME': runtime,
        'EARLY': native[early_start:early_end],
        'EARLY_HIDDEN': native[early_hidden_start:area_start],
        'AREA_GATE': native[area_start:area_end], 'SELECT': native[select_start:select_end],
        'SET_SELECTOR': re.search(r'd\.pvs_set=pvs_cur;', native[select_end:]).group(),
        'SET_DIRECT': re.search(r'if\(pvs_cur\)\{d\.pvs_set=pvs_cur;d\.pvs_first=[^\n]+', native[select_end:]).group(),
        'QUEUE_SELECT': assign[0], 'DIRECT': assign[1], 'QUEUE_LEGACY': assign[2],
        'REPLAY': re.search(r'e\.pvs_placement=x\.placement;', native).group(),
        'CHUNK_OK': function(selector, 'bool chunk_ok()const'),
        'CHUNK_EMIT': function(native, '__attribute__((noinline)) int chunk_emit('),
        'RESTART': function(native, '[[gnu::always_inline]] void chunk_restart()'),
        'OBSERVED': function(native, 'void pvs_observed('),
        'FINISH': function(native, 'void pvs_finish(bool success)'),
        'CLUSTER_FILTER': native[cluster_start:cluster_end],
    }


def instantiate(template, excerpts):
    for name, value in excerpts.items():
        template = template.replace('@'+name+'@', value)
    if re.search(r'@[A-Z_]+@', template):
        raise AssertionError('unexpanded target fixture placeholder')
    return template


def preprocessed(source, macros):
    source = re.sub(r'^\s*#\s*include[^\n]*', '', source, flags=re.M)
    names = set(re.findall(r'\bRE4DC_[A-Z0-9_]+\b', source))
    defines = ''.join(f'#define {n} {macros.get(n,0)}\n' for n in sorted(names))
    return subprocess.check_output(['g++','-E','-P','-x','c++','-'], input=defines+source, text=True, stderr=subprocess.DEVNULL)


def config_controls(mk, certify, work):
    path = work/'proposal.mk'
    path.write_text(mk+'\n$(OBJDIR)/platform/native_static.o:\n\t@echo $(PLATFORM_CPPFLAGS)\n')
    results = []
    for pvs, selected, accepted in [(0,0,True),(1,0,True),(1,1,True),(0,1,False),(1,2,False),(1,'0 1',False),(1,'',False)]:
        run = subprocess.run(['make','-s','-f',str(path),'RAM/platform/native_static.o','OBJDIR=RAM',
                              f'PS2_PVS={pvs}',f'PS2_PVS_SELECTED_TARGETS={selected}','PS2_WORLD_ROOMS=1'], text=True, capture_output=True)
        if (run.returncode == 0) != accepted:
            raise AssertionError('make knob acceptance mismatch: '+run.stdout+run.stderr)
        if accepted and pvs and f'-DRE4DC_PS2_PVS_SELECTED_TARGETS={selected}' not in run.stdout:
            raise AssertionError('selected-target knob did not reach actual object flags')
        results.append({'pvs':pvs,'selected':selected,'accepted':accepted,'output':(run.stdout+run.stderr).strip()})
    start = certify.index('    if a.conditional_targets:\n        # This exact table/descriptor pair')
    end = certify.index("    if panels:(root/'pvs23_certificates.inc')",start)
    guard_code = '\n'.join(line[4:] for line in certify[start:end].splitlines())
    for conditional in (False,True):
        env = dict(a=SimpleNamespace(conditional_targets=conditional),lines=['int synthetic_descriptor;'])
        exec(guard_code,env)
        descriptor = '\n'.join(env['lines'])
        for selected in (None,0,1):
            prefix = '' if selected is None else f'#define RE4DC_PS2_PVS_SELECTED_TARGETS {selected}\n'
            run = subprocess.run(['g++','-E','-P','-x','c++','-'], input=prefix+descriptor, text=True,capture_output=True)
            accepted = not conditional or selected == 1
            if (run.returncode == 0) != accepted:
                raise AssertionError('emitted descriptor escaped selected-target requirement')
            results.append({'conditional_descriptor':conditional,'selected':selected,'accepted':accepted})
    return results


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence',type=Path)
    args=parser.parse_args()
    here=Path(__file__).resolve().parent;repo=here.parents[4]
    inputs=read_inputs(repo);proposed=propose(inputs)
    patch=proposal_patch(inputs,proposed)
    if patch != (here/'selected-targets-owner.patch').read_text():
        raise AssertionError('committed proposal patch differs from exact tested proposal')
    platform=repo/'port/dreamcast/game/platform'
    runtime=(platform/'include/pvs23_runtime.inc').read_text()
    proof=(platform/'include/pvs23_proof.hpp').read_text()
    selector=(platform/'include/scenery_chunk_select.inc').read_text()
    template=(here/'fixture_selected_targets.cpp.in').read_text()
    excerpts=extract(proposed[NATIVE],runtime,selector)
    generated=instantiate(template,excerpts)
    results=dict(host_only=True,base=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),
                 input_sha256={path:digest(data) for path,data in inputs.items()},
                 proposal_sha256=digest(patch),fixture_sha256=digest(generated),
                 runtime_sha256=digest(runtime),proof_sha256=digest(proof),selector_sha256=digest(selector),
                 compiler=subprocess.check_output(['g++','--version'],text=True).splitlines()[0],runs=[],mutations=[])
    with tempfile.TemporaryDirectory(prefix='selected-targets-',dir='/dev/shm') as tmp:
        work=Path(tmp)
        # Apply the exact proposal to a tiny RAM mirror, independently of the
        # in-memory replacement generator used to extract the fixture bodies.
        for path,data in inputs.items():
            target=work/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(data)
        subprocess.run(['patch','-s','-p1','-d',str(work),'-i',str(here/'selected-targets-owner.patch')],check=True)
        if any((work/path).read_text()!=data for path,data in proposed.items()):
            raise AssertionError('applied proposal differs from tested source')
        (work/'pvs23_proof.hpp').write_text(proof)
        crc=zlib.crc32(bytes.fromhex('aabbccdd'))
        (work/'synthetic_cert.inc').write_text('constexpr Panel synthetic_panels[]={{0,0,0,0,0,{0,1,2,3,2,1}}};\n'
            f'constexpr Certificate certificates[]={{{{0x10d,0x11223344,256,0x55667788,4,{crc}U,0,1,32,synthetic_panels,{{1000,1000,1000}}}}}};\n')
        source=work/'fixture.cpp';exe=work/'fixture'
        def run_fixture(data,selected,lean,root,expected=True):
            source.write_text(data)
            subprocess.run(['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror',
                            f'-DRE4DC_PS2_PVS_SELECTED_TARGETS={selected}',f'-DRE4DC_PS2_WORLD_LEAN={lean}',
                            f'-DRE4DC_PS2_WORLD_ROOT_POSE={root}',str(source),'-o',str(exe)],check=True)
            run=subprocess.run([str(exe)],text=True,capture_output=True)
            if (run.returncode==0)!=expected:
                raise AssertionError(run.stdout+run.stderr)
            return dict(selected_targets=selected,lean=lean,root_pose=root,exit=run.returncode,output=(run.stdout+run.stderr).strip())
        for selected in (0,1):
            for lean in (0,1):
                for root in (0,1):
                    results['runs'].append(run_fixture(generated,selected,lean,root))
        # Restore the early fresh-state gate while preserving every later
        # source/numeric/epoch check, so the false cut must be detected.
        old=dict(excerpts)
        old['EARLY']=old['EARLY'].replace(' && !RE4DC_PS2_PVS_SELECTED_TARGETS','')
        old['EARLY_HIDDEN']=old['EARLY_HIDDEN'].replace(' && !RE4DC_PS2_PVS_SELECTED_TARGETS','')
        old['SELECT']=re.sub(r'#if RE4DC_PS2_PVS && RE4DC_PS2_PVS_SELECTED_TARGETS\n.*?\n#endif\n','',old['SELECT'],flags=re.S)
        results['mutations'].append(dict(name='old-early-fresh-state',**run_fixture(instantiate(template,old),1,1,1,False)))
        missing=dict(excerpts);missing['SELECT']=missing['SELECT'].replace('pvs_source_placement==i && ','')
        results['mutations'].append(dict(name='post-selection-missing-provenance',**run_fixture(instantiate(template,missing),1,1,1,False)))
        results['configuration']=config_controls(proposed[MAKE],proposed[CERTIFY],work)
        comparisons=[]
        for pvs in (0,1):
            for dynamic in (0,1):
                for lean in (0,1):
                    macros=dict(RE4DC_PS2_PVS=pvs,RE4DC_PS2_WORLD_DYNAMIC=dynamic,RE4DC_PS2_WORLD_LEAN=lean,
                                RE4DC_PS2_PVS_SELECTED_TARGETS=0,RE4DC_PS2_WORLD_MESH=1,RE4DC_SCENERY_CHUNK=1)
                    before=preprocessed(inputs[NATIVE],macros);after=preprocessed(proposed[NATIVE],macros)
                    if before!=after:raise AssertionError('knob-off host source preprocessing changed')
                    comparisons.append(dict(pvs=pvs,dynamic=dynamic,lean=lean,sha256=digest(after)))
        results['knob_off_source_comparisons']=comparisons
    result=json.dumps(results,indent=2)+'\n';print(result,end='')
    if args.evidence:
        args.evidence.mkdir(parents=True,exist_ok=True)
        (args.evidence/'selected-targets-host.json').write_text(result)
        (args.evidence/'selected-targets-excerpts.json').write_text(json.dumps(excerpts,indent=2)+'\n')


if __name__=='__main__':main()
