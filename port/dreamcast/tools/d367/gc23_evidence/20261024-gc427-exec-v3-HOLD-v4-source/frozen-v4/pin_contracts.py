"""Read-only exact source receipts for the I001 plan, no compiler or media."""
from pathlib import Path
import hashlib,json,subprocess
HERE=Path(__file__).resolve().parent
REPO='/root/work/lanes/gc23-evidence-tools'
def git(*argv):return subprocess.check_output(['git','-C',REPO,*argv])
def row(raw):return dict(size=len(raw),sha256=hashlib.sha256(raw).hexdigest())
if __name__=='__main__':
 sources={}
 paths=['port/dreamcast/game/gc_asset_gate.mk','port/dreamcast/game/platform/include/gc_asset_gate.h','port/dreamcast/game/platform/gc_asset_gate.cpp','port/dreamcast/game/platform/gc_asset_disc.cpp','port/dreamcast/game/platform/gc_asset_motion_unknown.cpp','port/dreamcast/game/platform/native_ui.cpp','port/dreamcast/game/platform/audio_aica.cpp','port/dreamcast/tools/d367/gc_port23/REMAINING-COVERAGE.md','port/dreamcast/tools/d367/gc_port23/MOTION-UNKNOWN24.md','port/dreamcast/tools/d367/gc_port23/LIFECYCLE.md','port/dreamcast/tools/d367/gc_port23/judge.py']
 for source in ['427784b1f48aa30742850bb5025925ab619b740e','c2f9ba8cbcebe30a218fe4fb6cf9ecd2305d853e']:
  sources[source]={p:dict(git_blob=git('rev-parse',source+':'+p).decode().strip(),**row(git('show',source+':'+p))) for p in paths}
 brief=HERE.parent.parent/'gc-port23/INBOX.md';status=HERE.parent.parent/'CODEX-TAKEOVER-STATUS.md'
 old=HERE.parent/'kos-budget-retest-guest-prep-v1'
 records=dict(source_pins=sources,original_I001_brief=dict(path=str(brief),identity=row(brief.read_bytes())),root_status_at_read=dict(path=str(status),identity=row(status.read_bytes())),V5_producer=dict(tool_source='c3dd19b999d3c36e76318a4d3825f8d1ca7310ec',seal=dict(path=str(HERE.parent.parent/'rain-diag24/qa-media-observer-ext4-v5/TOOLCHAIN-SEAL.json'),identity=row((HERE.parent.parent/'rain-diag24/qa-media-observer-ext4-v5/TOOLCHAIN-SEAL.json').read_bytes()))),unchanged_runtime_files={n:dict(predecessor=row((old/n).read_bytes()),successor=row((HERE/n).read_bytes())) for n in ['controller.py','post_slot.py','launch.py','windows_entry.py','owned_process.py','judge.py']},finish_callsite_receipt=git('grep','-n','re4dc_gcasset_finish','427784b1f48aa30742850bb5025925ab619b740e','--','port/dreamcast/game').decode().splitlines(),limits='Source-only plan; no new runtime, catalogue, allowance, SDK or guest authority')
 assert all(v['predecessor']==v['successor'] for v in records['unchanged_runtime_files'].values())
 with (HERE/'SOURCE-CONTRACT-PINS.json').open('x') as f:json.dump(records,f,indent=1);f.write('\n')
