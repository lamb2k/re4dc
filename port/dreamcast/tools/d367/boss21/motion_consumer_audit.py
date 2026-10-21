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
 defs=definitions(s);hits=[i for i,x in enumerate(defs) if x[2]==name]
 assert len(hits)==1,(name,len(hits))
 i=hits[0];start=defs[i][0];end=defs[i+1][0] if i+1<len(defs) else len(s)
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


def run(repo,ref,census_path):
 raw=census_path.read_bytes();assert digest(raw)==CENSUS_SHA,'sealed metadata changed'
 census=json.loads(raw)
 paths=subprocess.check_output(['git','-C',str(repo),'ls-tree','-r','--name-only',ref,'src','include','port/dreamcast/game']).decode().splitlines()
 texts={p:subprocess.check_output(['git','-C',str(repo),'show',ref+':'+p]).decode(errors='replace')
        for p in paths if p.endswith(('.cpp','.c','.h','.hpp','.inc','.S','.s')) and not p.startswith('src/lib/')}
 sites=calls(texts);ev=check_evaluators(texts);bl=check_blends(texts);groups=reviewed_groups(census,texts)
 pins=[dict(path=p,sha256=digest(t.encode()))for p,t in texts.items() if any(c['path']==p for c in sites)]
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
 out=dict(schema=1,scope='A01–A05/A07 source checkpoint; no whole-program CFG or complete audit claim',
  source_ref=subprocess.check_output(['git','-C',str(repo),'rev-parse',ref]).decode().strip(),
  census_sha256=CENSUS_SHA,qa_archive_inventory_count=sum(k.startswith('qa-fixed:')for k in census['archives']),
  complete_metadata_inventory_count=len(census['archives']),reused_inventory=True,
  evaluator_rules=ev,blend_helper_rules=bl,reviewed_groups=groups,
  lexical_occurrences_by_symbol=dict(sorted(Counter(c['symbol']for c in sites).items())),
  lexical_occurrences_by_file=dict(sorted(Counter(c['path']for c in sites).items())),
  asm_aliases=aliases,source_pins=pins,subarc_assignment_occurrences=len(borrowed),
  evidence_levels=dict(source='reviewed rules plus lexical inventory; dynamic ownership edges remain named OPEN',host='Python source-rule regression only; no C++ target execution by this tool',runtime='no new build/guest; H050/H055 and later handbacks retain their independent scopes'),
  open_edges=['A01 indirect or raw-pointer mutation and selected linkage beyond lexical scope','A02 all dynamic blend-owner setters and cross-state source assignments','A03 per-active-info shape population and all attachment setter generations','A04 module Work variants, variable indexes and event payload identities','A05 absent selected FCV records are not inferred resident; require actual binding/variant','A07 exceptional grab/QTE/death exits and donor replacement before borrower stop'])
 return out,details


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repo',type=Path,required=True);p.add_argument('--source-ref',default='c7e0358a');p.add_argument('--census',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--details',type=Path);a=p.parse_args()
 out,details=run(a.repo,a.source_ref,a.census)
 if a.details:
  a.details.write_text(json.dumps(details,indent=2)+'\n');out['private_details_sha256']=digest(a.details.read_bytes())
 a.output.write_text(json.dumps(out,indent=2)+'\n')
 print(json.dumps(dict(qa_archives=out['qa_archive_inventory_count'],hooks=len(out['evaluator_rules']),blend_helpers=len(out['blend_helper_rules']),groups=len(out['reviewed_groups']),occurrences=len(details['occurrences']),pins=len(out['source_pins']),borrowed=len(details['borrowed_assignments'])),indent=2))
if __name__=='__main__':main()
