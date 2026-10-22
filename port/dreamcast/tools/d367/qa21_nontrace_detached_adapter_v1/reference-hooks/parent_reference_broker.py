"""Parent-owned concrete hook service. NO entrypoint, launch or auto-adoption.
The existing505f private job/hardstop remain solely in the parent. A future reviewed
outer adapter must construct/start this service AFTER arming deadlines, BEFORE release.
No job HANDLE is duplicated or transmitted into the child.
"""
import hashlib
import json
import ntpath
import os
from pathlib import Path
import secrets
import threading
import time
from native_reference_api import canonical
from reference_collector import Collector,Refusal

PROFILE='4c386fa2fd826d2b04f7bf5b8696dca3e339dd92485c11b8ec91b863d21ce99b'
SOURCE='505f3ee487a1bb658199986f4988fdf14008c960'


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def atomic_new(path,value):
    path=Path(path);pending=path.with_name(path.name+'.pending')
    with pending.open('x',encoding='utf-8') as f:json.dump(value,f,sort_keys=True)
    if path.exists():raise Refusal('IPC destination already exists')
    os.replace(pending,path)


def allocation_proof(path,sha,cap,control,contract_sha,runner_sha,tools_sha):
    # Values originate in a NEW immutable future seal, never a request Boolean.
    if not sha or len(sha)!=64 or not tools_sha or len(tools_sha)!=64:raise Refusal('missing exact allocation/tools pins')
    raw=Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=sha:raise Refusal('root allocation bytes changed')
    data=json.loads(raw)
    expected={'profile_sha256':PROFILE,'tools_sha256':tools_sha,'contract_sha256':contract_sha,
              'runner_sha256':runner_sha,'tools_source':SOURCE,'semantic_mode':'return-door01',
              'cap':canonical(cap),'control':canonical(control),'attempt_limit':1,
              'inner_seconds':41,'input_cutoff_seconds':40.75,'private_job_seconds':47.0,
              'absolute_actual_seconds':47.5,'evidence_cap_bytes':60000000,'runtime_floor_bytes':19394461696}
    if set(data)!=set(expected) or any(type(data[k]) is not type(v) or data[k]!=v for k,v in expected.items()):raise Refusal('root allocation schema/types/exact pins differ; no allocation inferred')
    return {'path':str(path),'sha256':sha,'contents':data}


class Broker:
    def __init__(self,backend,api,contract_path,declarations_path,runner_path,tools_sha,
                 allocation_path,allocation_sha,control):
        self.backend=backend;self.api=api;self.control=Path(control);self.contract_path=Path(contract_path)
        self.contract=json.loads(self.contract_path.read_text());self.cap=Path(self.contract['proposed_phase_rules']['staged_owned']['paths'][-1]).parent
        expected_invocation=self.cap.parent/self.contract['new_output_contract_proposal']['control_name']
        if canonical(str(self.control))!=canonical(str(expected_invocation/'reference-hooks')):
            raise Refusal('wrong exact child hook control output')
        if canonical(str(backend.invocation))!=canonical(str(expected_invocation)) or canonical(str(backend.cap))!=canonical(str(self.cap)):
            raise Refusal('broker metadata not charged under exact existing backend cap/control')
        self.runner=Path(runner_path);self.tools_sha=tools_sha;self.job=backend.job;self.marker_handle=None
        self.contract_sha=digest(self.contract_path);self.runner_sha=digest(self.runner)
        self.authority=allocation_proof(allocation_path,allocation_sha,self.cap,self.control,self.contract_sha,self.runner_sha,tools_sha)
        self.inner=backend.inner
        if self.job is None or self.inner is None:raise Refusal('no actual owned parent job/inner')
        if any(t is None or not t.is_alive() for t in (backend.deadline_thread,backend.cutoff_thread)):
            raise Refusal('existing independent deadline threads not armed')
        self.inner_pin=dict(backend.inner_identity);self.inner_pin['path']=canonical(self.inner_pin['path'])
        self.records={};self.reader=None;self.guest=None;self.hold=False;self.stage='new';self.sequence=0;self.stop=threading.Event();self.thread=None
        self.nonce=secrets.token_hex(32);self.collector=Collector(api,self.contract,json.loads(Path(declarations_path).read_text()),self.resource_guard)

    def resource_guard(self):
        self.backend.check_deadlines()
        if self.backend.job!=self.job:raise Refusal('parent job authority changed')
        if self.backend.free()<19394461696:raise Refusal('unchanged runtime disk floor')
        if self.backend.evidence_bytes()>=60000000:raise Refusal('unchanged cumulative evidence cap')
        # Every chunk also checks retained live inner, including process birth.
        self.api.process(int(self.inner._handle),self.job,self.inner_pin,require_live=True)

    def inner_proof(self):
        self.resource_guard();proof=self.api.process(int(self.inner._handle),self.job,self.inner_pin,require_live=True)
        if self.backend.global_count()>16:raise Refusal('unchanged global guest limit')
        pids=self.api.job_pids(self.job)
        allowed={self.inner.pid}|{x['pin']['pid'] for x in (self.guest,self.reader) if x is not None}
        if self.inner.pid not in pids or set(pids)-allowed:raise Refusal('unexpected/missing private job member')
        return {'inner':proof,'job_pids':pids,'allocation':self.authority}

    def fail(self,error):
        self.hold=True;self.collector.hold=True
        # Stop uses only the existing captured owned private job, never a name/PID search.
        try:self.backend.stop_private_job(self.job)
        except BaseException as stop_error:error=RuntimeError(str(error)+'; owned stop failure: '+str(stop_error))
        return {'ok':False,'hold':True,'error':type(error).__name__+': '+str(error),'preserve_all_references':True}

    def retain_remote(self,payload,kind):
        if not isinstance(payload,dict) or set(payload)!={'process'}:raise Refusal('unexpected process proof payload')
        value=payload.get('process')
        if not isinstance(value,dict) or set(value)!={'pid','remote_handle'}:raise Refusal('missing actual child process handle')
        if type(value['pid']) is not int or type(value['remote_handle']) is not int or value['pid']<=0 or value['remote_handle']<=0:
            raise Refusal('invalid child process handle numbers')
        handle=self.api.duplicate(int(self.inner._handle),value['remote_handle'])
        try:
            proof=self.api.process(handle,self.job,require_live=True)
            if proof['pid']!=value['pid']:raise Refusal('Popen handle does not match child PID')
            expected=canonical(str(self.cap/'flycast.exe')) if kind=='guest' else self.inner_pin['path']
            if proof['path']!=expected:raise Refusal('actual guest/reader executable path mismatch')
            pin={k:proof[k] for k in ('pid','start_filetime','path')}
            if kind=='guest':
                if self.backend.guest is not None:raise Refusal('guest was acquired before staged/live proof')
                if digest(self.cap/'flycast.exe')!=self.backend.emu_sha:raise Refusal('guest executable hash differs')
                age=(self.api.now_filetime()-pin['start_filetime'])/1e7
                if age<0 or age>47.5:raise Refusal('actual process birth outside unchanged deadline')
                # Ownership transferred to EXISTING backend; existing deadline/release/final
                # telemetry code and final closure use this exact retained handle.
                self.backend.guest={'pid':pin['pid'],'handle':handle,'identity':pin,'anchor':self.backend.clock()-age}
            return {'handle':handle,'pin':pin,'live_proof':proof}
        except BaseException:self.api.close(handle);raise

    def marker_proof(self):
        path=self.cap/'.owned-reference-creator.json';key=canonical(str(path))
        expected={'inner_pid':self.inner.pid,'nonce':self.nonce,'runner_sha256':self.runner_sha,'allocation_sha256':self.authority['sha256']}
        raw=json.dumps(expected,sort_keys=True).encode('utf-8')
        wanted={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
        if self.marker_handle is None:
            self.collector.parents(str(path));self.marker_handle=self.api.open_file(str(path))
            # Pin original creator identity once. Never reseal a replacement alias.
            self.marker_original=self.api.stat(self.marker_handle)
        def current():
            retained=self.api.stat(self.marker_handle)
            if retained['deleted'] or retained['directory'] or retained['creation_filetime']<=0 or retained!=self.marker_original or self.api.final_path(self.marker_handle)!=key:
                raise Refusal('retained creator marker identity/type/path changed')
            fresh=self.api.open_file(str(path))
            try:
                now=self.api.stat(fresh)
                if now['deleted'] or now['directory'] or self.api.final_path(fresh)!=key or now!=self.marker_original:
                    raise Refusal('current creator marker alias differs from original retained identity')
                # Fresh pathname and original retained object must BOTH contain the
                # exact creator data, around every operation; no request Boolean.
                hashed=self.api.hash_file(fresh,self.resource_guard)
                if hashed!=wanted:raise Refusal('current creator marker contents differ')
                after=self.api.stat(fresh)
                if after!=now or after['deleted'] or after['directory'] or self.api.final_path(fresh)!=key:
                    raise Refusal('current creator marker changed during hash')
                # Re-open the pathname AFTER hashing as well. The retained handle
                # can still name a removed/renamed object when DELETE sharing allows
                # a replacement at its old pathname.
                post=self.api.open_file(str(path))
                try:
                    poststat=self.api.stat(post)
                    if poststat!=self.marker_original or poststat['deleted'] or poststat['directory'] or self.api.final_path(post)!=key:
                        raise Refusal('creator marker current pathname changed after operation')
                finally:self.api.close(post)
                return after
            finally:self.api.close(fresh)
        before=current();hashed=self.api.hash_file(self.marker_handle,self.resource_guard)
        if hashed!=wanted:raise Refusal('original retained creator marker contents differ')
        after=current()
        if before!=after or self.api.stat(self.marker_handle)!=self.marker_original or self.api.final_path(self.marker_handle)!=key:
            raise Refusal('creator marker alias/retained identity changed across operation')
        return {'native_identity':after,'hash':hashed,'exact_contents':expected}

    def stopped(self):
        self.inner_proof();out={}
        if self.guest is None or self.reader is None:raise Refusal('no complete retained process lineage; preserve partial')
        for kind,value in (('guest',self.guest),('reader',self.reader)):
            proof=self.api.process(value['handle'],self.job,value['pin'])
            if proof['phase']!='exited' or not proof['exit_filetime'] or proof['wait_status']!=0:raise Refusal('cleanup requires signaled retained '+kind)
            out[kind]=proof
        if self.api.job_pids(self.job)!=[self.inner.pid]:raise Refusal('cleanup private job not exclusively current inner')
        out['inner']=self.inner_pin;out['allocation_sha256']=self.authority['sha256'];return out

    def dispatch(self,message):
        try:
            if self.hold:raise Refusal('latched broker hold')
            if set(message)!={'nonce','sequence','pid','event','payload'} or message['nonce']!=self.nonce or type(message['sequence']) is not int or message['sequence']!=self.sequence+1 or type(message['pid']) is not int or message['pid']!=self.inner.pid:
                raise Refusal('stale/foreign/invalid hook request')
            self.sequence+=1;event=message['event'];payload=message['payload']
            # The new member is accepted ONLY by duplicating its actual retained Popen
            # HANDLE before job enumeration. A request PID alone is never an exception.
            if event=='guest' and self.stage=='ready':self.guest=self.retain_remote(payload,'guest')
            elif event=='reader' and self.stage=='guest':self.reader=self.retain_remote(payload,'reader')
            proof=self.inner_proof()
            if event=='prelaunch' and self.stage=='new':
                expected={'cap':canonical(str(self.cap)),'disc':canonical(self.collector.source),'runner_sha256':self.runner_sha,
                          'seconds':41,'period':0,'name':'return-door01'}
                if payload!=expected:raise Refusal('runner invocation differs from exact child contract')
                if self.cap.exists():raise Refusal('new cap already exists')
                result=self.collector.validate('prelaunch');self.stage='prelaunch'
            elif event=='staged' and self.stage=='prelaunch':
                expected=[{'source':canonical(ntpath.join(self.collector.source,n)),'destination':canonical(str(self.cap/n))} for n in ('track01.bin','track02.raw','track03.iso')]
                if payload!={'created_links':expected}:raise Refusal('actual runner creation ledger differs')
                marker=self.marker_proof();result=self.collector.validate('staged_owned')
                if marker!=self.marker_proof():raise Refusal('creator marker changed across stage hash')
                result={'references':result,'creator':marker};self.stage='staged'
            elif event=='before_spawn' and self.stage=='staged':
                if payload:raise Refusal('unexpected before_spawn data')
                result=self.collector.validate('staged_owned');self.stage='ready'
            elif event=='guest' and self.stage=='ready':
                result=self.collector.validate('live_owned');self.stage='guest'
                result={'references':result,'guest':self.api.process(self.guest['handle'],self.job,self.guest['pin'],require_live=True)}
            elif event=='reader' and self.stage=='guest':
                result=self.collector.validate('live_owned');self.stage='live'
                result={'references':result,'guest':self.api.process(self.guest['handle'],self.job,self.guest['pin'],require_live=True),'reader':self.api.process(self.reader['handle'],self.job,self.reader['pin'],require_live=True)}
            elif event=='cleanup' and self.stage=='live':
                if payload!={'run_status':'RUN_COMPLETE'}:raise Refusal('failed run preserves current references')
                result=self.collector.cleanup(self.stopped);self.stage='cleaned'
            else:raise Refusal('invalid hook lifecycle: '+event+'/'+self.stage)
            response={'ok':True,'nonce':self.nonce,'sequence':self.sequence,'event':event,'native_proof':proof,'result':result}
            self.records[self.sequence]=response;return response
        except BaseException as error:return self.fail(error)

    def start(self):
        if self.control.resolve()!=self.control.absolute() or self.control.exists():raise Refusal('new control exists/ancestor alias')
        # Parent must create this fresh control before inner release. No cap/image write.
        self.control.mkdir(parents=False);self.inner_proof()
        atomic_new(self.control/'context.json',{'nonce':self.nonce,'inner_pid':self.inner.pid,'cap':str(self.cap),
                 'contract_sha256':self.contract_sha,'runner_sha256':self.runner_sha,'tools_sha256':self.tools_sha,
                 'allocation_sha256':self.authority['sha256']})
        def serve():
            while not self.stop.wait(.01):
                seq=self.sequence+1;path=self.control/('request-%03d.json'%seq)
                if not path.exists():continue
                try:response=self.dispatch(json.loads(path.read_text()))
                except BaseException as error:response=self.fail(error)
                try:atomic_new(self.control/('response-%03d.json'%seq),response)
                except BaseException as error:self.fail(error);return
                if self.hold:return
        self.thread=threading.Thread(target=serve,name='owned-reference-broker',daemon=True);self.thread.start()

    def close(self):
        self.stop.set()
        if self.thread is not None:
            self.thread.join(timeout=2)
            if self.thread.is_alive():raise Refusal('broker still live; retain all handles and parent job authority')
        self.collector.close()
        if self.marker_handle is not None:self.api.close(self.marker_handle);self.marker_handle=None
        if self.reader is not None:self.api.close(self.reader['handle']);self.reader=None
        # guest handle remains backend-owned, closed by unchanged505f lifecycle.
