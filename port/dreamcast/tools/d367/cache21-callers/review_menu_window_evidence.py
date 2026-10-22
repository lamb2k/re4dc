#!/usr/bin/env python3
"""Verify retained identities/counter windows and summarize logged VRAM work. No replay."""
import argparse,collections,hashlib,json,pathlib,re,subprocess

PIN='b21116ec0cf2c984e9f49769a148373553bff00d'
ROOT=pathlib.Path('/mnt/c/Flycast-Evidence/re4-dreamcast')
def sha(path):
 h=hashlib.sha256()
 with pathlib.Path(path).open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def winpath(value):
 if value.startswith('C:'):return pathlib.Path('/mnt/c'+value[2:].replace('\\','/'))
 if value.startswith('\\\\wsl.localhost\\Ubuntu-24.04'):return pathlib.Path(value.split('Ubuntu-24.04',1)[1].replace('\\','/'))
 return pathlib.Path(value)
def main():
 p=argparse.ArgumentParser();p.add_argument('--repo',required=True);p.add_argument('--out',required=True);a=p.parse_args();out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=False)
 base=ROOT/'cache21-window-20261021';payload=ROOT/'cache21-payload-20261021';hashes=[];checks=[]
 def record(path,expected=None):
  path=pathlib.Path(path);value=sha(path)
  if expected:assert value==expected,(str(path),value,expected)
  hashes.append(dict(path=str(path),bytes=path.stat().st_size,sha256=value,matched_retained_identity=bool(expected)))
  return value
 def load(path):record(path);return json.loads(pathlib.Path(path).read_text(encoding='utf-8-sig'))
 def c(name,value):assert value,name;checks.append(dict(name=name,result='PASS',kind='retained evidence/source check, no new target run'))
 pair=load(base/'inventory-pair-result.json');builds=load(base/'paired-builds.json');demand=load(base/'window-demand-attribution-02.json');traffic=load(payload/'window-traffic-reconciliation-v1.json');host=load(payload/'window-traffic-host-v3.json')
 c('same frozen source across original reports',all(x==PIN for x in [pair['source'],builds['source'],traffic['frozen_source'],host['frozen_source']]))
 for name,expected in traffic['input_receipts'].items():
  if name not in ['run-output.txt','off_run_output_sha256','on_run_output_sha256']:record(base/name,expected)
 record(payload/'window-traffic-host-v3.json',traffic['host_replay_receipt']['sha256'])
 source=[]
 for name,expected in traffic['source_identities'].items():
  raw=subprocess.check_output(['git','-C',a.repo,'show',PIN+':'+name]);digest=hashlib.sha256(raw).hexdigest();assert digest==expected,name
  source.append(dict(path=name,source_commit=PIN,bytes=len(raw),sha256=digest,blob=subprocess.check_output(['git','-C',a.repo,'rev-parse',PIN+':'+name]).decode().strip()))
 for arm,v in traffic['builds'].items():
  for kind in ['program','ELF','generated_iso_source']:record(v[kind]['path'],v[kind]['sha256'])
  c(arm+' program/ELF reports agree',v['program']['sha256']==builds['arms'][arm]['program_sha256'] and v['ELF']['sha256']==builds['arms'][arm]['elf_sha256'])
 record(traffic['pack']['path'],traffic['pack']['sha256'])
 with pathlib.Path(traffic['pack']['path']).open('rb') as f:
  for member in demand['pack']['selected_members']:
   f.seek(member['offset']);data=f.read(member['stored_member_bytes']);assert hashlib.sha256(data).hexdigest()==member['member_sha256'],member['key']
 c('extra members match source payload accounting',len(demand['pack']['selected_members'])==26 and sum(m['texture_payload_bytes'] for m in demand['pack']['selected_members'])==122912)
 results={};launches={}
 for arm in ['off','on']:
  logpath=base/('inventory-'+arm+'-01')/'run-output.txt';record(logpath,traffic['input_receipts'][arm+'_run_output_sha256']);lines=logpath.read_text(errors='replace').splitlines();samples=load(base/('inventory-'+arm+'-samples.json'))
  bounds=pair['arms'][arm];start=next(x for x in samples if x['host_s']==bounds['before_host_s']);end=next(x for x in samples if x['host_s']==bounds['after_host_s']);delta={k:end[k]-start[k] for k in ['reads','bytes','block']};c(arm+' original counter window unchanged',delta==bounds['delta'])
  for plateau in traffic['counter_plateaus'][arm]['samples']:
   found=next(x for x in samples if x['host_s']==plateau['host_s']);c(arm+' retained plateau '+str(plateau['host_s']),all(found[k]==plateau[k] for k in ['reads','bytes','block']))
  begin=next(i for i,line in enumerate(lines) if 'native texture hold restore: picks=' in line);finish=next(i for i in range(begin+1,len(lines)) if 'native texture preload: frame=' in lines[i]);current=None;retries=[];opens=[]
  for i in range(begin,finish):
   m=re.search(r'native UI: load .*?/([0-9a-f]{8}-[0-9a-f]{8})\.re4tex',lines[i])
   if m:current=m[1];opens.append(current)
   if 'fragmented VRAM, evicted and retrying' in lines[i]:retries.append(dict(line=i+1,key=current,text=lines[i]))
  roomline=next(line for line in lines[finish:] if 'vram room: r=100 at=preload' in line)
  room={k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',roomline)}
  prior=next(line for line in reversed(lines[:begin]) if 'native UI VRAM: frame=360 ' in line)
  before={k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',prior)}
  c(arm+' logical restore opens are unique',len(opens)==len(set(opens)))
  c(arm+' restore log matches existing attribution order',opens==[e['key'] for e in demand['arms'][arm]['events'] if e['phase']=='restore'])
  record(base/bounds['ordinary_room_visible_screenshot'])
  launch=load(base/('inventory-'+arm+'-01')/'run-result.json');record(base/('inventory-'+arm+'-01')/'disc.gdi')
  c(arm+' original launch completed',launch['emulator_exited'] and launch['reader_exit']==0 and not launch['errors'])
  launches[arm]=dict(start_utc=launch['start_utc'],end_utc=launch['end_utc'],disc=launch['disc'],tracks=launch['tracks'],key_log=launch['key_log'])
  results[arm]=dict(window_before=start,window_after=end,delta=delta,return_preload_line=finish+1,return_preload=lines[finish],held_counter_frame360=before,return_vram_summary=room,restore_logical_opens=opens,fragmentation_retry_rows=retries)
 c('no lost-count splice',all(results['on']['delta'][k]-results['off']['delta'][k]==pair['on_minus_off'][k] for k in ['reads','bytes','block']))
 c('held phase unchanged traffic',traffic['counter_plateaus']['on']['held_delta']==traffic['counter_plateaus']['off']['held_delta'])
 c('pre-return held VRAM counter baseline equal',all(results['on']['held_counter_frame360'][k]==results['off']['held_counter_frame360'][k] for k in ['used','free','retries','evicted']))
 delta={k:results['on']['return_vram_summary'][k]-results['off']['return_vram_summary'][k] for k in ['loads','evicted','retries','pinned','free','largest']}
 c('extra observed VRAM work',delta==dict(loads=26,evicted=7,retries=5,pinned=28192,free=-28192,largest=-4224))
 extra=set(demand['comparison']['extra_on_restore_keys']);retryextra=[r for r in results['on']['fragmentation_retry_rows'] if r['key'] in extra]
 retry_delta=collections.Counter(r['key'] for r in results['on']['fragmentation_retry_rows'])-collections.Counter(r['key'] for r in results['off']['fragmentation_retry_rows'])
 c('four extra keys and one common key add five retries',len(retryextra)==4 and sum(retry_delta.values())==5 and retry_delta['cf2208cd-a6bfb2ef']==1)
 c('source bytes reconcile exact original delta',sum(traffic['source_reconciliation'][k] for k in ['extra_member_payload','extra_member_header_descriptors','extra_final_stream_tail_overread','extra_index_lookup_stream_bytes'])==pair['on_minus_off']['bytes'])
 c('source request classes reconcile exact original delta',sum(v for k,v in traffic['source_reconciliation']['requests'].items() if k!='sum')==pair['on_minus_off']['reads'])
 stage=load(base/'window-on-input'/'candidate-receipt.json');baseline=load(ROOT/'feedback21-runtime-20261021'/'qa-aafc10f3-input'/'input-receipt.json')
 c('retained candidate inner-file identity claim',stage['unchanged_files']==1728 and stage['candidate_overlays_from_same_on_build'] and len(stage['off_overlays_14_exact'])==14)
 result=dict(kind='independent retained menu-window identity/counter/VRAM review; no replay',frozen_source=PIN,checks=checks,verified_inputs=hashes,verified_source_objects=source,arms=results,original_launches=launches,retained_outer_image_identities=dict(off=baseline['files']['gdemu/track03.bin'],on=dict(sha256=stage['track03_sha256'],bytes=launches['on']['tracks']['track03.iso']),qualification='Retained manifest identities; tracks not rehashed or copied by this review; OFF2352/ON2048 layouts differ'),extra_retry_keys=[r['key'] for r in retryextra],additional_retry_keys=dict(retry_delta),return_vram_delta=delta,source_reconciliation=traffic['source_reconciliation'],status='negative traffic finding; SS_WINDOW_HOLD_RESTORE stays disabled',limits=['One actual inventory cycle, no second-cycle inference','Host-time windows not identical source frames','Repeated metadata reopen is not an extra uncached drive read','No attribution of block417678us or physical seeks','Existing mocked KOS replay accounting is verified by identity, not rerun'])
 target=out/'receipt.json';target.write_text(json.dumps(result,indent=2)+'\n');assert target.stat().st_size<4*1024*1024
 print(json.dumps(dict(result='PASS',checks=len(checks),verified_file_reads=len(hashes),source_objects=len(source),fresh_bytes=target.stat().st_size,extra_retry_keys=result['extra_retry_keys'])))
if __name__=='__main__':main()
