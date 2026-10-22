"""Bounded actual-index negative controls; no runtime source or package payload writes."""
from pathlib import Path
import argparse,hashlib,json,os,shutil,signal,struct,subprocess,time
T=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--ref',required=True);p.add_argument('--pack',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--working-index',type=Path,required=True);a=p.parse_args()
assert not a.out.exists();start_free=shutil.disk_usage('/mnt/c').free;assert start_free>=18*1024**3+128*1024**2;a.out.mkdir()
sha=lambda b:hashlib.sha256(b).hexdigest()
paths=['port/dreamcast/game/platform/include/texpack_index.inc','port/dreamcast/game/platform/include/texpack_payload_retry.inc']
inputs={}
for path in paths:
 b=(a.working_index.read_bytes()if path.endswith('/texpack_index.inc')else subprocess.check_output(['git','-C',str(a.source),'show',a.ref+':'+path]));(a.out/Path(path).name).write_bytes(b);inputs[path]={'bytes':len(b),'sha256':sha(b)}
with a.pack.open('rb')as f:
 header=f.read(2048);assert header[:8]==b'RE4PAK1\0';count=struct.unpack_from('<I',header,12)[0];nsec=(count*16+2047)//2048;assert 384<=count<=8192
 prefix=header+f.read(nsec*2048);assert len(prefix)==2048*(nsec+1)
(a.out/'original-index-prefix.bin').write_bytes(prefix)
runs=[]
def guarded(cmd,name):
 log=a.out/(name+'.log');started=time.time()
 with log.open('xb')as output:
  child=subprocess.Popen(cmd,stdout=output,stderr=subprocess.STDOUT,start_new_session=True)
  stat=Path(f'/proc/{child.pid}/stat').read_text().split()[21]
  (a.out/(name+'-owned-process.json')).write_text(json.dumps({'pid':child.pid,'pgid':os.getpgid(child.pid),'proc_start':stat,'command':cmd},indent=2)+'\n')
  while child.poll()is None:
   resource_ok=shutil.disk_usage('/mnt/c').free>=18*1024**3+64*1024**2 and sum(p.stat().st_size for p in a.out.rglob('*')if p.is_file())<20*1024**2 and log.stat().st_size<1024**2 and time.time()-started<55
   if not resource_ok:
    assert os.getpgid(child.pid)==child.pid and Path(f'/proc/{child.pid}/stat').read_text().split()[21]==stat
    os.killpg(child.pid,signal.SIGTERM);child.wait(timeout=5);raise RuntimeError('owned host resource guard stopped '+name)
   time.sleep(.1)
 assert child.returncode==0,(name,log.read_text()[-3000:])
 return log.read_text()
for guard in [0,1]:
 command=['bash','/root/probe/d367-buildslot.sh','g++','-std=c++17','-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all','-DRE4DC_TEX_PAYLOAD_RETRY='+str(guard),'-DRE4DC_TEX_PACK_FAULT=0','-I'+str(a.out),str(T/'probe.cpp'),'-o',str(a.out/('probe'+str(guard)))]
 guarded(command,'compile'+str(guard));output=guarded([str(a.out/('probe'+str(guard))),str(a.out/'original-index-prefix.bin'),str(a.pack.stat().st_size)],'run'+str(guard))
 runs.append({'guard':guard,'command':command,'results':[json.loads(x)for x in output.splitlines()]})
record={'scope':'Main working-tree per-sector index candidate plus frozen helper compiled unchanged with synthetic fault reader over fresh original sorted header/index only. No package payload/guest/runtime edits.','source_parent_ref':a.ref,'working_index':str(a.working_index),'source_inputs':inputs,'fixture_sha256':sha((T/'probe.cpp').read_bytes()),'runner_sha256':sha(Path(__file__).read_bytes()),'pack_index':{'source':str(a.pack),'pack_size':a.pack.stat().st_size,'count':count,'sectors':nsec,'prefix_bytes':len(prefix),'fresh_prefix_sha256':sha(prefix),'previously_sealed_pack_sha256':'18fcee11491f2c1f212863d6d6b572b3997f691b2e990217e1c2518f134021ef','full_pack_rehashed_this_unit':False},'runs':runs,'C_start':start_free,'C_end':shutil.disk_usage('/mnt/c').free,'output_bytes_before_receipt':sum(p.stat().st_size for p in a.out.rglob('*')if p.is_file()),'limits':'Injected read errors/key changes/CRC refusals after complete valid init; no normal-media occurrence, payload I/O saving, target timing, lifetime/race, full program, Flycast, release or hardware acceptance claim.'}
(a.out/'receipt.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({'source':a.ref,'count':count,'runs':[{'guard':r['guard'],'results':[x for x in r['results']if x.get('case')in ['minimal_ABA_same_frame','two_failed_sectors_30_frames','CRC_only_mutation_not_checked_OFF']or 'checks'in x]}for r in runs],'output_bytes':record['output_bytes_before_receipt']},indent=2))
