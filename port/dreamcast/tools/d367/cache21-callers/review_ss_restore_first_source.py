#!/usr/bin/env python3
"""Read-only new restore guard/source and actual Make stanza parse; no build."""
import argparse,hashlib,json,pathlib,subprocess
from audit_archive_borrow_boundaries import body
p=argparse.ArgumentParser();p.add_argument('--repo',required=True);p.add_argument('--out',required=True);a=p.parse_args();repo=pathlib.Path(a.repo);out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=False)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def git(path):return subprocess.check_output(['git','-C',str(repo),'show','54ba44079:'+path])
path='port/dreamcast/game/sscrn_bridge.cpp';raw=(repo/path).read_bytes();text=raw.decode();baseline=git(path).decode();block=text[text.index('#if RE4DC_SS_RESTORE_VALIDATE_FIRST'):text.index('#endif',text.index('#if RE4DC_SS_RESTORE_VALIDATE_FIRST'))+len('#endif\n')]
assert sha(raw)=='2c9179df90c206bf079d3915f4ade4175ed8b0f2f79ca774cfadf0379de123b9';assert text.replace(block,'',1)==baseline
close,_,_=body(text,'extern "C" void re4dc_subscreen_swap_close(');early=close.index('#if RE4DC_SS_RESTORE_VALIDATE_FIRST');assert close.index('h = hash_words(')<early<close.index('re4dc_logic_trace_swap_close()')<close.index('re4dc_ssb_close()')<close.index('swapped = false;')<close.index('re4dc_motion_forget_dead_heaps()');assert close.count('if (h != open_hash) re4dc_missing(')==2
mem=(repo/'port/dreamcast/game/platform/mem.cpp').read_bytes();missing,lo,hi=body(mem.decode(),'void re4dc_missing(');assert 'for (;;) {' in missing and 'thd_sleep(1000);' in missing
makepath='port/dreamcast/game/game30.mk';mk=(repo/makepath).read_bytes();m=mk.decode();stanza=m[m.index('SS_RESTORE_VALIDATE_FIRST ?= 0'):m.index('EVENT_MANAGER_STORAGE_FLAGS ?=')];assert m.replace('# Conditional failed-restore containment; optional source candidate only.\n'+stanza,'',1)==git(makepath).decode()
probes=[]
for value in [None,'0','1','2','-1','yes','']:
 command=['make','--no-print-directory','-s','-n','-f','-','audit']+([]if value is None else ['SS_RESTORE_VALIDATE_FIRST='+value]);r=subprocess.run(command,input=stanza+'\n$(info AUDIT_FLAGS=$(GAME_CPPFLAGS))\naudit:\n',text=True,capture_output=True)
 assert (r.returncode==0)==(value in [None,'0','1']);assert (('-DRE4DC_SS_RESTORE_VALIDATE_FIRST=1'in r.stdout)==(value=='1'))
 probes.append(dict(value=value,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr))
owner=pathlib.Path('/root/probe/cache21-ss-restore-first-host-20261022-01/receipt.json');ownerraw=owner.read_bytes();r=json.loads(ownerraw);assert r['source_sha256']==sha(raw) and r['disabled_preprocessed_function_exact'] is True
result=dict(scope='Independent source/actual Make stanza parsing only; no compiler/build/guest',source_sha256=sha(raw),game30_sha256=sha(mk),all_other_source_bytes_equal_54ba=True,all_other_game30_bytes_equal_54ba=True,source_patch=block,make_stanza=stanza,make_probes=probes,actual_missing=dict(path='port/dreamcast/game/platform/mem.cpp',file_sha256=sha(mem),start=lo,end=hi,body=missing,nonreturning_loop=True),owner_host_receipt=dict(path=str(owner),sha256=sha(ownerraw),reported_flags=['matching_restore_sequence_unchanged','enabled_mismatch_halts_before_backing_close_thaw_or_recount','disabled_preprocessed_function_exact'],not_reexecuted=True),limitations=['Conditional fault containment only; no observed corruption/issue52 cause','Full archive/reset lifetime and source-pointer validity not established'])
(out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(result='PASS',make_modes=len(probes),source_guard='early before backing close/thaw/recount',fresh_bytes=(out/'receipt.json').stat().st_size)))