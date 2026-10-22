"""Concrete source-only parent wiring around exact505f backend. No entrypoint.
Only a future outer with an exact root allocation instantiates this class.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

P=Path(__file__).parent
HOOKS=P/'reference-hooks'
sys.path.insert(0,str(HOOKS))
from parent_reference_broker import Broker,allocation_proof
from native_reference_api import WindowsApi
spec=importlib.util.spec_from_file_location('frozen_505f_windows_backend',P/'windows-backend.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)

ALLOCATION=Path('C:/Game Dev/Emulators/codex-lanes/qa21-combined-regression/RETURN-DOOR-DOMAINS01-WIRING-ROOT-ALLOCATION.json')


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_authority(path,pin,tools_sha,cap,control):
    if Path(path)!=ALLOCATION:raise RuntimeError('only exact separate ROOT allocation path allowed')
    return allocation_proof(path,pin,cap,Path(control)/'reference-hooks',sha(HOOKS/'COLLECTOR_CONTRACT.json'),sha(HOOKS/'checkpoint_runner18.child.py'),tools_sha)


class WindowsBackend(base.WindowsBackend):
    def __init__(self,*args,allocation,allocation_sha256,tools_sha256,**kwargs):
        # Verify explicit root authority BEFORE binding native backend APIs.
        cap,control=args[:2]
        self.root_authority=validate_authority(allocation,allocation_sha256,tools_sha256,cap,control)
        self.allocation_path=Path(allocation);self.allocation_sha256=allocation_sha256;self.tools_sha256=tools_sha256
        self.reference_service=None;self.reference_history={'available':False,'reason':'reference service not started'}
        super().__init__(*args,**kwargs)

    def release(self,inner):
        if inner is not self.inner:raise RuntimeError('foreign retained inner release')
        # core.monitor has ALREADY armed the exact independent47s and cutoff threads.
        # Broker retains parent job authority; no job HANDLE is ever duplicated.
        self.reference_service=Broker(self,WindowsApi(),HOOKS/'COLLECTOR_CONTRACT.json',
            HOOKS/'retained-all-track-declarations.json',HOOKS/'checkpoint_runner18.child.py',
            self.tools_sha256,self.allocation_path,self.allocation_sha256,self.invocation/'reference-hooks')
        self.reference_service.start()
        context=self.invocation/'reference-hooks'/'context.json'
        descriptor={'context_path':str(context),'context_sha256':sha(context)}
        line=json.dumps(descriptor,sort_keys=True).encode('utf-8')+b'\n'
        if len(line)>4096:raise RuntimeError('owned context release payload too large')
        inner.stdin.write(b'owned-job-ready\n'+line);inner.stdin.flush();inner.stdin.close()

    def close_reference_service(self):
        service=self.reference_service
        if service is None:return
        # If stop/join fails, keep service/handles/job alive; no unsafe close fallthrough.
        try:service.close()
        except BaseException:
            service.hold=True;service.collector.hold=True
            raise
        self.reference_history={'available':True,'closed_after_join':True,'hold':service.hold,'stage':service.stage,
            'sequence':service.sequence,'records':service.records,'root_authority':service.authority,
            'scope':'actual broker operations; source/native/role qualification still separate'}
        self.reference_service=None

    def stop_deadlines(self):
        # Existing core calls this only after actual private-job-empty proof.
        self.close_reference_service()
        return super().stop_deadlines()

    def close_owned_handles(self,job,inner,guest):
        self.close_reference_service() # MUST precede every backend/process/job close.
        actual=self.guest
        if guest is not None and actual is not guest:raise RuntimeError('core/backend retained guest authority differs')
        # Broker can retain guest before flycast.pid/core.find_guest sees it. On
        # failure that actual HANDLE still requires closure even if core guest=None.
        return super().close_owned_handles(job,inner,actual)

    def reference_receipt(self):
        if self.reference_service is not None:raise RuntimeError('reference broker not closed; no completed receipt')
        return self.reference_history
