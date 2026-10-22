from pathlib import Path
import json,hashlib
L=Path(__file__).parent
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
s=(L/'run-controlled-ch32-door022.py').read_text()
assert sha(L/'run-controlled-ch32-door022.py')=='3849d7bf7b70f6931fe8ab241cb14de0eb3700342f72584e49ed4b526e4fd292'
s=s.replace('door022','escape023').replace('DOOR022','ESCAPE023').replace('allocated022','allocated023').replace('Controlled022','Controlled023').replace('exact021state','exact022state').replace('actual021state','actual022state').replace('Source-only exact022state already209/nativephysicalDoor1/original leader-cut continuation','Source-only exact022state originalAEV16 escape continuation')
s=s.replace("seed=D/'route-walk-controlled-ch32-door021/data'", "seed=D/'route-walk-controlled-ch32-door022/data'")
s=s.replace("L/'controlled022-OWNED-INPUT-CONTRACT.json'", "L/'controlled023-retained-AEV16-qualification.json'")
s=s.replace("for name,digest in protected.items():assert sha(D/name)==digest", "protected['route-walk-controlled-ch32-door022/data/disc.state']='b63e07f2ebb8be87be27e051d4580d28c878a0495348c5f99792ff2dcab4f16a'\nprotected['route-walk-controlled-ch32-door022/data/T0000_vmu_save_A1.bin']='425595f75b099a23789e09bbbd8fa4a3661072539644eae6051aa884943400b0'\nfor name,digest in protected.items():assert sha(D/name)==digest",1)
s=s.replace("allocation['allow_debug_goto_command_writes']is False", "allocation['allow_debug_goto_command_writes']is True").replace("allocation['allow_owned_window_focus']is True", "allocation['allow_owned_window_focus']is False").replace("allocation['allow_scan_code_SendInput']is True", "allocation['allow_scan_code_SendInput']is False").replace("allocation['exclusive_gui_input']is True", "allocation['exclusive_gui_input']is False").replace("allocation['maximum_successful_command_bytes']==0", "allocation['maximum_successful_command_bytes']==28").replace("allocation['write_allowlist']==[]", "allocation['write_allowlist']==[dict(address='0x8c47ff78',bytes=24),dict(address='0x8c47fff0',bytes=4)]")
s=s.replace("exclusive_gui_input_required=True", "exclusive_gui_input_required=False")
s=s.replace("assert not processes,'022 owned-focus unit requires no peer Flycast/GUI-input process; root must close QA and hold exclusive GUI-input lease'", "# Automatic area trigger performs no GUI focus or input; peer limits/accounting remain root-owned.")
s=s.replace("Exact zero-gamewrite/ordinaryinput allocation required", "Exact28B existingGoto-only/noGUI allocation required")
s=s.replace("print('Controlled023 closed; audit native209 physicalDoor1/originalleadercut independently')", "print('Controlled023 closed; audit originalAEV16 escape C/D/lift/return independently')")
# Keep inherited lineage text historical where it identifies preserved prior inputs,
# but make the new execution scope and acceptance concrete.
a=s.index("proof=dict(scope=");b=s.index("\n(D/(cap.name+'-preparation.json'))",a)
s=s[:a]+'''proof=dict(scope='CONTROLLED actual022 fullstate originalAEV16 escape. Existing position-onlyGoto slot3/currententry3 plus count4 LAST, exactly28Bmaximum; no max_entry/actor/HP/RSF/AI/outcome writes, no GUI/input, no build/fullcopy.',inputs=pins,argv=argv,fixture_sha256=sha(fixture),observer_sha256=sha(observer),supervisor_sha256=sha(guard),programme_binding_receipt_sha256=sha(D/'frozen-master-programme-binding-20261021.json'),environment={n:os.environ.get(n)for n in ['RE4DC_EMU','TRACE_SLOTS','TRACE_LOCK_OWNER']},admission_bytes=admission,runtime_floor_bytes=runtime,capture_cap_bytes=60*1024**2,raw_seconds=41,normal_close_seconds=39,absolute_seconds=47.5,global16=True,lane2=True,protected=protected,initial_process_inventory=processes,acceptance='Fresh advancing64nativeKeyneutral/idle/originalAEV16/code admission before28Bpublication. ActualoriginalCamC thenD/liftAC motion/originalRSF1/door51cc80000/eventreturn/advancingframes andPNGs independently. Originalcancel can shareflags; flagsalone notcomplete. Preserve actualdamage/partialstateatbound; no followingguest/retry/rollback.')''' +s[b:]
compile(s,'run-controlled-ch32-escape023.py','exec')
p=L/'run-controlled-ch32-escape023.py';assert not p.exists();p.write_text(s,newline='\n')
shell=(L/'run-controlled-ch32-door022.sh').read_text().replace('door022','escape023').replace('allocated022','allocated023')
ps=L/'run-controlled-ch32-escape023.sh';assert not ps.exists();ps.write_text(shell,newline='\n')
pins=json.loads((L/'controlled-ch32-door022-pins.json').read_text())
pins.pop(str(L/'observe-controlled-ch32-door022.py'))
pins[str(L/'observe-controlled-ch32-escape023.py')]=sha(L/'observe-controlled-ch32-escape023.py')
for p in [L/'controlled023-retained-AEV16-qualification.json',L.parent/'castle-controls21/r209-after022-live-overlay-proof.json',L.parent/'castle-controls21/r209-after022-exact-native-wrapper.json',L/'NEXT-CH32-SOURCE-CAPABILITY-20261022.json',L/'controlled-ch32-drain014-frozen-DWARF.json',L/'ACTUAL022-CLOSEOUT-REFERENCE.json']:
 pins[str(p)]=sha(p)
D=Path(r'C:\Flycast-Evidence\re4-dreamcast\castle18-20261018\Test21\recovered-j-content-20261021')
for name in ['disc.state','T0000_vmu_save_A1.bin']:
 p=D/'route-walk-controlled-ch32-door022/data'/name;pins[str(p)]=sha(p)
pp=L/'controlled-ch32-escape023-pins.json';assert not pp.exists();pp.write_text(json.dumps(pins,indent=2)+'\n',newline='\n')
print(json.dumps(dict(wrapper_sha256=sha(L/'run-controlled-ch32-escape023.py'),shell_sha256=sha(ps),pin_count=len(pins),pins_sha256=sha(pp))))
