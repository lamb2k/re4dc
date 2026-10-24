"""QA postbuild: actual568/449 graph and same-QA OFF identity, no SDK execution."""
from pathlib import Path
import argparse,hashlib,json,re,shlex,struct,resource,signal,sys,types
import common as c
SUPPORT=c.HERE/'elf_reader.py'
ELF_SOURCE_SHA256='a5099263389d5ac7555118fdad007af3ed2381a7647fa1616cb9eb1438e871e4'
_elf_source=SUPPORT.read_bytes();c.require(hashlib.sha256(_elf_source).hexdigest()==ELF_SOURCE_SHA256,'ELF helper source changed')
e=types.ModuleType('normal_elf');e.__file__=str(SUPPORT);sys.modules['normal_elf']=e
exec(compile(_elf_source,str(SUPPORT),'exec',dont_inherit=True),e.__dict__)
HELPERS={'gc_asset_gate','gc_asset_disc','gc_asset_members','gc_asset_payloads','gc_asset_audio','gc_asset_motion_unknown'}

def overlays(names,plan):c.require(set(names)=={n.lower()+'.ovl' for n in plan['overlay_order']},'Missing/extra overlays')
def graph(log,plan,arm):
 lines=log.splitlines();links=[x for x in lines if 'bash tools/link.sh ' in x];c.require(len(links)==1,'Exactly one normal link graph required')
 av=shlex.split(links[0]);objects=[x for x in av if x.endswith('.o')]
 c.require(len(objects)==plan['reference']['object_count']==449 and len(objects)==len(set(objects)),'449 unique QA objects required')
 c.require(not any(Path(x).stem in HELPERS for x in objects),'GC helper linked')
 base=plan['reference']['object_order'];norm=lambda x:x.rsplit('/obj/',1)[-1]
 c.require([norm(x) for x in objects]==[norm(x) for x in base],'Normal ordered graph changed')
 for x in objects:c.contained(Path(plan['root'])/arm/'out/obj',x)
 order=[x.split('gen_overlay: .ovl_',1)[1].split()[0] for x in lines if 'gen_overlay: .ovl_' in x]
 c.require(order==plan['overlay_order'],'Overlay pipeline order')
 compiled=[shlex.split(x) for x in lines if ' -c ' in x and ' -o ' in x]
 c.require(bool(compiled),'Compile log missing')
 for avc in compiled:
  flags=[x for x in avc if x.startswith('-DRE4DC_')]
  c.require(not any(x.startswith(('-DRE4DC_GC_ASSET','-DRE4DC_PS2_PVS_BATCH_COMPOSE','-DRE4DC_PS2_PVS_EFFECTIVE0_SOURCES')) and x.split('=',1)[-1]!='0' for x in flags),'Unexpected experimental macro')
 # Compare every actual normal compilation with the pinned568-command baseline.
 baseline_log=(Path(plan['reference']['root'])/'off/build.log').read_text()
 baseline=[shlex.split(x) for x in baseline_log.splitlines() if ' -c ' in x and ' -o ' in x]
 def key(av):return av[av.index('-o')+1].rsplit('/obj/',1)[-1]
 old={key(av):av for av in baseline};now={key(av):av for av in compiled}
 c.require(len(old)==len(baseline)==568 and len(now)==len(compiled) and set(old)==set(now),'Actual compile graph differs')
 current_prefix=str(Path(plan['root'])/arm);old_prefix=str(Path(plan['reference']['root'])/'off')
 for k,avc in now.items():
  actual=[x.replace(current_prefix,'<ARM>') for x in avc if not x.startswith('-DRE4DC_RAIN_R10C')]
  expected_argv=[x.replace(old_prefix,'<ARM>') for x in old[k]]
  c.require(actual==expected_argv,'Actual compiler argv changed '+k)
 rain=[(a[a.index('-c')+1],[x for x in a if x.startswith('-DRE4DC_RAIN_R10C')]) for a in compiled]
 expected={} if arm=='off' else {'../../../src/game/filter06.cpp':['-DRE4DC_RAIN_R10C_DC=1','-DRE4DC_RAIN_R10C_DIAG=1'],'../../../src/game/espgen44.cpp':['-DRE4DC_RAIN_R10C_DIAG=1']}
 actual={name:sorted(flags) for name,flags in rain if flags}
 c.require(actual=={n:sorted(v) for n,v in expected.items()},'Rain macros differ from exact arm')
 return dict(argv=av,objects=objects,compile_commands_matched=568,helper_compiles=[a for a in compiled if Path(a[a.index('-c')+1]).stem in HELPERS])

def dependencies(plan,arm):
 root=Path(plan['root'])/arm;source=root/'source';out=root/'out';cwd=source/'port/dreamcast/game';seen={};files={}
 for d in sorted(out.rglob('*.d')):
  c.contained(out,d);files[str(d)]=c.identity(d);line=d.read_text().replace('\\\n',' ').splitlines()[0];_,items=line.split(':',1)
  for token in shlex.split(items):
   p=Path(token);p=(p if p.is_absolute() else cwd/p).resolve();name=str(p)
   if name in seen:continue
   if p.is_relative_to(source):
    rel=str(p.relative_to(source))
    if rel in plan['source_manifest']:c.verify({name:plan['source_manifest'][rel]});kind='exact-source'
    else:
     c.require(rel.startswith('port/dreamcast/game/platform/sdk/gen/') and p.suffix=='.c','Unqualified generated source '+name)
     original=source/'src/lib'/p.name;driver=source/'port/dreamcast/game/platform/sdk/strip_cw_asm.py'
     c.require(original.is_file() and driver.is_file(),'Unbound ephemeral SDK source')
     c.verify({str(original):plan['source_manifest'][str(original.relative_to(source))],str(driver):plan['source_manifest'][str(driver.relative_to(source))]})
     kind='ephemeral-SDK-generated-C';seen[name]=dict(kind=kind,present=p.exists(),original=c.identity(original),driver=c.identity(driver));continue
   elif p.is_relative_to(out):c.require(p.is_file(),'Missing generated dependency');kind='owned-generated'
   else:c.require(name in plan['input_pins'],'New external dependency refused '+name);c.verify({name:plan['input_pins'][name]});kind='exact-external'
   seen[name]=dict(kind=kind,identity=c.identity(p))
 reference_out=Path(plan['reference']['root'])/'off/out'
 c.require({str(Path(x).relative_to(out)) for x in files}=={str(x.relative_to(reference_out)) for x in reference_out.rglob('*.d')},'Actual QA dependency file inventory differs')
 return dict(files=files,dependencies=seen)

def fullsymbols(path):
 b=Path(path).read_bytes();h=struct.unpack_from('<16sHHIIIIIHHHHHH',b);ss=[struct.unpack_from('<IIIIIIIIII',b,h[6]+i*h[11]) for i in range(h[12])];result=[]
 for section in ss:
  if section[1]!=2:continue
  strings=ss[section[6]];strings=b[strings[4]:strings[4]+strings[5]]
  for at in range(section[4],section[4]+section[5],16):
   ni,v,size,info,other,index=struct.unpack_from('<IIIBBH',b,at);name=strings[ni:].split(b'\0',1)[0].decode()
   if name:result.append(dict(name=name,value=v,bytes=size,info=info,other=other,index=index))
 return result

def helper_identity(path):
 x=e.elf(path)
 c.require(x['type']==1 and x['allocated_bytes']==0 and x['meaningful_symbol_rows']==[],'Default-off helper nonempty')
 return dict(identity=c.identity(path),allocated_bytes=0,symbols=[])

def raw_identity(parsed,raw):
 c.require(parsed['raw_from_ELF']['sha256']==c.sha(raw) and parsed['raw_from_ELF']['bytes']==Path(raw).stat().st_size,'Exact objcopy raw mismatch')

def validate_rain(rain,sections,on):
 if not on:c.require(not rain,'OFF record retained');return
 c.require(len(rain)==1,'One rain record required');v=rain[0]
 c.require(v['info']==0x11 and v['other']==0 and v['bytes']==128 and v['value']%32==0 and 0x8c000000<=v['value'] and v['value']+128<=0x8d000000,'Rain absolute P1/extent/alignment')
 c.require(any(s['name']=='.bss' and s['addr']<=v['value'] and v['value']+128<=s['addr']+s['bytes'] for s in sections),'Rain record outside BSS')

def read_arm(plan,arm):
 root=Path(plan['root'])/arm;out=root/'out';scratch=root/'source/port/dreamcast/game/obj'
 c.require(json.loads((root/'command.json').read_text())==plan['commands'][arm],'Actual command changed')
 log=(root/'build.log').read_text();g=graph(log,plan,arm)
 c.require((scratch/'missing.txt').is_file() and (scratch/'missing.txt').stat().st_size==0,'Missing provider inventory')
 for n in ['aliases.ld','missing.cpp']:
  text=(scratch/n).read_text().lower();c.require(not any(t in text for t in ['gcasset','gc_asset','motion_unknown','rain_r10c']),'Diagnostic alias/stub')
 c.verify({str(scratch/n):c.identity(Path(plan['reference']['root'])/'off/source/port/dreamcast/game/obj'/n) for n in ['missing.txt','missing.cpp','aliases.ld']})
 resolved=dict(x.split('=',1) for x in (out/'resolved-knobs.txt').read_text().splitlines() if '=' in x and not x.startswith('#'))
 expected={'RAIN_R10C_DC':str(int(arm=='on')),'RAIN_R10C_DIAG':str(int(arm=='on')),'GC_ASSET_GATE':'0','GC_ASSET_MOTION_UNKNOWN':'0','GC_ASSET_CATALOG_SHA256':'0','PS2_PVS_BATCH_COMPOSE':'0','PS2_PVS_EFFECTIVE0_SOURCES':'0','KOS_CACHE_P2_DIAG':'0','KOS_CACHE_P2':'1','DBG_WARP':'1','PC_SAMPLER':'0'}
 expected.update(plan['critical_common']);c.require(all(resolved.get(k)==v for k,v in expected.items()),'Resolved QA flags wrong')
 helpers={}
 for av in g['helper_compiles']:
  path=Path(av[av.index('-o')+1]);c.contained(out,path);helpers[str(path)]=helper_identity(path)
 found={str(p.resolve()) for p in (out/'obj').rglob('gc_asset_*.o')};c.require(found==set(helpers),'Helper object not accounted in actual compile log')
 binary=out/'re4dc-game.elf';raw=root/'program.bin';x=e.elf(binary,True)
 c.require(x['type']==2 and not x['undefined_gc_symbols'] and not x['defined_gc_symbols'],'GC gate retained in normal programme')
 raw_identity(x,raw)
 c.require(x['addresses']==e.nm_addresses(root/'symbols.txt'),'ELF/nm addresses')
 c.require(x['sizes']==e.size_default((root/'size.txt').read_text()),'ELF/size')
 sectionrows=e.section_text(root/'sections.txt');c.require(all(sectionrows.get(s['name'])==(s['bytes'],s['addr']) for s in x['allocated_sections']),'ELF/sections')
 syms=fullsymbols(binary);undefined=[s for s in syms if s['index']==0 and (s['info']>>4)!=0]
 c.require(not undefined,'Final unresolved provider symbols')
 ov={q.name:q for q in out.glob('*.ovl')};overlays(ov,plan)
 files={q.name:c.identity(q) for q in [binary,raw,*ov.values()]}
 if arm=='off':
  for name,r in plan['OFF_expected'].items():c.require(files[name]==r,'OFF same-QA identity '+name)
  c.require(x['addresses']['_end']==plan['OFF_end'],'OFF linked_end')
 rain=[s for s in syms if s['name']=='_re4dc_rain_r10c_diag'];validate_rain(rain,x['allocated_sections'],arm=='on')
 dep=dependencies(plan,arm)
 c.require(len(g['helper_compiles'])==len(helpers)==6,'Exactly six empty GC helpers required')
 return dict(complete=True,arm=arm,files=files,ELF=x,raw_object_count=len(g['objects']),graph=g,default_off_helpers=helpers,resolved_expected=expected,resolved_sha256=c.sha(out/'resolved-knobs.txt'),build_log_sha256=c.sha(root/'build.log'),undefined_symbols=undefined,rain_record=rain,dependency_closure=dep,provider_evidence={n:c.identity(scratch/n) for n in ['missing.txt','missing.cpp','aliases.ld']})

def main():
 resource.setrlimit(resource.RLIMIT_AS,(268435456,268435456));signal.alarm(120)
 a=argparse.ArgumentParser();a.add_argument('--arm',choices=['off','on'],required=True);a.add_argument('--output',required=True);args=a.parse_args();plan=c.load();c.check_inputs(plan);c.contained(Path(plan['root']),args.output);r=read_arm(plan,args.arm);c.exclusive_json(args.output,r)
if __name__=='__main__':main()
