"""Child hooks; default unconfigured. NO launches, native queries or entrypoint here.
The NEW child runner refuses before cap creation unless a future reviewed adapter
explicitly assigns a Proxy. Existing505f adapter still loads its original runner.
"""
import hashlib
import json
import os
from pathlib import Path
import threading
import time
from native_reference_api import canonical
from parent_reference_broker import atomic_new,PROFILE
from reference_collector import Refusal


class Proxy:
    def __init__(self,context_path,context_sha256,profile_path,clock=time.monotonic):
        self.context_path=Path(context_path);raw=self.context_path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=context_sha256:raise Refusal('parent context bytes differ')
        self.context=json.loads(raw);self.control=self.context_path.parent;self.clock=clock;self.origin=clock()
        profile_raw=Path(profile_path).read_bytes()
        if hashlib.sha256(profile_raw).hexdigest()!=PROFILE:raise Refusal('unchanged profile4c differs')
        self.profile=json.loads(profile_raw);self.sequence=0;self.hold=False;self.links=[];self.lock=threading.RLock()
        if self.context['inner_pid']!=os.getpid():raise Refusal('parent context belongs to another retained inner')
        self.cap=Path(self.context['cap'])

    def latch(self,error):
        self.hold=True
        # Failure marker creation is best-effort evidence, never required for HOLD.
        try:atomic_new(self.control/'REFERENCE-HOLD.json',{'error':str(error),'preserve_all_references':True})
        except BaseException:pass
        raise Refusal(str(error)) from error

    def request(self,event,payload):
        with self.lock:
            if self.hold:raise Refusal('latched child reference hold')
            try:
                self.sequence+=1;message={'nonce':self.context['nonce'],'sequence':self.sequence,'pid':os.getpid(),'event':event,'payload':payload}
                atomic_new(self.control/('request-%03d.json'%self.sequence),message)
                response_path=self.control/('response-%03d.json'%self.sequence)
                # Requests consume the SAME existing hard47s budget; no extra guest time.
                deadline=min(self.origin+47.0,self.clock()+10.0)
                while not response_path.exists():
                    if self.clock()>=deadline:raise Refusal('reference hook response deadline')
                    time.sleep(.01)
                response=json.loads(response_path.read_text())
                if response.get('ok') is not True:raise Refusal('parent refused: '+str(response.get('error')))
                if response.get('nonce')!=self.context['nonce'] or response.get('sequence')!=self.sequence or response.get('event')!=event:
                    raise Refusal('stale/foreign hook response')
                return response
            except BaseException as error:self.latch(error)

    def before_create(self,args,cap,runner):
        # Deliberately narrower child; production runner is preserved byteexact.
        if any(getattr(args,n,None) for n in ('base','warp','pad','w11','vmu','stop','align')):
            raise Refusal('unallocated runner mode/fixture option')
        role=next(r for r in self.profile['roles'] if r['name']=='return-door01')
        if args.keys!=role['keys'] or args.name!='return-door01' or args.seconds!=41 or args.period!=0:
            raise Refusal('exact return-door invocation mismatch')
        if args.syms.split()!=['0x3db360','0x3eb364','0x3eb360']:raise Refusal('exact c57 log symbol offsets differ')
        if canonical(str(cap))!=canonical(str(self.cap)) or cap.exists():raise Refusal('fixed fresh cap mismatch')
        runner_sha=hashlib.sha256(Path(runner).read_bytes()).hexdigest()
        if runner_sha!=self.context['runner_sha256']:raise Refusal('child runner source differs')
        return self.request('prelaunch',{'cap':canonical(str(cap)),'disc':canonical(args.disc),'runner_sha256':runner_sha,
                                        'seconds':args.seconds,'period':args.period,'name':args.name})

    def cap_created(self):
        # Exclusive metadata binds actual child creator/context; native parent
        # verifies and retains its file identity before accepting staged links.
        atomic_new(self.cap/'.owned-reference-creator.json',{
            'inner_pid':os.getpid(),'nonce':self.context['nonce'],
            'runner_sha256':self.context['runner_sha256'],
            'allocation_sha256':self.context['allocation_sha256']})

    def link_created(self,source,destination):
        # Called ONLY immediately AFTER os.link returned successfully in child runner.
        self.links.append({'source':canonical(str(source)),'destination':canonical(str(destination))})

    def staged(self):return self.request('staged',{'created_links':self.links})
    def before_spawn(self):return self.request('before_spawn',{})
    def guest_started(self,process):return self.request('guest',{'process':{'pid':process.pid,'remote_handle':int(process._handle)}})
    def reader_started(self,process):return self.request('reader',{'process':{'pid':process.pid,'remote_handle':int(process._handle)}})

    def cleanup(self,status):
        if self.hold:raise Refusal('refused attempt preserves newly staged fourth reference')
        return self.request('cleanup',{'run_status':status})
