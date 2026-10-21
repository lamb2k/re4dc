#!/usr/bin/env python3
"""Source-first continuation of H050/H055; metadata only, no asset rescan.

The lexical inventory is a change detector and a remaining-work list, not C++
control-flow, linkage, simultaneity or lifetime proof. Reviewed rules below are
explicitly narrower than the discovered caller population.
"""
import argparse
import hashlib
import json
import re
import subprocess
from collections import Counter
from pathlib import Path

CENSUS_SHA = '3adb52b984ed441fe52d58b704d1abc392c11afc39e3ae24a78f551ba756ce60'
EVALUATORS = {
 'src/game/motion.cpp': ['MotionSetCore','MotionMoveCore','MotionGetSpeed','MotionGetPosition'],
 'src/game/shape.cpp': ['CalculateShape_new'],
 'src/game/cam_motion.cpp': ['CameraMotion::CameraMotion','CameraMotion::move'],
}
BLENDS = {
 'em10': ('em10BlendMotSet','m0, a','m, seq'),
 'em2b': ('em2bBlendMotSet','m0, ai','m, arg'),
 'em2c': ('em2cBlendMotSet','m0, aa','m, arg'),
 'em32': ('em32BlendMotSet','m0, m3i','m, arg'),
 'em35': ('em35BlendMotSet','m0, (int) m3','m, seq'),
 'em38': ('em38BlendMotSet','m0, (int) m3','m, seq'),
 'em39': ('em39BlendMotSet','m0, ai','m, seq'),
}
WRAPPER_SYMBOLS = [
 'HermiteInterpolation','FcvGetMaxFrame','MotionSetCore','MotionMove','MotionMoveF',
 'MotionMoveCore','MotionMoveSub','MotionGetSpeed','MotionGetPosition','MotionAddSpeed',
 'MotionBlendOff','MOT_SET','ShapeSet','SetShape','ShapeMove','CalculateShape_new',
 'motionSet','motionMove','backCheckSet','setEvtMotion','setGondolaMotion',
 'setR11DMotion','setDrill','setGatling','setUFOCatch','setGrenadeThrow','setMotData',
] + [v[0] for v in BLENDS.values()] + ['em32BlendMotSetI','em2cBlendMotSet2','plBlendMotSet']


def digest(b): return hashlib.sha256(b).hexdigest()
def mask_comments(s):
 return re.sub(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|//[^\n]*|/\*.*?\*/',
  lambda m: re.sub(r'[^\n]',' ',m[0]) if m[0].startswith(('/',)) else m[0],s,flags=re.S)
def mask(s):
 return re.sub(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'',
               lambda m: re.sub(r'[^\n]',' ',m[0]),s,flags=re.S)


def definitions(s):
 """Column-zero definitions only; conditional bodies are deliberately not a CFG."""
 z=mask(s)
 return [(m.start(),m.end(),m[1]) for m in re.finditer(
   r'^[^\n;{}#=]*?\b([A-Za-z_~][\w:~]*)\s*\([^;{}]*\)\s*(?:const\s*)?\{',z,re.M)
   if m[1] not in ('if','for','while','switch')]


def fn(s,name):
 """Exact reviewed name + source-style boundary; deliberately not a CFG."""
 z=mask(s)
 hits=list(re.finditer(r'^[^\n;{}#=]*?\b'+re.escape(name)+r'\s*\([^;{}]*\)\s*(?:const\s*)?\{',z,re.M))
 hits=[m for m in hits if not re.match(r'^\s*(?:if|for|while|switch|return)\b',z[m.start():m.end()])]
 assert len(hits)==1,(name,len(hits))
 start=hits[0].start();opening=hits[0].end();depth=1;end=opening
 # A raw #if can have mutually exclusive opening braces. The selected source
 # style uses a column-zero function close. Do not truncate at a compound Vec
 # literal/multiline call that the loose navigation index mistook for a function.
 closing=re.search(r'^}',z[opening:],re.M)
 if closing:end=opening+closing.end();depth=0
 else:
  while depth and end<len(z):
   depth+=(z[end]=='{')-(z[end]=='}');end+=1
 assert depth==0,(name,'unbalanced reviewed function')
 return s[start:end],s.count('\n',0,start)+1


def calls(texts,symbols=WRAPPER_SYMBOLS):
 pat=re.compile(r'\b('+ '|'.join(map(re.escape,symbols))+r')\s*\(')
 out=[]
 for path,s in sorted(texts.items()):
  z=mask(s);defs=definitions(s)
  for m in pat.finditer(z):
   # Preserve raw arguments as an explicit follow-up index; no constant folding.
   pos=m.end();depth=1
   while depth and pos<len(z):
    depth+=(z[pos]=='(')-(z[pos]==')');pos+=1
   context=None
   for i,(st,en,name) in enumerate(defs):
    end=defs[i+1][0] if i+1<len(defs) else len(s)
    if st<=m.start()<end:context=name
   line=s.count('\n',0,m.start())+1
   out.append(dict(path=path,line=line,symbol=m[1],context_hint=context,
                   arguments=s[m.end():pos-1].strip(),
                   classification='lexical occurrence; declaration, macro, inactive branch and indirect dispatch require review'))
 return out


def check_evaluators(texts):
 reviewed=[]
 for path,names in EVALUATORS.items():
  s=texts[path]
  assert s.count('Re4dcMotionLease keys(')==len(names),(path,'unreviewed lease-site change')
  for name in names:
   body,line=fn(s,name)
   assert 'Re4dcMotionLease keys(' in body,(path,name,'missing scoped lease')
   reviewed.append(dict(path=path,line=line,function=name,lease='local evaluation scope; source stores proxy/header'))
 # All functional Hermite invocations in these evaluators must be inside one of
 # these scopes. A new evaluator outside the three reviewed files fails too.
 for c in calls(texts,['HermiteInterpolation']):
  if c['path'].endswith(('.h','.hpp')):continue
  name=c['context_hint'];path=c['path']
  if name in EVALUATORS.get(path,[]):continue
  if path=='src/game/motion.cpp' and name=='HermiteInterpolation':continue
  # Bare declarations precede the first function. Shape's extern-C wrapper is
  # not treated as a function by definitions().
  if name is None:continue
  raise AssertionError(('unreviewed Hermite occurrence',c))
 assert '#define MOTION_KEY(w, i) native_keys[i]' in texts['src/game/motion.cpp']
 assert 'w->pHermite_data = tbl' in fn(texts['src/game/motion.cpp'],'MotionSetCore')[0]
 assert 'w->keyTbl = tbl' in fn(texts['src/game/cam_motion.cpp'],'CameraMotion::CameraMotion')[0]
 assert 'return data[0]' in fn(texts['src/game/motion.cpp'],'FcvGetMaxFrame')[0]
 return reviewed


def check_blends(texts):
 rows=[]
 for module,(name,main,second) in BLENDS.items():
  path=f'src/{module}/{module}.cpp';b,line=fn(texts[path],name)
  assert b.count('MotionSetCore(')==2,(name,'helper fan-out changed')
  assert main in b and second in b and 'm = m1' in b and 'm = m2' in b,(name,'selector changed')
  rows.append(dict(path=path,line=line,function=name,fcv='body m0 + one sign-selected m1 OR m2',
                   sequence_argument='m3 is sequence for em32/em35/em38; a/b/c otherwise'))
 m=texts['src/game/motion.cpp'];b,line=fn(m,'MotionMove')
 assert 'MotionMoveCore(m, MOTION(m), 0)' in b
 assert b.count('MotionMoveCore(m, MOTION(m)->blend, 0)')==2
 h,_=fn(m,'MotionHokan');assert 'prevMat' in h and 'HermiteInterpolation(' not in h and 'MotionMoveCore(' not in h
 s,_=fn(m,'MotionSetCore');assert '0x20000000' in s and 'MOTION(m)->blend = 0' in s
 assert 'PSMTXCopy(p->l_mat, p->prevMat)' in s
 return rows


def group(census,label,arcs,reason):
 a=census['archives'][label];records=[]
 for arc in arcs:
  assert str(arc) in a['clips'],(label,hex(arc),'not a selected FCV')
  records.append(a['clips'][str(arc)])
 # Deduplicate actual binding entry identity (or resident source offset), not
 # stream count or guessed content-key sharing across different bindings.
 cached={r['entry']:r for r in records if 'entry' in r}
 cold={i:r for i,r in cached.items() if r['state']=='cached-cold'}
 mtc=a['mtc']
 return dict(archive=label,native_sha256=a['native_sha256'],native_bytes=a['native_bytes'],mtc=mtc,
  source_arcs=[hex(x)for x in arcs],records=records,
  distinct_cached=len(cached),cached_payload_bytes=sum(r['bytes']for r in cached.values()),cold_bytes=sum(r['bytes']for r in cold.values()),
  strict_v3_over_two=bool(mtc and mtc['version']==3 and len(cold)>2),
  reason=reason,proof='reviewed local source demand, no runtime acceptance or all-state closure')


def reviewed_groups(census,texts):
 # These source assertions bind the metadata calculation to reviewed dispatch.
 for path,needle in [
 ('src/game/pl_npc.cpp','back = SUB_MOT(subSelf, 0x18)'),
 ('src/pl11/pl11.cpp','data = ARC(0x6D)'),
 ('src/em32/em32.cpp','MotionSetCore(em, w->pMot, ARC(0xAD)'),
 ('src/em32/em32.cpp','em32BodyMove(this)'),
 ('src/em38/em38.cpp','em38ShellControl(this)'),
 ('src/em39/em39.cpp','em39ArmControl(this)'),
 ('src/em10/em10.cpp','MotSetObj16(o, PL_ARC_PTR(em->subArc, 0x253)'),
 ]:assert needle in texts[path],(path,needle)
 result={
 'ashley-baseline-body-look-face':group(census,'qa-original:em/pl11.drs',[0x12,0x18,0x6d],'body + additive look-back + held face4: MTC entries0/6/61'),
 'ashley-fixed-body-look-face':group(census,'qa-fixed:em/pl11.drs',[0x12,0x18,0x6d],'same source group; all three moved inline by selected hot preparation'),
 'mendez-spear-negative':group(census,'qa-fixed:em/em35.drs',[0x6a,0x6d],'body + negative sign blend; ARC6b sequence excluded'),
 'mendez-spear-positive':group(census,'qa-fixed:em/em35.drs',[0x6a,0x6c],'body + other sign blend; mutually exclusive with negative pair'),
 'queen-wait-positive-shell':group(census,'later-castle:em/em38.drs',[0xc,0xe,0x41],'type0 wait positive turn + independent shell mode1; three FCV streams all inline'),
 'u3-form0-walk-positive-body':group(census,'prepared-u3:em/em32.drs',[0xb,0xd,0xad],'positive turn body+blend and independent AD BodyMove, unless death suppresses it; two inline + one cold1312'),
 'u3-form1-walk-negative-body':group(census,'prepared-u3:em/em32.drs',[0x3f,0x42,0xad],'negative sign turn and independent AD; two inline + one cold1312'),
 'u3-form2-walk-positive-body':group(census,'prepared-u3:em/em32.drs',[0x3a,0x3c,0xad],'positive turn and independent AD; two inline + one cold1312'),
 'krauser-type2-wait-arm':group(census,'prepared-krauser:em/em39.drs',[0xd6,0x104],'wait body and Arm_rno8 defaultArm_type0 transition; source-possible pair, arm alternatives not all coactive'),
 'krauser-mg-body-blend-gun':group(census,'prepared-krauser:em/em39.drs',[0x7f,0x81,0x2f],'positive MG body+blend+independent cEmWep gun. All preload hints remain reclaimable, not guaranteed resident'),
 'ganado12-parasite-core-tentacle':group(census,'qa-fixed:em/em12.drs',[0x27b,0x253],'live parent body adds to core idle + four tentacle instances sharing one FCV253; no fourfold payload charge'),
 'leon08-held-face':group(census,'qa-fixed:em/pl08.drs',[0x62,0x63],'face alternatives, not simultaneous; body/neck may use own player or weapon archive'),
 }
 assert result['ashley-baseline-body-look-face']['strict_v3_over_two']
 assert not result['ashley-fixed-body-look-face']['strict_v3_over_two']
 return result



def lifecycle_rules(texts):
 """Reviewed shared normal-return and door quiescence, not all-exit closure."""
 rows=[]
 def body(path,name):
  b,line=fn(texts[path],name);rows.append(dict(path=path,line=line,function=name));return b
 b=body('src/game/pl_sub.cpp','SetPlDamage')
 assert 'Pl_func_tbl[4] = func' in b and 'PlSetRoutine(4, 0, 0, 0)' in b and 'pl->dmgType = type' in b
 b=body('src/game/em_sub.cpp','EmCatchPLSet')
 assert 'pPL->subArc = em->subArc' in b and 'SetPlDamage((int) em' in b
 b=body('src/game/pl_sub.cpp','EndPlDamage')
 assert all(x in b for x in ['PlSetRoutine(0, 0, 0, 0)','pl->subArc = pl->subArc2','pl->endDamage()'])
 assert b.index('PlSetRoutine(0, 0, 0, 0)')<b.index('pl->subArc = pl->subArc2')<b.index('pl->endDamage()')
 b=body('src/game/pl_sub.cpp','EndSubDamage')
 assert 'sub->subArc = sub->subArc2' in b and 'sub->r_no_0 = 0' in b
 b=body('src/game/pl_class.cpp','cPlayer::interrupt')
 interrupt_restores_subarc='subArc' in mask(b)
 b=body('src/game/pl_class.cpp','cPlayer::endDamage')
 assert 'setFace(0)' in b
 begin=body('src/game/pl_class.cpp','cPlayer::beginEvent');end=body('src/game/pl_class.cpp','cPlayer::endEvent')
 assert 'int mode = modeReg' in begin and 'endEvent0(modeReg)' in end
 assert 'PPC_REG' in texts['include/types.h'] and 'cUnitEvent' in texts['src/game/sce_com.cpp']
 b=body('src/game/read.cpp','InitModule')
 assert b.index('re4dc_cabin_carrier_before_free')<b.index('re4dc_motion_unbind')
 assert b.index('re4dc_motion_unbind')<b.index('DLL_Unlink')<b.index('re4dc_effect_unbind')<b.index('Mem_free(m->pArc)')
 b=body('src/game/game.cpp','gameDoordemo')
 assert b.index('BitSet(pG->Stop_flg, 0xFFFFFFFF)')<b.index('pG->Disp_flg = 0xFFFFFFFF')<b.index('Dvd.ReadCancelAll()')<b.index('EmReadInit()')
 b=body('src/game/game.cpp','gameRoomMemInit')
 assert b.index('re4dc_motion_retire_all()')<b.index('MemReplaceHeap(3, 4)')
 assert b.index('re4dc_effect_retire_room()')<b.index('MemReplaceHeap(3, 4)')
 empty=[]
 for path in ['src/em10/em10_set.cpp','src/em11/em11_set.cpp','src/em12/em12_set.cpp']+[f'src/em{x}/em{x}.cpp' for x in ['2b','2c','2f','31','32','35','38','39']]:
  b=body(path,'_epilog');z=mask(b);start=z.find('{');end=z.find('}',start)
  assert not z[start+1:end].strip(),(path,'epilog changed; re-review ownership')
  empty.append(path)
 b=body('src/game/read.cpp','readEmData')
 assert b.index('re4dc_ui_bind_enemy')<b.index('re4dc_effect_bind')<b.index('re4dc_motion_bind')<b.index('m->pArc = pArc')
 early=b[:b.index('m->pArc = pArc')]
 unwind=re.findall(r'\bre4dc_(?:ui_unbind_enemy|effect_unbind|motion_unbind)\s*\(',mask(early))
 return dict(source_sites=rows,normal_return='EndPlDamage/EndSubDamage restore archive and routine; retained pMot is not reset by subArc restoration alone',
  interrupt_restores_subarc=interrupt_restores_subarc,empty_selected_epilogs=empty,
  player_event_mode_abi=dict(source='beginEvent()/endEvent() read formal-parameter-free register locals; PPC_REG is empty off PPC',status='OPEN nonzero mode behavior; separate selected object corroborates mode0',nonzero_literal_callers=[dict(path='src/st2/r220.cpp',line=162,function='r220_moveElevator',mode=2),dict(path='src/st2/r221.cpp',line=557,function='r221_moveElevator',mode=2)]),
  door_quiescence='Stop all, disable display, cancel transport, unbind modules; later retire keys before room heap replacement',
  existing_cabin_guard='RE4DC_CABIN_SOURCE InitModule gate precedes unbind; native_event_file451 checks in-flight DMA and releasing/readers/event counters for its owned carriers only',
  partial_admission=dict(order=['ui','effect','motion','publish m->pArc'],local_unwind_calls=len(unwind),
   classification='bind refusal is terminal re4dc_missing halt; early nonfatal read/resize and exhausted-slot returns require separate cleanup proof'),
  open=['fatal callback external completion','interrupt/replacement outside normal End* callbacks','non-door reset/continue/overlay path ordering','partial-admission refusal and cleanup','caller-owned attachment and emitter pointers'])



def block(s,anchor):
 """Balanced block at an exact reviewed template/macro signature."""
 start=s.index(anchor);z=mask(s);opening=z.index('{',start)+1;depth=1;end=opening
 while depth and end<len(z):
  depth+=(z[end]=='{')-(z[end]=='}');end+=1
 assert depth==0,(anchor,'unbalanced reviewed block')
 return s[start:end],s.count('\n',0,start)+1


def ownership_rules(texts,census):
 """Source contracts and named counterexamples, not a runtime lifetime proof."""
 sites=[]
 def body(path,name):
  b,line=fn(texts[path],name);sites.append(dict(path=path,line=line,function=name));return b
 shape=body('src/game/shape.cpp','ShapeMove')
 assert 'p = p->pList' in shape and shape.count('SetShape(p, p->pShape,')==1
 assert shape.index('SetOriginalShape(p)')<shape.index('SetShape(p, p->pShape,')
 neck=body('src/game/pl_class.cpp','cPlNeck::motSet')
 assert 'p->blendMot = &p->neckMot' in neck and 'MotionSetCore(p, &p->neckMot' in neck
 partner=body('src/game/pl_npc.cpp','cSubChar::neckCtrl')
 assert not calls({'src/game/pl_npc.cpp':partner},['MotionMove','MotionMoveCore','MotionSetCore'])
 begin=body('src/game/pl_npc.cpp','cSubChar::beginEvent');interrupt=body('src/game/pl_npc.cpp','cSubChar::interrupt')
 assert 'interrupt()' in begin and 'subArc' not in mask(begin+interrupt) and 'r_no_0 =' not in mask(begin+interrupt)
 manager=body('src/game/em.cpp','cEmMgr::move');move=body('src/game/em.cpp','emMove')
 assert manager.index('dieCheck()')<manager.index('if (!(pG->Stop_flg')
 assert move.index('pG->Status_flg[1] & 0x10000000')<move.index('em->move()')
 assert '!(em->be_flag & 0x800)' in move
 push=body('src/game/model.cpp','cModel::push')
 assert 'releasePartsList(0)' in push and 'releaseModelInfo()' in push
 destructor=body('src/em10/em10.cpp','cEm10::~cEm10')
 assert 'MotionSetCore(w->pCart, MOTION(w->pCart), w->mot[51]' in destructor
 destroy,line=block(texts['include/cManager.h'],'inline void cManager<T>::destroy(T* p)')
 sites.append(dict(path='include/cManager.h',line=line,function='cManager<T>::destroy'))
 assert 'case 2:' in destroy and 'p->be_flag |= 0x200' in destroy
 die,line=block(texts['include/cManager.h'],'int cManager<T>::dieCheck()')
 sites.append(dict(path='include/cManager.h',line=line,function='cManager<T>::dieCheck'))
 assert die.index('p->be_flag & 0x400')<die.index('delete p')<die.index('p->be_flag |= 0x400')
 obj12=body('src/game/obj12.cpp','cObj12::move');obj16=body('src/game/obj16.cpp','cObj16::move')
 assert obj12.index('MotionMove(this, 0)')<obj12.index('w->oya->be_flag & 0x201')
 assert obj16.index('w->target->be_flag & 0x201')<obj16.index('Obj16_R1_move_tbl')
 lost=texts['src/game/obj16.cpp'].split('#define OBJ16_LOST',1)[1].split('// Per-frame:',1)[0]
 assert lost.index('EffectEspDelete')<lost.index('ObjMgr.destroy') and 'EffectEspgenDelete' in lost and 'EffectEfmDelete' in lost
 cart=[]
 for p,t in sorted(texts.items()):
  if re.fullmatch(r'src/em[0-9a-f]{2}/em[0-9a-f]{2}_set.cpp',p):
   m=re.search(r'w->mot\[51\]\s*=\s*([^;]+);',mask(t))
   if m:
    value=t[m.start(1):m.end(1)].strip();cart.append(dict(path=p,line=t.count('\n',0,m.start())+1,value=value))
 sites.extend(dict(path=x['path'],line=x['line'],function='Work mot51 initializer')for x in cart)
 assert [x['path'].split('/')[1]for x in cart if x['value']!='0']==['em10','em12','em13','em15']
 origins=[]
 for module in ['10','11','12','13','14','15','16','17','1b','1c']:
  p=f'src/em{module}/em{module}_set.cpp';assert '#define ARC(no) PL_ARC_PTR(em->subArc, no)' in texts[p]
  origins.append(dict(path=p,owner='em->subArc',scope='literal Work initializer, not state co-use proof'))
 for module in ['2b','2c','32','38','39']:
  p=f'src/em{module}/em{module}.cpp';assert '#define ARC(no) PL_ARC_PTR(em->subArc, no)' in texts[p]
  origins.append(dict(path=p,owner='em->subArc',scope='literal Work initializer, not state co-use proof'))
 walk=body('src/em10/em10.cpp','em10SetWalkMotion');dash=body('src/em10/em10.cpp','em10SetDashMotion');wait=body('src/em10/em10.cpp','em10SetWaitMotion')
 assert all(x in walk for x in ['w->Ganado','w->Wep_type','w->pShield','em->type','w->Walk_type','em->emset_no % 5','CheckInWater','MotionSetCore(em, MOTION(em), m0, (int) m1'])
 assert 'MotionSetCore(em, MOTION(em), m0, (int) m1' in dash and 'MotionSetCore(em, MOTION(em), mot, 0' in wait
 grenade=body('src/game/emwep.cpp','cEmWep::setGrenadeThrow')
 assert all(x in grenade for x in ['w->Mot_escape = motEscape','w->motEscape2 = motEscape2','w->motBackjump = motBackjump','w->motFront = motFront','w->pEm_oya = 0'])
 # A transient subArc restoration does not change these caller-supplied headers.
 gsites=calls(texts,['setGrenadeThrow']);gcallers=[x for x in gsites if x['path']=='src/em39/em39.cpp']
 assert len(gcallers)==2 and all('ARC(0x10B)' in x['arguments']for x in gcallers)
 fatal=[]
 for path,name in [('src/em10/em10.cpp','plem10_C_SawCriHit'),('src/em35/em35.cpp','plem35_CriticalHit'),('src/em38/em38.cpp','plem38_AtkHit'),('src/em32/em32.cpp','plemDivide'),('src/em39/em39.cpp','plem39_Failure'),('src/game/emrock.cpp','plemDropDie'),('src/game/emrock.cpp','subemDropDie')]:
  b=body(path,name);assert 'subArc' in b and not re.search(r'\bEnd(?:Pl|Sub)Damage\s*\(',mask(b))
  fatal.append(dict(path=path,function=name,classification='retained borrowed header; normal End* not the termination owner'))
 death=body('src/game/game.cpp','gameDiedemo');cont=body('src/game/game.cpp','GameContinue')
 assert 'GameContinue(0)' in death and 'pG->Rno0 = 4' in cont
 reset=body('src/game/main.cpp','systemSoftReset');common=body('src/game/main.cpp','systemResetCommon')
 assert reset.index('Dvd.ReadCancelAll()')<reset.index('MemClearAllHeap()')<reset.index('systemResetCommon()')
 assert common.index('TaskAllClear()')<common.index('EmReadInit()')
 bridge=body('port/dreamcast/game/motion_bridge.cpp','re4dc_motion_free')
 assert 'OSFreeToHeap(allocation->heap,allocation)' in bridge
 free=body('src/game/read.cpp','ModuleMemFree');assert 'Heap[i].handle < 0' in free
 heap=body('src/game/main_mem.cpp','MemDestroyHeap')
 assert 're4dc_motion_retire_all' not in heap and 'OSDestroyHeap' in heap
 # Distinguish fatal admission from an ordinary failure return.
 missing=body('port/dreamcast/game/platform/mem.cpp','re4dc_missing')
 assert 'for (;;)' in missing and 'thd_sleep(1000)' in missing
 read=body('src/game/read.cpp','readEm');data=body('src/game/read.cpp','readEmData')
 no_slot=read.split('if (m == NULL)',1)[1].split('if (readEmData',1)[0]
 assert 'return NULL' in no_slot
 resize=data.split('if (len < size)',1)[1].split('} else {',1)[0]
 assert 'Mem_free(old)' in resize and 'if (pArc != old)' in resize and 'm->pArc =' not in resize
 setevd=body('src/game/event.cpp','EventMgr::SetEvd');getbin=body('src/game/event.cpp','EventMgr::GetBin');getevd=body('src/game/event.cpp','EventMgr::GetEvd')
 assert setevd.index('EvdTbl.SetDat')<setevd.index('for (i = 0; i < hdr->nBin')<setevd.index('SetBin(e->name')
 assert 'DelEvd(' not in mask(setevd) and 'DelBin(' not in mask(setevd)
 for b in [getbin,getevd]:assert 'HDReadDebugAlloc' in b and 'Debug_free(' not in mask(b)
 endevt=body('src/game/event.cpp','Event::ExeEndEvt');delevt=body('src/game/event.cpp','EventMgr::DelEvt')
 assert 'case 5:\n            MotionClear(m, 0)' in endevt
 assert endevt.index('EventAllEffDelete()')<endevt.index('ExeFunc(2, 0)')<endevt.index('pPL->move()')
 assert delevt.index('evt->ExeEndEvt(evt, 0)')<delevt.index('destroyNow(evt)')<delevt.index('DelEvd(p)')
 assert 'ClrShape(' not in mask(endevt) and 'ShapeEnd(' not in mask(endevt)
 assert 'if ((s16) pG->pl_life > 0)' in body('src/game/pl_class.cpp','cPlayer::endEvent0')
 model=body('src/game/model.cpp','cModel::modelInit')
 assert 'releaseModelInfo();' in model.split('if (initJoint(bin) != 1)',1)[1]
 leon=body('src/game/pl_leon.cpp','cPlLeon::setModel')
 assert leon.count('setModel() failed.')>=5 and leon.count('addModel(info)')>=5
 return dict(source_sites=sites,
  multiplicity=dict(normal_shape='one pShape curve per active info through ShapeMove; info chain may have multiple independent curves',leon_neck='neckMot is blendMot, not an additional third body channel',partner_neck='procedural matrices; subBackMot is the blend work; face remains independent',event_shape='ExePacket_Shp resolves ModTbl target; type2 info and distinct model targets require selected event ownership'),
  cart_selector_rows=cart,cart_selected_em12=group(census,'qa-fixed:em/em12.drs',[0x25d,0x25e],'independent cart state alternatives; not a simultaneous pair'),
  selector_contracts=dict(literal_work_archive_origins=origins,ganado='own subArc; type/Ganado/weapon/shield/Walk_type and emset/water select ONE body FCV plus its SEQ; not all alternatives at once',grenade=dict(owner='Krauser ARC10b/10c/10d/111 supplied through stored fields; weapon subArc is not their owner',callers=gcallers)),
  fatal_retained_headers=fatal,
  partial_admission=dict(bind_refusal='terminal re4dc_missing halt in selected implementation; local returns are not a recoverable gameplay retry',module_slot_exhaustion_restores_display='pG->Disp_flg = flags' in no_slot,resize_relocation='pre-bind nonfatal return if replacement differs; new owner is not published, cleanup OPEN',event_partial_registration='SetEvd publishes header before all bins; no local rollback; subsequent ChkDat success can mask prior partial bin failure',event_fallback_allocation='GetBin/GetEvd allocate before registration; local registration failure does not free dat; actual bridge/allocator failure OPEN',model='modelInit releases base info if joint init fails; cPlLeon::setModel can return after prior infos added, caller transactional recovery OPEN'),
  lifetime_edges=[
   dict(id='A03-OBJ12',owner='parent source archive retained by obj12 motion header',termination='parent guard follows MotionMove; detached cart can remain independent',status='OPEN stop-before-free',next_case='mark parent, retain child Motion, retire donor before next child tick; prove child stop or explicit owner retention'),
   dict(id='A03-OBJ16',owner='target/body borrowed model + own stored pMotion',termination='dead target/body guard precedes move and deletes owner emitters; does not guard render-before-tick or address reuse',status='source local guard proved; generation boundary OPEN',next_case='destroy/reuse target between child update and model trans; verify emitter/shape/model readers drain'),
   dict(id='A07-FATAL',owner='dmgType donor + retained pMot, independent catch props',termination='death demo retains archive; Continue selects door quiescence; interrupt alone does not restore callback',status='source normal Continue contract; intra-room/forced interrupt OPEN',next_case='abort a retained fatal/QTE callback through each non-door module retirement; require callback and catch prop quiescence'),
   dict(id='A08-RESET',owner='native slot/slab saved SDK heap handle',termination='soft reset destroys heaps before module unbind; ModuleMemFree source guard does not wrap native motion free',status='OPEN native post-destroy free risk',next_case='loaded MTC reset with existing native allocator/handle audit; compare before-clear retirement versus later unbind, no guest claimed'),
   dict(id='A08-INTRAROOM',owner='em15 bell/em3,4,13 cabin/em11 cannon plus borrowers/children',termination='bell/cabin sleep2 before InitModule; cannon frees before next yield; event pause exempts be_flag800',status='OPEN per-caller deferred destruction and no-suspend proof',next_case='prove two actual manager dieCheck passes, slow-motion skip and child/borrower termination; cannon has no drain before free'),
   dict(id='A08-SLOTS',owner='saved pG->Disp_flg in readEm',termination='read failure restores saved flags; no-slot early return currently does not',status='source-visible failure-path defect',next_case='exhaust four module slots and check original display word restored on returned NULL'),
   dict(id='A08-EVENT-SHAPE',owner='external type5 model info pShape from named EVD bin',termination='ExeEndEvt clears body motion but not ShapeEnd/ClrShape; normal event data destroy follows',status='OPEN selected packet/owner lifetime',next_case='a type5 model with event Shp plus live frame after carrier deletion; prove shape stop or retain carrier; also dead-player endEvent0 skips routine reset'),
   dict(id='A08-EVDBINS',owner='EvdTbl header + BinTbl borrowed entries/refcounts',termination='normal Event destroy before DelEvd; partial SetBin refusal leaves header registered',status='source-visible transactional admission defect',next_case='fail kth BinTbl registration then retry same EVD name; require complete bins or rollback without releasing live refs')])



def indirect_owner_rules(texts,census):
 sites=[]
 def body(path,name):
  b,line=fn(texts[path],name);sites.append(dict(path=path,line=line,function=name));return b
 setter=body('src/game/obj16.cpp','cObj16::setMotData')
 assert all(f'w->mot[{i}] = m{i};' in setter for i in range(11))
 assert 'MotionSetCore(this, &pMotion, m2' in setter and 'MotionSetCore(this, &pMotion, m0' in setter
 damage=body('src/game/obj16.cpp','cObj16::setPlDmgMot');assert 'w->Mot_pl_dm = mot' in damage and 'w->Seq_pl_dm = a' in damage
 bite=body('src/game/obj16.cpp','plemDmMStar')
 assert 'w->Mot_pl_dm, w->Seq_pl_dm' in bite and 'EndPlDamage()' in bite
 assert '->subArc =' not in mask(bite) # subArc-assignment census alone misses this borrower
 actual={n:[x for x in calls(texts,[n])if x['path'].startswith('src/') and x['path']!='src/game/obj16.cpp']for n in ['setMotData','setPlDmgMot']}
 assert len(actual['setMotData'])==6 and len(actual['setPlDmgMot'])==3
 assert {x['path']for x in actual['setMotData']}=={'src/em10/em10.cpp','src/em30/em30.cpp','src/em3c/em3c.cpp'}
 for module in ['30','3c']:
  assert '#define ARC(no) PL_ARC_PTR(em->subArc, no)' in texts[f'src/em{module}/em{module}.cpp']
 boat=[]
 for module in ['0e','0f']:
  path=f'src/pl{module}/pl{module}.cpp';move=body(path,'PlBoatMove')
  assert move.index('pl->subArc = pl->m_pBoat->subArc')<move.index('plboat_R2_move_tbl[pl->r_no_2](pl)')<move.index('pl->subArc = pl->subArc2')
  for name in ['plboatBlendMotSet','subBlendMotSet']+(['pl0eBlendMotSet']if module=='0e'else[]):
   b=body(path,name);assert b.count('MotionSetCore(')==2 and 'm = m1' in b and 'm = m2' in b
  label=f'qa-fixed:em/pl{module}.drs';archive=census['archives'][label];assert archive['mtc'] is None
  boat.append(dict(path=path,archive=label,native_sha256=archive['native_sha256'],native_bytes=archive['native_bytes'],motion_policy='selected prepared archive has no MTC; reviewed FCVs below are inline, not motion-cache entries',dispatch_states=7 if module=='0e'else 19,lifetime='m_pBoat null check only; no alive/generation check; normal door/Continue retains source contract, mid-ride donor destroy OPEN'))
 ski=body('src/pl0e/pl0e.cpp','subBoatRun');ride=body('src/pl0e/pl0e.cpp','plboat_R2_Move')
 assert 'SUBARC(0x25), SUBARC(0x27), SUBARC(0x26)' in ski and 'PLARC(0x16), PLARC(0x18), PLARC(0x17)' in ride
 leave=body('src/pl0f/pl0f.cpp','plboat_R2_Getoff');assert 'EndPlDamage()' in leave
 leave_sub=body('src/pl0f/pl0f.cpp','subBoatGetoff');assert 'EndSubDamage()' in leave_sub
 groups={
  'jet-ski-positive-lean-six-body-streams':group(census,'qa-fixed:em/pl0e.drs',[0x8,0x9,0x16,0x17,0x25,0x26],'ski body+lean, rider body+lean, partner body+lean; positive sign example'),
  'del-lago-boat-rider-positive-lean':group(census,'qa-fixed:em/pl0f.drs',[0x9,0xa],'player boat body+one lean; boss and boat own body remain separate'),
 }
 assert all(g['distinct_cached']==0 and all(x['state']=='inline-resident'for x in g['records'])for g in groups.values())
 return dict(source_sites=sites,head_setter_callers=actual,head_contract='11 alternatives feed one child body work; independent parasite/tentacle/body/player demand still counts; duplicate setters do not create another stream',bite_contract='dmgType obj16 points to Mot_pl_dm from em10 own ARC17a/SEQ17b, legacy em30 ARC20, or em3c ARC61/SEQ62; no subArc store in callback; EndPlDamage is normal exit',boat_dispatch=boat,reviewed_groups=groups,remaining=['raw dmgType donor retirement during obj16 bite before EndPlDamage','jet-ski partner callback/ride stopped before exceptional donor unload','actual loaded boat variant and render/hand/texture/audio reads are runtime gates, not inferred from no MTC'])

def run(repo,ref,census_path):
 raw=census_path.read_bytes();assert digest(raw)==CENSUS_SHA,'sealed metadata changed'
 census=json.loads(raw)
 paths=subprocess.check_output(['git','-C',str(repo),'ls-tree','-r','--name-only',ref,'src','include','port/dreamcast/game']).decode().splitlines()
 texts={p:subprocess.check_output(['git','-C',str(repo),'show',ref+':'+p]).decode(errors='replace')
        for p in paths if p.endswith(('.cpp','.c','.h','.hpp','.inc','.S','.s')) and not p.startswith('src/lib/')}
 sites=calls(texts);ev=check_evaluators(texts);bl=check_blends(texts);groups=reviewed_groups(census,texts);life=lifecycle_rules(texts);owners=ownership_rules(texts,census);indirect=indirect_owner_rules(texts,census)
 lifecycle_paths={x['path']for x in life['source_sites']+owners['source_sites']+indirect['source_sites']}|{'include/types.h','src/game/sce_com.cpp','port/dreamcast/game/platform/native_event_file.cpp'}
 pins=[dict(path=p,sha256=digest(t.encode()))for p,t in texts.items() if p in lifecycle_paths or any(c['path']==p for c in sites)]
 # Discover literal asm aliases independently of masked string contents.
 aliases=[]
 for p,t in texts.items():
  for m in re.finditer(r'\b(\w+)\s*\([^;{}]*\)\s*asm\("([^"\n]+)"\)',mask_comments(t)):
   if 'Motion' in m[2] or 'MotSet' in m[2]:aliases.append(dict(path=p,line=t.count('\n',0,m.start())+1,name=m[1],target=m[2]))
 borrowed=[]
 for p,t in texts.items():
  if not p.startswith('src/'):continue
  for m in re.finditer(r'\b(\w+)->subArc\s*=\s*([^;\n]+);',mask(t)):
   borrowed.append(dict(path=p,line=t.count('\n',0,m.start())+1,target=m[1],source=t[m.start(2):m.end(2)].strip(),
                        proof='assignment inventory only; exceptional exits/retirement OPEN'))
 details=dict(source_ref=ref,source_pins=pins,occurrences=sites,asm_aliases=aliases,borrowed_assignments=borrowed)
 out=dict(schema=1,scope='A01–A05/A07/A08 source checkpoint; no whole-program CFG or complete audit claim',
  source_ref=subprocess.check_output(['git','-C',str(repo),'rev-parse',ref]).decode().strip(),
  census_sha256=CENSUS_SHA,qa_archive_inventory_count=sum(k.startswith('qa-fixed:')for k in census['archives']),
  complete_metadata_inventory_count=len(census['archives']),reused_inventory=True,
  evaluator_rules=ev,blend_helper_rules=bl,reviewed_groups=groups,lifecycle_rules=life,ownership_followup=owners,indirect_owner_followup=indirect,
  lexical_occurrences_by_symbol=dict(sorted(Counter(c['symbol']for c in sites).items())),
  lexical_occurrences_by_file=dict(sorted(Counter(c['path']for c in sites).items())),
  asm_aliases=aliases,source_pins=pins,subarc_assignment_occurrences=len(borrowed),
  evidence_levels=dict(source='reviewed rules plus lexical inventory; dynamic ownership edges remain named OPEN',host='Python source-rule regression only; no C++ target execution by this tool',runtime='no new build/guest; H050/H055 and later handbacks retain their independent scopes'),
  open_edges=['A01 indirect or raw-pointer mutation and selected linkage beyond lexical scope','A02 all dynamic blend-owner setters and cross-state source assignments','A03 per-active-info shape population and all attachment setter generations','A04 module Work variants, variable indexes and event payload identities','A05 absent selected FCV records are not inferred resident; require actual binding/variant','A07 exceptional grab/QTE/death exits and donor replacement before borrower stop'])
 return out,details


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repo',type=Path,required=True);p.add_argument('--source-ref',default='c7e0358a');p.add_argument('--census',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--details',type=Path);p.add_argument('--target-object',type=Path);a=p.parse_args()
 out,details=run(a.repo,a.source_ref,a.census)
 if a.target_object:
  target_sha=digest(a.target_object.read_bytes());assert target_sha=='d4cc10f6bdb0bc00f5f2f0999db75d5144d388f0933d00d95092609ed784c887','separate root target object identity changed'
  out['selected_target_corroboration']=dict(source='root c7 full control4 pl_class.o; hash read-only verified here',sha256=target_sha,reported_disassembly='beginEvent has mode0 routine5/BlendOff/setFootwork path; endEvent passes0 to endEvent0; incoming nonzero mode not preserved',proof='root-provided disassembly + artifact hash, not a new target compile or gameplay test')
 if a.details:
  a.details.write_text(json.dumps(details,indent=2)+'\n');out['private_details_sha256']=digest(a.details.read_bytes())
 a.output.write_text(json.dumps(out,indent=2)+'\n')
 print(json.dumps(dict(qa_archives=out['qa_archive_inventory_count'],hooks=len(out['evaluator_rules']),blend_helpers=len(out['blend_helper_rules']),groups=len(out['reviewed_groups']),occurrences=len(details['occurrences']),pins=len(out['source_pins']),borrowed=len(details['borrowed_assignments'])),indent=2))
if __name__=='__main__':main()
