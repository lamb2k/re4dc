#!/usr/bin/env python3
"""Continue the sealed animation census with reviewed shared lifecycle rules.

No ISO rescan, asset conversion, room capture or CFG completeness claim. The
census contains metadata only; exact selected bytes were verified by H050.
"""
import argparse,hashlib,json,re,subprocess
from pathlib import Path
CENSUS_SHA='3adb52b984ed441fe52d58b704d1abc392c11afc39e3ae24a78f551ba756ce60'

def digest(data):return hashlib.sha256(data).hexdigest()
def source(repo,ref,path):return subprocess.check_output(['git','-C',str(repo),'show',ref+':'+path]).decode()
def function(text,name):
    # Reviewed definitions only. Balance braces with comments/strings masked.
    masked=re.sub(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'',lambda m:re.sub(r'[^\n]',' ',m[0]),text,flags=re.S)
    pat=r'^[^\n;{}]*\b'+re.escape(name)+r'\s*\([^;{}]*\)\s*(?:const\s*)?\{'
    matches=list(re.finditer(pat,masked,re.M));assert len(matches)==1,(name,len(matches))
    start=matches[0].start();at=matches[0].end();depth=1
    while depth:
        if masked[at]=='{':depth+=1
        elif masked[at]=='}':depth-=1
        at+=1
    return text[start:at],text.count('\n',0,start)+1

def reviewed_group(census,label,arcs):
    archive=census['archives'][label];clips=[]
    for arc in arcs:
        assert str(arc) in archive['clips'],(label,arc)
        clips.append(archive['clips'][str(arc)])
    cold=[r for r in clips if r['state']=='cached-cold'];mtc=archive['mtc']
    return dict(archive=label,arcs=[hex(x)for x in arcs],clips=clips,cold_count=len(cold),cold_bytes=sum(r['bytes']for r in cold),strict_two_slot_fits=len(cold)<=2 if mtc and mtc['version']==3 else None,
        qualification='Reviewed local source state only; no all-state/runtime closure')

def run(repo,census_path,ref):
    raw=census_path.read_bytes();assert digest(raw)==CENSUS_SHA,'sealed H050 census changed'
    census=json.loads(raw);paths=[
      'src/game/motion.cpp','src/game/shape.cpp','src/game/cam_motion.cpp','src/game/pl_leon.cpp','src/game/pl_class.cpp','src/game/pl_npc.cpp','src/game/emwep.cpp',
      'src/em10/em10.cpp','src/em2b/em2b.cpp','src/em2c/em2c.cpp','src/em31/em31.cpp','src/em32/em32.cpp','src/em35/em35.cpp','src/em38/em38.cpp','src/em39/em39.cpp',
      'src/game/read.cpp','src/game/dvd.cpp','src/game/snd.cpp','port/dreamcast/game/motion_bridge.cpp','port/dreamcast/game/platform/native_movie.cpp','port/dreamcast/game/sscrn_bridge.cpp',
      'port/dreamcast/game/platform/native_motion.cpp','port/dreamcast/game/platform/include/native_motion.h','port/dreamcast/game/platform/native_effect.cpp','port/dreamcast/game/platform/native_ui.cpp','port/dreamcast/game/platform/audio_aica.cpp',
      'port/dreamcast/game/coarse_ganado_lod.inc','port/dreamcast/game/coarse_actor_leon_hands.inc','port/dreamcast/game/coarse_actor_pl08_pack.inc','port/dreamcast/game/ui_bridge.cpp']
    paths+=['src/em'+x+'/em'+x+'_set.cpp'for x in ['10','11','12','13','14','15','16','17','1b','1c']]
    texts={p:source(repo,ref,p)for p in paths};pins=[dict(path=p,sha256=digest(t.encode()))for p,t in texts.items()]
    def fn(path,name):return function(texts[path],name)[0]
    hooks=[]
    for path in ['src/game/motion.cpp','src/game/shape.cpp','src/game/cam_motion.cpp']:
        hooks.extend(dict(path=path,line=texts[path].count('\n',0,m.start())+1)for m in re.finditer(r'Re4dcMotionLease keys\(',texts[path]))
    assert len(hooks)==7
    assert 'PSMTXCopy(p->l_mat, p->prevMat)' in fn('src/game/motion.cpp','MotionSetCore')
    assert '0x20000000' in fn('src/game/motion.cpp','MotionSetCore') and 'MOTION(m)->blend = 0' in fn('src/game/motion.cpp','MotionSetCore')
    assert 'PL_ARC(0x93)' in fn('src/em35/em35.cpp','plem35_BearHug') and 'PL_ARC(0x94)' in fn('src/em35/em35.cpp','plem35_BearHug')
    assert 'pl->subArc = PL_EM_G->subArc' in fn('src/em35/em35.cpp','plem35_BearHug') and 'pl->subArc = pl->subArc2' in fn('src/em35/em35.cpp','plem35_BearHug')
    assert 'ARC(0x36)' in fn('src/em35/em35.cpp','em35_R1_BearHug') and 'ARC(0x38)' in fn('src/em35/em35.cpp','em35_R1_BearHug')
    assert 'PL_ARC_PTR(pG->pPlayer, 0x62)' in fn('src/game/pl_leon.cpp','cPlLeon::setFace')
    assert 'plBlendMotSet(pl, PL_ARC(0xBA), PL_ARC(0xBD)' in fn('src/em2b/em2b.cpp','plem2b_Strangle')
    assert 'ARC(0x39)' in fn('src/em2b/em2b.cpp','em2b_R1_Strangle')
    groups={
      'mendez-bearhug':reviewed_group(census,'qa-fixed:em/em35.drs',[0x36,0x93]),
      'mendez-release':reviewed_group(census,'qa-fixed:em/em35.drs',[0x38,0x94]),
      'gigante-strangle-body-player-blend':reviewed_group(census,'qa-fixed:em/em2b.drs',[0x39,0xba,0xbd]),
      'leon-face-pain':reviewed_group(census,'qa-fixed:em/pl08.drs',[0x62]),
    }
    assert groups['mendez-bearhug']['strict_two_slot_fits'] and groups['mendez-release']['strict_two_slot_fits']
    assert all(r['state']=='inline-resident'for r in groups['gigante-strangle-body-player-blend']['clips'])
    sites=[]
    for path,needle in [
      ('src/game/motion.cpp','void MotionSetCore('),('src/game/motion.cpp','u16 MotionMove('),
      ('src/game/shape.cpp','void CalculateShape_new('),('src/game/cam_motion.cpp','void CameraMotion::move()'),
      ('src/game/read.cpp','void InitModule('),('src/game/read.cpp','int readEmData('),('src/game/read.cpp','void* EmReadSearch('),
      ('src/game/snd.cpp','u32 SndCall('),('src/game/snd.cpp','int SndEmDataReadCheck('),('src/game/dvd.cpp','r = SndEmDataReadCheck('),
      ('port/dreamcast/game/platform/native_movie.cpp','int finish('),('port/dreamcast/game/platform/native_movie.cpp','bool open('),
      ('port/dreamcast/game/sscrn_bridge.cpp','const unsigned motions = re4dc_motion_forget_dead_heaps();'),
      ('port/dreamcast/game/platform/native_effect.cpp','static int bind_archive('),('port/dreamcast/game/platform/native_ui.cpp','Entry* load(const Re4dcUiImage&'),
      ('port/dreamcast/game/platform/audio_aica.cpp','bool str_index_load()'),('port/dreamcast/game/ui_bridge.cpp','unsigned re4dc_fixture_source_frame()')]:
        at=texts[path].find(needle);assert at>=0,(path,needle);sites.append(dict(path=path,line=texts[path].count('\n',0,at)+1,anchor=needle))
    aliases=[]
    for path,text in texts.items():
        if not path.startswith('src/em'):continue
        for m in re.finditer(r'w->(\w+(?:\[\s*(?:0x[0-9a-fA-F]+|\d+)\s*\])?)\s*=\s*(?:\(int\)\s*)?ARC\(\s*(0x[0-9a-fA-F]+|\d+)\s*\)',text):
            aliases.append(dict(path=path,line=text.count('\n',0,m.start())+1,field=m[1],arc=hex(int(m[2],0)),qualification='initializer/selector alternative, not a concurrent group'))
    borrowed=[]
    for path,text in texts.items():
        if not path.startswith('src/'):continue
        for m in re.finditer(r'pl->subArc\s*=\s*([^;\n]+);',text):
            borrowed.append(dict(path=path,line=text.count('\n',0,m.start())+1,source=m[1].strip(),restores_default=m[1].strip()=='pl->subArc2'))
    return dict(schema=1,scope='shared mechanisms + explicitly reviewed state/owner rules; no whole CFG/caller closure',source_ref=ref,census_sha256=CENSUS_SHA,archive_inventory_reused=True,qa_selected_archive_count=sum(k.startswith('qa-fixed:')for k in census['archives']),source_pins=pins,source_sites=sites,registered_evaluator_hooks=hooks,reviewed_local_coactivity=groups,work_alias_assignments=aliases,borrowed_archive_assignments=borrowed,
      unresolved=['em10 evtMot injection by room/event setters; setter arguments and archive owner must be followed, not assumed em12','em10 module-specific mot/model alternatives plus independently reacting active actors; source dispatch group contract incomplete','ElGigante tree/parasite/twin states beyond reviewed walk/strangle; later em2b same policy is not wholefight closure','Mendez upper-body/beam/damage/borrowed callbacks beyond reviewed spear/bearhug/release; v3 invariant remains unproven globally','U3/Krauser/Saddler phase tables, attached objects and borrowed player sets beyond reviewed helper arity/triplet','shape has up to five registered channels; held faces still evaluate; no global per-owner shape-channel concurrency contract','camera/event FCV archive selection beyond the shared leased evaluator sites','movie pressure evictions have no bounded source-used generation-safe resume journal; normal menu preserves room cache and should not be blindly replayed'],
      repairs=dict(accounting='c5fbf44d default off; target/host qualified, QA integration owned by root/Claude',reserved_capacity='54be5527 default off; v2 only, no growth/moves, strictv3 unchanged; QA/Claude functional gates pending',motion_resume='owned424B journal component with host tests; no runtime hooks/native edit while Claude MOTION21 owns integration',weapon='root owns read.cpp/weapon archive and hand followup'))

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repo',type=Path,required=True);p.add_argument('--census',type=Path,required=True);p.add_argument('--source-ref',default='9eb83d59');p.add_argument('--output',type=Path,required=True);p.add_argument('--details',type=Path);a=p.parse_args();r=run(a.repo,a.census,a.source_ref)
    if a.details:a.details.write_text(json.dumps(r,indent=2)+'\n')
    summary={k:v for k,v in r.items()if k not in ['work_alias_assignments','borrowed_archive_assignments']}
    summary['work_alias_count']=len(r['work_alias_assignments']);summary['borrowed_assignment_count']=len(r['borrowed_archive_assignments'])
    summary['details_qualification']='Initializer alternatives are not coactivity/CFG closure; full metadata can be emitted privately with --details'
    if a.details:summary['details_sha256']=digest(a.details.read_bytes())
    a.output.write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(dict(source_pins=len(r['source_pins']),hooks=len(r['registered_evaluator_hooks']),aliases=len(r['work_alias_assignments']),borrowed_assignments=len(r['borrowed_archive_assignments']),groups=len(r['reviewed_local_coactivity'])),indent=2))
if __name__=='__main__':main()
