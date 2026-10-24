#!/usr/bin/env python3
"""Bind existing room/material and texture metadata; no asset copying or conversion."""
import argparse,collections,hashlib,json,pathlib,re,resource,signal,subprocess,sys
sys.dont_write_bytecode=True

def pin(p):
 b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def main():
 resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,256*1024*1024));signal.alarm(120)
 a=argparse.ArgumentParser();a.add_argument('--folder',type=pathlib.Path,required=True);a.add_argument('--source',type=pathlib.Path,required=True);args=a.parse_args();b=args.folder;r=args.source
 assert not (b/'BINDINGS.json').exists()
 census=json.loads((b/'PS2-CENSUS.json').read_bytes());rooms={x['room']:x for x in census['census']}
 private=pathlib.Path('/mnt/c/Game Dev/Emulators/re4-assets-private');extract=private/'ps2rooms-20260930/extract-manifest.json';manifest=json.loads(extract.read_bytes())
 candidates=['r100','r107','r10a','r106','r108','r10b','r11a','r11b','r10c','r10d','r10e']
 result={'source':subprocess.check_output(['git','-C',str(r),'rev-parse','HEAD'],text=True).strip(),'census_pin':pin(b/'PS2-CENSUS.json'),'extraction_manifest':pin(extract),'rooms':{},'source_files':[],'existing_images_inspected':[],'limits':{'address_space_bytes':256*1024*1024,'timeout_seconds':120},'assets_copied':False}
 for room in candidates:
  q=rooms[room];ref=manifest['rooms'].get(room)
  entry={'member':q['member'],'water_like_count':q['water_like_count'],'water_like_texture_counts':q['water_like_texture_counts'],'matches_existing_extraction_member':q['member']['sha256']==ref['member']['sha256'] if ref else None}
  if room=='r100':src=private/'world-agent-20260926/ps2-rooms-20260929/inputs/r100'
  else:src=private/'ps2rooms-20260930/inputs'/room
  entry['world_material_inputs']=[]
  for suffix in ['SMD','TPL','scenario.idxmaterial','scenario.mtl','scenario.idx_ps2_smd']:
   p=src/(room+'_004.'+suffix)
   if p.exists():
    row=pin(p)
    if suffix.endswith('mtl'):row['material_count']=len(re.findall(r'^newmtl ',p.read_text(encoding='utf-8-sig'),re.M))
    entry['world_material_inputs'].append(row)
  result['rooms'][room]=entry
 for f in ['src/st1/r100.cpp','src/st1/r106.cpp','src/st1/r107.cpp','src/st1/r108.cpp','src/st1/r10a.cpp','src/st1/r10b.cpp','src/st1/r10c.cpp','src/st1/r10d.cpp','src/st1/r10e.cpp','src/st1/r11a.cpp','src/st1/r11b.cpp','src/game/esp08.cpp','src/game/espgen45.cpp','port/dreamcast/tools/d367/water/water_ps2_table.py','port/dreamcast/tools/d367/water/water_ps2_ext.py','tools/audit_ps2_fx_recipes.py','port/dreamcast/tools/ps2_room_extract.py','port/dreamcast/tools/d367/test12fx/fx_ps2_pack.py']:
  result['source_files'].append(pin(r/f))
 keys=private/'ps2lib/effects-tex/KEYS.tsv';result['effect_key_map']=pin(keys);result['effect_texture_bindings']=[]
 for line in keys.read_text().splitlines():
  fields=line.split('\t')
  if len(fields)!=6 or fields[1] not in ['common',*candidates]:continue
  match=re.search(r':0x([0-9a-f]+)$',fields[2]);
  if not match or int(match.group(1),16) not in (0xf2,0xf7,0xfe,0xef,0xc5):continue
  p=private/'ps2lib/effects-tex'/fields[1]/(fields[0]+'.re4tex')
  row={'key':fields[0],'room':fields[1],'gc_binding':fields[2],'frame':int(fields[3]),'width':int(fields[4]),'height':int(fields[5]),'package':pin(p) if p.exists() else None}
  result['effect_texture_bindings'].append(row)
 for p in [private/'ps2rooms-20260930/sheets'/f'{room}-ps2-sheet.png' for room in ['r106','r107','r10a']]+[pathlib.Path('/mnt/c/Flycast-Evidence/re4-dreamcast/fix-water-traps23/stills')/n for n in ['r10c-river.png','r10e-river.png']]:result['existing_images_inspected'].append(pin(p))
 result['notes']=['Existing image sheets mix offline renders and Dolphin reference; not fresh guest/look acceptance.','GC water-object IDs are not a proven one-to-one PS2 SMD placement map.','The effect ID/texture filter is a superset; f7/base-only and c5/vertical sheets do not independently identify river water.','The r100 TexRender path is current recovered GameCube-derived source, not a newly disassembled PS2 runtime proof.','No unique binding from the user phrase to an actual scene is available.']
 (b/'BINDINGS.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({'rooms':len(result['rooms']),'source_files':len(result['source_files']),'effect_texture_bindings':len(result['effect_texture_bindings']),'sha256':pin(b/'BINDINGS.json')['sha256']},indent=2))
if __name__=='__main__':main()