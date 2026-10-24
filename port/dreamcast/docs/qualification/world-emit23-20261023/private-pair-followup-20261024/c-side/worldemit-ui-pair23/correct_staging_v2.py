from pathlib import Path
import hashlib,json
L=Path('/mnt/c/Game Dev/Emulators/codex-lanes/worldemit-ui-pair23')
E=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/world-emit23-takeover/49ad20f9')
sha=lambda b:hashlib.sha256(b).hexdigest()
old=L/'STAGING.md';oldb=old.read_bytes();sup=L/'STAGING-v1-B-m-SUPERSEDED.md'
with sup.open('xb') as f:f.write(oldb)
if sha(oldb)!='53ae85bf6889962a9e6e866bb7eb9274f298ec86f00b6ca77f993a5800346a5e':raise ValueError('unexpected prior staging bytes')
launch=E/'captures/B-mendez-r1/current-gate-launch.json';lb=launch.read_bytes();g=json.loads(lb)
assert g['unit']['source']=='49ad20f9932d638ddb7becf5db6f86b92e0a76a2' and g['unit']['profile']=='t'
assert g['unit']['output']=='/root/probe/lanes/route/out-we23B49adrT' and len(g['unit']['programme']['overlays'])==14
binding=dict(schema='MENDEZ_PRIVATE_PAIR_CONTROL_BINDING_V2',launch_path=str(launch),launch_sha256=sha(lb),
 unit=g['unit'],staged=g['staged'],fixtures=g['fixtures'],gate=g['gate'],tag=g['tag'],
 fresh_matched_control_required=True,notes='Preserved failing B-mendez-r1 uses B-t trace programme. B-m meter is a different programme and is not a matching control.')
bp=L/'CONTROL-B-t-BINDING.json';bp.write_text(json.dumps(binding,indent=2)+'\n')
s=oldb.decode('utf-8-sig').replace('current49ad B-m source/programme','current49ad B-t trace source/programme').replace('current49ad B-m twin-output directory','current49ad B-t trace twin-output directory').replace('original current B-m base','original current B-t base')
s=s.replace('The exact same Mendez fixture','The exact same Mendez fixture')
s=s.replace('5. When root separately allocates a guest, run the exact same Mendez fixture on baseline and private candidate,', '5. When root separately allocates a guest, run a FRESH matched B-t baseline control and private B-t candidate using the exact same Mendez fixture,')
s=s.replace('After independent source review', '''Control binding (authoritative actual run): captures/B-mendez-r1/current-gate-launch.json SHA25641a45bd36a778414938c0b43b373a140ee2862833b8c27751edc6dd62be435c1. Its frozen source is49ad20f9932d638ddb7becf5db6f86b92e0a76a2, armB/profilet, output /root/probe/lanes/route/out-we23B49adrT. Programme ELF da9d6a2ab97bc0850e25b3ee3c3cd27d7f69ed24a39f824211033705cb5e1965 (28800320B), staged main ab03d9d75d4e60e2dacdec6dbef3ac41fe15691784ab2281c238692a6d0425d9 (3407568B). CONTROL-B-t-BINDING.json preserves that complete actual unit, all14 overlay SHA/size rows, knobs/stack/recipe/manifests, staged media and exact fixture bindings. Revalidate ALL of those programme entries before staging; no B-m meter output substitution is permitted. Original B-t media SHA32a3616818c863270fbc86a0bc544b0696f905b0c01603c8ebaa035e728b3807 is preserved, not remastered in place.

The prior STAGING-v1-B-m-SUPERSEDED.md incorrectly named B-m; it is historical and MUST NOT be executed. Root confirmed no execution of that plan. CORRECTION-v2.json records the correction without changing the earlier candidate/source receipt.

Actual release pack check: PACK-ABSENCE.json binds the exact162154496B pack SHA5bba464a1175d8ebe153d5aecb629ea9637807c2bf4fc438a32c17148d0729da, validated7299-key index/CRC/order/extents, source49ad lookup algorithm and exact release/B-t manifests. Requested key is absent, so this unchanged pack cannot shadow the new loose pair. This read-only result does not replace staged-file readback or a fresh actual runtime load.

After independent source review''')
old.write_text(s)
record=dict(schema='MENDEZ_PAIR_STAGING_DOC_CORRECTION_V2',
 correction='B-mendez-r1 actual frozen programme is B-t trace, not B-m meter; stage candidate and fresh matched control with exact B-t unit/main/all14 overlays.',
 superseded=dict(path=str(sup),sha256=sha(oldb)),corrected=dict(path=str(old),sha256=sha(old.read_bytes())),
 actual_control_binding=dict(path=str(bp),sha256=sha(bp.read_bytes())),
 pack_absence=dict(path=str(L/'PACK-ABSENCE.json'),sha256=sha((L/'PACK-ABSENCE.json').read_bytes())),
 prior_candidate_receipt=dict(path=str(L/'RECEIPT.json'),sha256=sha((L/'RECEIPT.json').read_bytes()),unchanged=True),
 source_commit='67474ea4b1dd01b0d47e2f80c0e9b58103a7f86d',source_and_private_candidate_unchanged=True,
 obsolete_plan_executed=False,execution_statement_source='Parent root explicitly confirmed no execution of bad plan',
 actual_stage_or_guest=False)
cp=L/'CORRECTION-v2.json';cp.write_text(json.dumps(record,indent=2)+'\n')
print('STAGING',record['corrected']['sha256']);print('CONTROL',record['actual_control_binding']['sha256']);print('CORRECTION',sha(cp.read_bytes()))
