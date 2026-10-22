from pathlib import Path
import ast,copy,json,hashlib
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18');D=Path(r'C:\Flycast-Evidence\re4-dreamcast\castle18-20261018\Test21\recovered-j-content-20261021');p=L/'observe-controlled-ch32-drain015.py';tree=ast.parse(p.read_text(encoding='utf-8'));ns=dict(inherited014_verified=True,page_advanced=False,invoked=True,exec_seen=True,held_seen=True);exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name in ['page_ready','prompt_ready']],type_ignores=[]),'actual015_gates','exec'),ns)
row=json.loads((D/'route-walk-controlled-ch32-drain014/controlled-drain014-observer-summary.json').read_text())['last'];audit=json.loads((D/'controlled-ch32-drain014-closed-audit.json').read_text());row['message0_source_identity'].update(current_offset_bytes=audit['closed_state']['source_identity']['current_offset_bytes'],opcode=audit['closed_state']['message0']['opcode'],next_opcode=audit['closed_state']['message0']['next_opcode']);tests=[]
def ck(n,v):assert v,n;tests.append(n)
ck('actual014typedintro_pagegate_accepts',bool(ns['page_ready'](row)));ck('actual014intro_cannotconfirmYes',not ns['prompt_ready'](row))
for field,v in [('current_offset_bytes',132),('opcode',4),('next_opcode',1),('language',0)]:
 q=copy.deepcopy(row);q['message0_source_identity'][field]=v;ck('rejectwrongintro_'+field,not ns['page_ready'](q))
for field,v in [('table_size',2),('button',0),('selection',1),('wait',1)]:
 q=copy.deepcopy(row);q['message0'][field]=v;ck('rejectwrongpage_'+field,not ns['page_ready'](q))
ns['page_advanced']=True;ck('neverrepeat_introA',not ns['page_ready'](row));ck('page_sentflag_alone_notYes',not ns['prompt_ready'](row))
q=copy.deepcopy(row);q['message0_source_identity'].update(current_offset_bytes=132,opcode=8,next_opcode=1);q['message0']['table_size']=2;ck('source_modeled_actual_choice_gate',bool(ns['prompt_ready'](q)));q['message0']['selection']=1;ck('rejectalreadyanswered',not ns['prompt_ready'](q))
r=dict(scope='Actual014 closedtypedintro tests plus source-modeled choicegate checks; no actual015 UI/input/guest. Existing014source/ABI remainsunchanged.',observer_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),actual014_state_sha256=audit['closed_state']['sha256'],actual014_audit_sha256=hashlib.sha256((D/'controlled-ch32-drain014-closed-audit.json').read_bytes()).hexdigest(),PASS=len(tests),tests=tests)
(L/'controlled-ch32-drain015-source-gates.json').write_text(json.dumps(r,indent=2)+'\n');print('PASS',len(tests),'actualintro/sourcegatecases, no guest')
