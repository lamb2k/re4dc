#!/usr/bin/env python3
"""Read-only ELF32/SH4 selected-unit checker. No subprocess/toolchain invocation."""
import argparse,hashlib,json,pathlib,re,struct

def sha(path):return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
class Elf:
 def __init__(self,path):
  self.path=pathlib.Path(path);self.raw=self.path.read_bytes();b=self.raw
  if len(b)<52 or b[:7]!=b'\x7fELF\x01\x01\x01':raise ValueError('ELF32 little endian required')
  h=struct.unpack_from('<HHIIIIIHHHHHH',b,16);self.kind,self.machine,self.flags=h[0],h[1],h[6]
  if self.machine!=42:raise ValueError('SH machine required')
  off,ents,n,strings=h[5],h[10],h[11],h[12]
  if ents!=40 or not(0<n<32768) or off+n*40>len(b) or strings>=n:raise ValueError('section bounds')
  rows=[struct.unpack_from('<IIIIIIIIII',b,off+40*i) for i in range(n)]
  def data(row):
   if row[1]==8:return b''
   if row[4]+row[5]>len(b):raise ValueError('section file extent')
   return b[row[4]:row[4]+row[5]]
  def word(tab,i):
   if not(0<=i<len(tab)):raise ValueError('string offset')
   end=tab.find(b'\0',i)
   if end<0:raise ValueError('unterminated name')
   return tab[i:end].decode('utf8')
  names=data(rows[strings]);self.sections=[]
  for i,row in enumerate(rows):
   self.sections.append(dict(index=i,name=word(names,row[0]),type=row[1],flags=row[2],address=row[3],offset=row[4],size=row[5],link=row[6],info=row[7],align=row[8],entsize=row[9],data=data(row)))
  self.symbols=[];symtabs={}
  for section in self.sections:
   if section['type'] not in (2,11):continue
   if section['entsize']!=16 or len(section['data'])%16 or section['link']>=n:raise ValueError('symbol table layout')
   tab=self.sections[section['link']]['data'];syms=[]
   for i in range(0,len(section['data']),16):
    nm,val,size,info,other,ndx=struct.unpack_from('<IIIBBH',section['data'],i)
    sym=dict(name=word(tab,nm),value=val,size=size,bind=info>>4,type=info&15,section=ndx)
    syms.append(sym);self.symbols.append(sym)
   symtabs[section['index']]=syms
  if len([x['name'] for x in self.sections if x['flags']&2])!=len(set(x['name'] for x in self.sections if x['flags']&2)):raise ValueError('duplicate allocated section names')
  self.relocations=[]
  for section in self.sections:
   if section['type'] not in (4,9):continue
   if section['link'] not in symtabs or section['info']>=n:raise ValueError('relocation layout')
   syms=symtabs[section['link']];target=self.sections[section['info']]
   step=12 if section['type']==4 else 8
   if section['entsize']!=step or len(section['data'])%step:raise ValueError('relocation extent')
   for i in range(0,len(section['data']),step):
    offset,info=struct.unpack_from('<II',section['data'],i);idx=info>>8
    if idx>=len(syms):raise ValueError('relocation symbol')
    sym=syms[idx];name=sym['name']
    if sym['type']==3 and sym['section']<n:name=self.sections[sym['section']]['name']
    addend=struct.unpack_from('<i',section['data'],i+8)[0] if step==12 else None
    if offset>=target['size']:raise ValueError('relocation target extent')
    # Resolved symbol identity includes section/value, so a changed definition
    # cannot hide behind an unchanged relocation name/type/offset.
    target_name=self.sections[sym['section']]['name'] if sym['section']<n else 'SPECIAL:'+str(sym['section'])
    resolved=(name,target_name,sym['value'],sym['size'],sym['bind'],sym['type'])
    self.relocations.append((target['name'],offset,info&255,resolved,addend))
 def allocated(self):
  return {s['name']:(s['type'],s['flags'],s['size'],s['align'],hashlib.sha256(s['data']).hexdigest()) for s in self.sections if s['flags']&2}
 def alloc_relocations(self):
  names=set(self.allocated());return sorted((r for r in self.relocations if r[0] in names),key=repr)
 def undefined(self):return {s['name']:s['bind'] for s in self.symbols if s['name'] and s['section']==0 and s['bind'] in(1,2)}
 def definitions(self):return {s['name'] for s in self.symbols if s['section']!=0 and s['bind'] in(1,2)}
 def record(self,required):
  found=[s for s in self.symbols if s['name'] in ('re4dc_rain_r10c_diag','_re4dc_rain_r10c_diag') and s['section']!=0]
  if not required:
   if found:raise ValueError('disabled record exists')
   return None
  if len(found)!=1:raise ValueError('ON record not unique')
  sym=found[0]
  if sym['section']>=len(self.sections):raise ValueError('ON record section')
  sec=self.sections[sym['section']]
  if sym['size']!=128 or sym['bind']!=1 or sym['type']!=1 or sym['value']+128>sec['size'] or sym['value']%32 or sec['align']<32 or sec['type']!=8 or sec['flags']&3!=3:raise ValueError('ON record size/alignment/storage')
  return {'name':sym['name'],'bytes':sym['size'],'section':sec['name'],'section_alignment':sec['align'],'section_relative_value':sym['value'],'absolute_P1_address':'UNPROVEN ET_REL'}
 def sizes(self):
  return {key:sum(s['size'] for s in self.sections if s['flags']&2 and predicate(s)) for key,predicate in [('text',lambda s:bool(s['flags']&4)),('data',lambda s:bool(s['flags']&1) and s['type']!=8),('bss',lambda s:s['type']==8),('rodata',lambda s:not(s['flags']&5) and s['type']!=8)]}

def require_identity(a,b):
 if a.kind!=1 or b.kind!=1 or a.flags!=b.flags or a.allocated()!=b.allocated() or a.alloc_relocations()!=b.alloc_relocations():raise ValueError('disabled allocated section/relocation/ABI mismatch')

def stacks(path):
 result=[]
 for line in pathlib.Path(path).read_text().splitlines():
  m=re.fullmatch(r'(.+)\t(\d+)\t(.+)',line)
  if not m:raise ValueError('unknown stack usage row')
  result.append({'declaration':m[1],'self_bytes':int(m[2]),'classification':m[3]})
 return result

def check(root,pins):
 root=pathlib.Path(root);run=json.loads((root/'matrix-result.json').read_text())
 if not run.get('selected_compilation_complete') or run['source']!=pins['source'] or run['base']!=pins['base'] or run.get('case_names')!=pins['case_names'] or run.get('runtime')!=pins['runtime'] or run.get('limits')!=pins['limits']:raise ValueError('incomplete/wrong-source run')
 for rel in ('RESERVED.json','environment-bootstrap.log','environment.nul','grant.json','pins.json'):
  if rel not in run['artifacts']:raise ValueError('missing allocation/bootstrap artifact')
 for case in pins['case_names']:
  for suffix in ('.log','.stdout'):
   if case+'-partial-link'+suffix not in run['artifacts']:raise ValueError('missing partial-link log')
  for unit in ('filter06','espgen44'):
   for phase in ('deps','includes','compile','strip','disassemble'):
    if case+'-'+unit+'-'+phase+'.log' not in run['artifacts']:raise ValueError('missing command/include trace')
    if phase in ('compile','strip') and case+'-'+unit+'-'+phase+'.stdout' not in run['artifacts']:raise ValueError('missing command stdout')
   for suffix in ('.o','-nodebug.o','.d','.su','.ii','-disassembly.txt','-argv.json','-before.d','-before-pins.json','-actual-pins.json'):
    if 'cases/'+case+'/'+unit+suffix not in run['artifacts']:raise ValueError('missing unit artifact')
  if 'cases/'+case+'/pair.o' not in run['artifacts']:raise ValueError('missing pair artifact')
 for rel,pin in run['artifacts'].items():
  candidate=root/rel;path=candidate.resolve()
  if any(x.is_symlink() for x in [candidate]+list(candidate.parents) if x.is_relative_to(root)) or not path.is_relative_to(root.resolve()) or not path.is_file() or sha(path)!=pin['sha256'] or path.stat().st_size!=pin['bytes']:raise ValueError('artifact drift')
 if sha(pins['provider']['path'])!=pins['provider']['sha256']:raise ValueError('provider drift')
 provider=Elf(pins['provider']['path']);provided=provider.definitions();report={'scope':'selected SH4 objects only; no whole programme/guest/cache execution/ancestry/look acceptance','objects':[],'off_identity':[],'on_pricing':[],'opcodes_require_root_review':True}
 for feature in (0,1):
  base=root/'cases'/('base-f'+str(feature));base_pair=Elf(base/'pair.o')
  for diag in ('absent','0','1'):
   case=root/'cases'/('new-f'+str(feature)+'-d'+diag);pair=Elf(case/'pair.o')
   for unit in ('filter06','espgen44'):
    a=Elf(base/(unit+'.o'));b=Elf(case/(unit+'.o'));required=diag=='1' and unit=='filter06'
    a.record(False);record=b.record(required)
    row={'feature':feature,'diag':diag,'unit':unit,'raw_sha256':sha(case/(unit+'.o')),'raw_equal_baseline':sha(case/(unit+'.o'))==sha(base/(unit+'.o')),'strip_debug_sha256':sha(case/(unit+'-nodebug.o')),'strip_debug_raw_equal_baseline':sha(case/(unit+'-nodebug.o'))==sha(base/(unit+'-nodebug.o')),'differing_sections':[x['name'] for x in b.sections if x['name'] not in {y['name'] for y in a.sections} or x['data']!=next((y['data'] for y in a.sections if y['name']==x['name']),None)],'record':record,'sizes':b.sizes(),'self_stack':stacks(case/(unit+'.su')),'baseline_self_stack':stacks(base/(unit+'.su')),'undefined_symbols':b.undefined(),'baseline_undefined_symbols':a.undefined()}
    report['objects'].append(row)
    if diag!='1':
     require_identity(a,b);require_identity(Elf(base/(unit+'-nodebug.o')),Elf(case/(unit+'-nodebug.o')))
     report['off_identity'].append({'feature':feature,'diag':diag,'unit':unit,'allocated_and_relocations_identical':True,'raw_equal':row['raw_equal_baseline'],'strip_debug_raw_equal':row['strip_debug_raw_equal_baseline']})
   new_u={x for x,v in pair.undefined().items() if base_pair.undefined().get(x)!=v}
   unknown={x for x in new_u if x not in provided}
   if unknown:raise ValueError('unsupported new provider imports '+repr(sorted(unknown)))
   if any('dcache_wback_all' in x or 'dcache_purge_all' in x for x in new_u):raise ValueError('new whole-cache provider')
   if diag=='1':
    a=base_pair.sizes();b=pair.sizes()
    report['on_pricing'].append({'feature':feature,'selected_pair_section_delta':{k:b[k]-a[k] for k in a},'new_or_changed_external_imports':{x:pair.undefined()[x] for x in sorted(new_u)},'pair_undefined_symbols':pair.undefined(),'baseline_pair_undefined_symbols':base_pair.undefined(),'new_imports_resolved_by_frozen_provider':True,'absolute_linked_padding_stack_headroom':'UNPROVEN'})
 # Disassembly is retained verbatim. Structural counts are evidence, not a four-line semantic proof.
 report['opcode_observations']=[]
 for feature in(0,1):
  path=root/'cases'/('new-f'+str(feature)+'-d1')/'filter06-disassembly.txt';s=path.read_text()
  report['opcode_observations'].append({'feature':feature,'ocbwb_occurrences':len(re.findall(r'\bocbwb\b',s)),'ocbi_occurrences':len(re.findall(r'\bocbi\b',s)),'ocbp_occurrences':len(re.findall(r'\bocbp\b',s)),'P2_mask_literal_seen':any(b'\0\0\0\xa0' in x['data'] for x in Elf(path.parent/'filter06.o').sections if x['flags']&2),'boot_128B_fourline_and_all_P2_access_semantics':'REQUIRES actual function/relocation opcode review; never inferred from counts'})
 return report
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--root',required=True);ap.add_argument('--pins',required=True);ap.add_argument('--out');args=ap.parse_args();result=check(args.root,json.loads(pathlib.Path(args.pins).read_text()));out=json.dumps(result,indent=2)+'\n'
 if args.out:
  with open(args.out,'x') as f:f.write(out)
 else:print(out,end='')