#!/usr/bin/env python3
"""Bounded own-Python RAM fixture only. Never launches/attaches an emulator."""
import argparse,ctypes,json,os,sys,time
from pathlib import Path
from fixture69f import Fixture
from scalar_priority69f import ScalarProcess,ScalarLatch,BufferedRows,observe_scalar,cadence_model
from observer69f import Coverage

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--base-plan',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
 if os.name!='nt':raise SystemExit('Native Windows ownprocess fixture only')
 if a.out.exists():raise SystemExit('Preserve previous fixture result')
 fixture=Fixture(a.base_plan);ram=(ctypes.c_ubyte*len(fixture.raw)).from_buffer(fixture.raw)
 proc=ScalarProcess(os.getpid(),Path(sys.executable));proc.ram=ctypes.addressof(ram)
 try:
  fixture.t.read=proc.read;latch=ScalarLatch(fixture.t,fixture.audit);buffer=BufferedRows();coverage=Coverage();cpu=time.process_time()
  result=observe_scalar(proc,latch,{'anchors':[{'address':0x8c100000,'hex':bytes(256).hex()}]},'.',.75,buffer.emit,coverage)
  result.update(own_observer_process_CPU_seconds=time.process_time()-cpu,identity='NATIVE_WINDOWS_OWN_PYTHON_RAM_FIXTURE_NOT_GAME_NOT_FLYCAST_NOT_CONSOLE',target_RAM_fixture_bytes=len(fixture.raw),source_binding_ELF=fixture.audit['exact_ELF_sha256'],clock_implementations={n:str(time.get_clock_info(n))for n in ['monotonic','perf_counter']},cadence_models={'legacy10ms':cadence_model(33000000,2000000,121,10000000),'new500us':cadence_model(33000000,2000000,121,500000)})
 finally:proc.close()
 with a.out.open('x')as f:json.dump(result,f,indent=2);f.write('\n')
 print(json.dumps({k:result[k]for k in ['polls','seconds','max_poll_gap_seconds','max_collection_seconds','own_observer_process_CPU_seconds','poll_gap_histogram']}))
if __name__=='__main__':main()
