"""Read-only programme/asset authentication and explicit budget freeze, no stage."""
from pathlib import Path
import hashlib,json,sys,types
HERE=Path(__file__).resolve().parent
assert __debug__ and sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
p=HERE/'core.py';k=types.ModuleType('core');k.__file__=str(p);sys.modules['core']=k;exec(compile(p.read_bytes(),str(p),'exec',dont_inherit=True),k.__dict__)
def pin(p):return dict(path=str(p),identity=k.row(p))
def main():
 assert not (HERE/'BASELINE.json').exists(),'One preparation, immutable predecessors'
 c,pins=k.parent();oldplan=k.read(k.OLD/'BASE-PLAN.json');original=k.read(k.OLD/'CURRENT-CANDIDATE-MANIFEST.json')
 lane=HERE.parent;prior=lane/'kos-budget-retest-media-prep-v1';scope={'__file__':str(prior/'capacity.py'),'__name__':'historical_capacity'};exec(compile((prior/'capacity.py').read_bytes(),str(prior/'capacity.py'),'exec'),scope)
 roots=scope['ROOTS'];total,members,_=k.scan(roots,hashes=True)
 assert total+1100*1024**2<k.AGG,'Conservative one-track aggregate estimate cannot fit'
 s=__import__('os').statvfs('/mnt/c');assert s.f_bavail*s.f_frsize>=k.ADMIT
 durable=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/gc-motion24-20261024/stream-budget-427-qa-programmes-v1');mp=durable/'MANIFEST.json';assert k.sha(mp)=='73bc1537067aa0c28a8e25e5117d40d2ad045c7be7e83adf4893898b8ef52063'
 manifest=k.read(mp);assert manifest['source']==k.SOURCE
 for v in manifest['files']:k.verify(durable/v['path'],v)
 terminal=durable/'continuation-receipt.json';assert k.sha(terminal)=='4cccda258c4db04e5be740be727cf9b7af20e94a289df5401ee8bd916470e0b9';t=k.read(terminal);assert t['complete']
 review=lane/'review-budget-qa-on-target-v1/REVIEW.json';assert k.sha(review)=='3d207941b8a91c191f8487f5a5d2553fa07cf9d262fddb50be0437bcdb972d66';assert k.read(review)['verdict']=='CLEAR_STATIC_TARGET_READBACK_ONLY'
 for name,want in [('READBACK.json','130bb13f1788cc13fefd001a77447ca3542661cd5cc4636797bede8e6ed53f88')]:assert k.sha(review.parent/name)==want
 # Authenticate every original asset source; link only to these exact inodes.
 fixture=Path(oldplan['assets']['read_only_fixture']);programmes={'1ST_READ.BIN'}|{'dc/'+n for n in oldplan['overlays']}
 for name,v in original.items():
  c.key(name)
  if name not in programmes:k.verify(fixture/name,v)
 k.verify(oldplan['sourceIP_path'],oldplan['sourceIP'])
 k.fresh(HERE/'BASELINE.json',dict(roots=roots,unique_bytes=total,members=members,old_contracts_unchanged=True,successor_authorization='Root explicit resource plan: old historical baseline +new delta1.25GiB/aggregate6.5GiB; not silent old4GiB reset'))
 plan={**oldplan,'source':k.SOURCE,'programmes':'CORRECTED_DURABLE_427_READBACK_CLEAR','squeeze0_fixture':oldplan['original_fixture']['identity'],'capacity':dict(delta=k.DELTA,aggregate=k.AGG,admit=k.ADMIT,floor=k.FLOOR)}
 k.fresh(HERE/'BASE-PLAN.json',plan);k.fresh(HERE/'CURRENT-CANDIDATE-MANIFEST.json',original)
 binding=dict(source=k.SOURCE,terminal=pin(terminal),target_review=dict(status=k.read(review)['verdict'],receipt=pin(review),readback=pin(review.parent/'READBACK.json')),durable_manifest=pin(mp),arms={})
 for arm in ['off','on']:
  files={n:dict(path=str(durable/arm/n),identity=dict(size=v['bytes'],sha256=v['sha256'])) for n,v in t['arms'][arm]['files'].items()}
  expected=dict(original);expected['1ST_READ.BIN']=files['program.bin']['identity']
  for n in oldplan['overlays']:expected['dc/'+n]=files[n]['identity']
  for n in ['warp','padscript','w11']:expected['dc/'+n+'.txt']=dict(size=8192,sha256=hashlib.sha256(bytes(8192)).hexdigest())
  k.fresh(HERE/(arm.upper()+'-EXPECTED-MANIFEST.json'),expected)
  # Exact ELF values from authentic final nm metadata, never guessed original ON.
  nm=(durable/arm/'symbols.txt').read_text();addresses={}
  for line in nm.splitlines():
   w=line.split()
   if len(w)>=3 and w[-1] in ['_re4dc_logbuf','_re4dc_log_head','_re4dc_stage']:assert w[-1] not in addresses;addresses[w[-1]]=int(w[0],16)
  assert len(addresses)==3
  binding['arms'][arm]=dict(ELF=files.pop('re4dc-game.elf'),programmes=files,symbols=addresses,expected=k.row(HERE/(arm.upper()+'-EXPECTED-MANIFEST.json')))
 k.fresh(HERE/'BINDING.json',binding);k.validate_binding(binding)
 # Metadata only: no unowned fixture copies, Pillow/install payloads or media.
 pillow=lane/'pillow-isolated-prep-v1';assert k.sha(pillow/'SOURCE-SEAL.json')=='3bcff1c5a4eb7f5823296be065c097a246251ffd3c3d3d42ecf11073eeb7add2'
 refs=[pin(pillow/'SOURCE-SEAL.json'),pin(pillow/'pillow_launcher.py'),pin(pillow/'PILLOW-PINS.json')]
 fixtures=[pin(lane/'qa-memory-media-prep/fixtures'/('kos-fight-49152-'+str(f)+'.txt')) for f in [0,1]]
 k.fresh(HERE/'ALLOCATION-CONTRACT.json',dict(source=k.SOURCE,baseline=k.row(HERE/'BASELINE.json'),binding=k.row(HERE/'BINDING.json'),prior_unique_bytes=total,new_delta_cap=k.DELTA,aggregate_cap=k.AGG,C_admission=k.ADMIT,C_floor=k.FLOOR,new_final_arms=['on'],existing_OFF=str(k.OFF),reuse_OFF_exact_bytes=True,immutable_asset_hardlinks_only=True,no_whole_asset_copy=True,fixtures=fixtures,pillow=refs,cases=['off-frag0','on-frag0','off-frag1','on-frag1'],seconds=45,exact_child_cap=55,root_pool=3,global_slots=16,H2='HELD_NO_PERMISSION',FP_NOLIMIT='1',configLimitFPS='no',memory_result='NOT_RUN',no_stage=True,no_guest=True))
 print(json.dumps(dict(status='BOUND_PREPARATION_NO_STAGE_NO_GUEST',capacity=k.capacity(),binding=k.row(HERE/'BINDING.json'))))
if __name__=='__main__':main()
