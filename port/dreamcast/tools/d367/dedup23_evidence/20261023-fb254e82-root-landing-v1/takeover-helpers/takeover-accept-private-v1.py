from pathlib import Path
import hashlib,json,shutil
base=Path(r'C:\Game Dev\Emulators')
e=Path(r'C:\Flycast-Evidence\re4-dreamcast\dedup-offline23-20261023\current-4be08e01')
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
seal=e/'private-qa-pair-seal-r1.json'
assert sha(seal)=='4180931954be3dc47e587bea96b82a550799c898a7491a9de4df5e01a69f95be'
review=base/'codex-lanes/dedup-offline23/root-qa-review4be/REVIEW.md'
assert sha(review)=='4e799aa3a8dc9051819ec77148f2be88067a0d18beff3579b3a643b05e733317'
j=json.loads(seal.read_text());out=e/'root-private-delivery';out.mkdir(exist_ok=False)
receipt=dict(status='ACCEPTED_FOR_PRIVATE_CONSOLE_FEEDBACK',source=j['source'],worker_seal_sha256=sha(seal),independent_review_sha256=sha(review),production_dedup=0,physical_acceptance=False,hardware_performance_claim=False,profile=dict(SCENERY_EMIT_PREFETCH=0,SCENERY_SELECT_LEAN2=0),normal_qa_heap=dict(off=48768,on=98496),standard_heap=dict(off=93920,on=139552),limits=['Actual final-GDI boot differs from separately labelled fixture-proxy menu-warp/H2.', 'Known baseline Mendez late-pair material issue remains; no texture completeness claim.', 'Later prefetch context repair does not alter this exact frozen4be QA pair.', 'No full-route, fresh full-release or physical acceptance.'])
rp=out/'ROOT-ACCEPTANCE.json';rp.write_text(json.dumps(receipt,indent=2)+'\n');delivery={}
for arm,label in [('off','Off'),('on','On')]:
 d=base/f'RE4DC-QA23-Dedup-{label}-4be08e01';backup=out/arm;backup.mkdir()
 for name in ('README.txt','IDENTITY.json','SHA256SUMS.txt','QUALIFICATION-PENDING.txt'):shutil.copyfile(d/name,backup/name)
 for line in (d/'SHA256SUMS.txt').read_text().splitlines():
  pin,rel=line.split('  ',1);assert sha(d/rel)==pin,(arm,rel)
 ident=json.loads((d/'IDENTITY.json').read_text());assert ident['source']==j['source']
 assert ident['normal_qa_gates']['h2']['heap_before']==receipt['normal_qa_heap'][arm]
 ident['status']='ACCEPTED_FOR_PRIVATE_CONSOLE_FEEDBACK'
 ident['root_acceptance_sha256']=sha(rp)
 ident['known_limitations']=[x for x in ident['known_limitations'] if x!='Root integration/recipe decision pending']
 ident['known_limitations'].append('Production dedup remains off; later integration has its separate source and image receipts.')
 (d/'IDENTITY.json').write_text(json.dumps(ident,indent=2)+'\n')
 text=(d/'README.txt').read_text().replace('LOCAL QA GATES PASS; ROOT REVIEW / INTEGRATION / PHYSICAL ACCEPTANCE PENDING.','ROOT-REVIEWED PRIVATE CONSOLE PAIR; PHYSICAL ACCEPTANCE PENDING.').replace('Root final review remains required.','Root private-media review passed; production dedup remains off.')
 (d/'README.txt').write_text(text)
 (d/'QUALIFICATION-PENDING.txt').write_text('Historical filename retained. Root private-media review passed; physical acceptance and hardware performance remain pending. Production dedup stays off. See ROOT-ACCEPTANCE.json.\n')
 shutil.copyfile(rp,d/'ROOT-ACCEPTANCE.json')
 lines=[sha(p)+'  '+p.relative_to(d).as_posix() for p in sorted(d.rglob('*')) if p.is_file() and p.name!='SHA256SUMS.txt']
 (d/'SHA256SUMS.txt').write_text('\n'.join(lines)+'\n')
 for line in lines:
  pin,rel=line.split('  ',1);assert sha(d/rel)==pin
 delivery[arm]=dict(path=str(d),identity_sha256=sha(d/'IDENTITY.json'),sums_sha256=sha(d/'SHA256SUMS.txt'),files=len(lines))
(out/'DELIVERY-READBACK.json').write_text(json.dumps(delivery,indent=2)+'\n')
print(json.dumps(delivery,indent=2))
