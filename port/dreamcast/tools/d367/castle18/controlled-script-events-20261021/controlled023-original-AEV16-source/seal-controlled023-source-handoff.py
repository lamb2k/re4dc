from pathlib import Path
import hashlib,json,datetime,shutil,subprocess,sys
L=Path(__file__).parent;P=L.parent/'castle-controls21';sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
D=Path(r'C:\Flycast-Evidence\re4-dreamcast\castle18-20261018\Test21\recovered-j-content-20261021')
assert not(D/'route-walk-controlled-ch32-escape023').exists()
reviewpath=P/'review-source023-final-delta.json'
assert reviewpath.exists(),'Independent final source review required before seal'
review=json.loads(reviewpath.read_text())
observer=L/'observe-controlled-ch32-escape023.py';wrapper=L/'run-controlled-ch32-escape023.py';pinpath=L/'controlled-ch32-escape023-pins.json';proposal=L/'CONTROLLED023-SOURCE-LAUNCH-PROPOSAL.json'
identities=dict(observer=sha(observer),wrapper=sha(wrapper),pins=sha(pinpath),proposal=sha(proposal))
assert {name:sha(L/name)for name in review['sourcepins']}==review['sourcepins']
assert review['owner_case_receipt']['sha256']==sha(L/'controlled023-focused-source-cases.json')
assert identities==dict(observer='e2e802830868ae4ae0e56f72e8c09d2d5475d7cff29661df8373a9fa283e1c13',wrapper='651b4298adbc94df0055af54c703bb40380d4c61311e4a505f65be546bced834',pins='045f06552668fc5e9180cdee759ad5285b4a0f835f168dd5ee178b526a5c32c8',proposal='5c882b71d000fe2823416e8414089d6a7afc15559d82b3f3dbd906a7f7a50fa5')
pins=json.loads(pinpath.read_text())
for name,digest in pins.items():assert sha(Path(name))==digest,name
tests=json.loads((L/'controlled023-focused-source-cases.json').read_text());assert tests['case_count']==34 and all(c['passed']for c in tests['cases'])
archive=L/'controlled023-HISTORICAL-STATUS-BEFORE-SOURCE.md';assert not archive.exists();archive.write_bytes((L/'STATUS.md').read_bytes())
status='\n'.join(['Done: Source023 original AEV16 escape unit prepared; retained actual022 remains source6612/r209/HP1040,1440,600,600. No following guest allocated.','Doing now: Final source qualification and owned branch handoff; original callback/leader/idle/lift/area bound by independent read-only native proof.','Next: Root reviews exact source and fresh resources, then allocates one consolidated C/lift/D/native flags/event-return attempt. Full native PAD neutral required before 28B publication.','Blocked / Needs the user: none. No GUI/input, max_entry, actor, HP, AI, RSF or outcome writes; legitimate injury and all earlier states/VMUs preserved.','Last pushed: pending owned codex/castle22-source023 commit; observer e2e80283, wrapper 651b4298, pins 045f0655, proposal 5c882b71.'])+'\n'
(L/'STATUS.md').write_text(status,newline='\n')
files=['observe-controlled-ch32-escape023.py','run-controlled-ch32-escape023.py','run-controlled-ch32-escape023.sh','controlled-ch32-escape023-pins.json','CONTROLLED023-SOURCE-LAUNCH-PROPOSAL.json','controlled023-default-prepare.json','controlled023-focused-source-cases.json','controlled023-retained-AEV16-qualification.json','prepare-controlled023-source-unit.py','prepare-controlled023-wrapper.py','qualify-controlled023-retained-gates.py','finalize-controlled023-source.py','test-controlled023-source.py','controlled023-HISTORICAL-STATUS-BEFORE-SOURCE.md']
handback=dict(scope='SOURCE_ONLY originalAEV16 unit qualified, no actual event/guest/build/programme/image allocated.',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),branch='codex/castle22-source023',frozen_runtime_source='12a841d7cfe2c747266b0c330555557e651a4af0',ELF='4d823b496b9a402baadabe7f679c089fa0fd55c7ffd175ec634915745a11487f',raw='78fb06976cc394ec6e4cb7861046c24a15f82ddf7bcbf72e33',image='b67ac21eff8d819ef9ca5f0997b4c16401cb98a3d304feb65aa4b90f7affbeb6',identities=identities,pins_count=len(pins),all_pins_fresh=True,focused_cases=34,focused_receipt=sha(L/'controlled023-focused-source-cases.json'),old_broad_suites_not_repeated=True,independent_review=dict(path=str(reviewpath),sha256=sha(reviewpath)),original_gate_review=dict(path=str(P/'r209-after022-qualification-final.json'),sha256=sha(P/'r209-after022-qualification-final.json')),contract='Native old/on/trg ALL64bitszero on2freshcoherentadvancing samples; idle/current exact originalAEV16 polygon/callback/main code and inherited rig gating. ONE position-only existingGoto slot3/currententry3 descriptor24B plus count4 LAST4B; max_entry remains3. Engine owns done/position; original registered script owns isActive, C/lift/D/RSF1/door51cc/eventreturn. No keyboard/focus/SendInput API in observer. No no-peer exclusion: fresh global<16/lane<2 and exact root accounting remain.',next='Root exact reviewed allocation and fresh resources; one consolidated original event attempt, no retries/followingguest/earlycombatstop. Source qualification is not Flycast/hardware/audio/performance/release acceptance.',protected_status_sha256=sha(archive),resource=dict(source_metadata_git_mirror_unit_maximum_bytes=1048576,standing_peer_bytes=67108864,runtime_floor=19394461696,new_guest_build_programme_image_allocation=0),owned_files={n:sha(L/n)for n in files})
handback['raw']='78fb06976cc394ec6e4cb7861046c24a15f82ddf7bcb2fcbfd452d3fcbf72e33'
out=L/'ESCAPE023-SOURCE-QUALIFIED-HANDBACK.json';assert not out.exists();out.write_text(json.dumps(handback,indent=2)+'\n',newline='\n')
with(L/'HANDBACK.md').open('a')as f:f.write('\n\nSource023 original AEV16 source-only handoff on codex/castle22-source023. No guest allocated. See ESCAPE023-SOURCE-QUALIFIED-HANDBACK.json; observer '+identities['observer']+', pins '+identities['pins']+'. New focused34 cases and independent final source review; root actual allocation remains next.\n')
files+=['ESCAPE023-SOURCE-QUALIFIED-HANDBACK.json']
dest=Path(r'\\wsl.localhost\Ubuntu-24.04\root\probe\codex-castle18\port\dreamcast\tools\d367\castle18\controlled-script-events-20261021\controlled023-original-AEV16-source');assert not dest.exists();dest.mkdir()
for n in files:shutil.copyfile(L/n,dest/n)
(dest/'CURRENT-STATUS.md').write_text(status,newline='\n')
(dest/'review-source023-final-delta.json').write_bytes(reviewpath.read_bytes())
(dest/'.gitattributes').write_text('* -text\n',newline='\n')
physical_new=sum((L/n).stat().st_size for n in files)+sum(p.stat().st_size for p in dest.iterdir())
assert physical_new<700000
print(json.dumps(dict(handback=sha(out),mirror=str(dest),new_file_logical_bytes_before_Git=physical_new,maximum_unit_bytes=1048576,source=identities,no_guest=True)))
