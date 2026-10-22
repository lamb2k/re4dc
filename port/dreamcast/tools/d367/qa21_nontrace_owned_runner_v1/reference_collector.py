"""Real collector orchestration, injectable API for source-only fault tests.
A snapshot is never caller proof. Native handles/names/stats surround EVERY hash.
No runtime entrypoint or automatic adoption.
"""
import ntpath
from pathlib import PureWindowsPath
from native_reference_api import canonical

TRACKS=('track01.bin','track02.raw','track03.iso')


class Refusal(RuntimeError):pass


def identity(stat):
    return {k:stat[k] for k in ('volume','native_file_id','size','mtime_ns','allocated','links','attributes','deleted','directory')}


class Collector:
    def __init__(self,api,contract,declarations,guard):
        self.api=api;self.contract=contract;self.declarations=declarations;self.guard=guard
        self.cap=ntpath.dirname(contract['proposed_phase_rules']['staged_owned']['paths'][-1])
        self.source=ntpath.dirname(contract['image']['source_path']);self.handles={};self.dirs={};self.hold=False;self.receipts=[]

    def refuse(self,error):
        self.hold=True
        raise Refusal(str(error)) from error

    def parents(self,path):
        for parent in reversed(PureWindowsPath(path).parents):
            name=canonical(str(parent))
            if name not in self.dirs:self.dirs[name]=self.api.open_file(str(parent),directory=True)

    def handle(self,path,delete=False):
        key=canonical(path)
        if key not in self.handles:
            self.parents(path);self.handles[key]=self.api.open_file(path,delete=delete)
        return self.handles[key]

    def pin(self,path,stat,expected_links=None):
        name=ntpath.basename(path);decl=self.declarations['files'][name];pin=decl['references'][0]
        wanted=decl['native_file_id'].split()[-1].lower()
        if stat['native_file_id'].lower()!=wanted or (int(wanted,16)&((1<<64)-1))!=pin['inode']:
            raise Refusal('reviewed native ID/inode mismatch: '+path)
        if stat['size']!=pin['bytes'] or stat['mtime_ns']!=pin['mtime_ns'] or stat['deleted'] or stat['directory']:
            raise Refusal('reviewed size/mtime/type mismatch: '+path)
        if expected_links is not None and stat['links']!=expected_links:raise Refusal('exact link count mismatch: '+path)

    def snapshot(self,phase):
        rule=self.contract['proposed_phase_rules'][phase];wanted=sorted(canonical(p) for p in rule['paths'])
        native=self.api.names(self.contract['image']['source_path'])
        if native!=wanted:raise Refusal('full native image name set mismatch: '+phase)
        refs={}
        # Every declared ref has its own handle/path check; samefile is native volume+ID.
        for imagepath in rule['paths']:
            for name in TRACKS:
                path=ntpath.join(ntpath.dirname(imagepath),name);key=canonical(path)
                h=self.handle(path)  # READ-only during guest; no retained DELETE access
                if self.api.final_path(h)!=key:raise Refusal('retained reference path changed')
                stat=identity(self.api.stat(h));self.pin(path,stat,rule['expected_links'] if name=='track03.iso' else None)
                fresh=self.api.open_file(path)
                try:
                    if self.api.final_path(fresh)!=key or identity(self.api.stat(fresh))!=stat:
                        raise Refusal('current pathname no longer denotes retained alias')
                finally:self.api.close(fresh)
                refs[key]=stat
        for name in TRACKS:
            same=[v for k,v in refs.items() if ntpath.basename(k)==name]
            if any(v!=same[0] for v in same):raise Refusal('declared aliases are not exact same native file: '+name)
        return {'phase':phase,'names':native,'references':refs}

    def validate(self,phase,hash_all=True):
        if self.hold:raise Refusal('latched reference hold; no validation/cleanup')
        try:
            self.guard();before=self.snapshot(phase);hashes={}
            if hash_all:
                for name in TRACKS:
                    path=ntpath.join(self.source,name)
                    hashed=self.api.hash_file(self.handle(path),self.guard);decl=self.declarations['files'][name]
                    if hashed!={'sha256':decl['sha256'],'bytes':decl['references'][0]['bytes']}:
                        raise Refusal('full retained source hash mismatch: '+name)
                    hashes[name]=hashed
            self.guard();after=self.snapshot(phase)
            if before!=after:raise Refusal('native reference race across hashing: '+phase)
            result={'before':before,'hashes':hashes,'after':after};self.receipts.append(result);return result
        except BaseException as error:self.refuse(error)

    def cleanup(self,stop_proof):
        # stop_proof is executed HERE, not a caller-supplied Boolean or cached claim.
        if self.hold:raise Refusal('hold forbids removal of fourth reference')
        try:
            proof=stop_proof();self.validate('staged_owned');proof_after=stop_proof()
            if proof!=proof_after:raise Refusal('retained stop proof changed across cleanup hash')
            removed=[]
            for name in TRACKS: # Active image is LAST. Never enumerate/delete baseline links.
                stop_proof();self.guard();path=ntpath.join(self.cap,name);key=canonical(path)
                h=self.handles[key]
                if self.api.final_path(h)!=key:raise Refusal('cleanup exact opened alias changed')
                self.pin(path,self.api.stat(h),4 if name=='track03.iso' else None)
                # DELETE access is acquired ONLY after both guests are signaled and
                # job has just the inner. Holding DELETE access across guest launch
                # can conflict with ordinary ISO readers' share modes.
                deletion=self.api.open_file(path,delete=True)
                try:
                    if self.api.final_path(deletion)!=key or identity(self.api.stat(deletion))!=identity(self.api.stat(h)):
                        raise Refusal('cleanup DELETE handle differs from retained owned alias')
                except BaseException:
                    self.api.close(deletion);raise
                self.api.close(h);self.handles[key]=deletion
                self.api.delete_opened_link(deletion);del self.handles[key];removed.append(key)
            result=self.validate('post_clean');return {'removed_only_owned':removed,'stop_proof':proof_after,'post_clean':result}
        except BaseException as error:self.refuse(error)

    def close(self):
        # Closing readonly handles never unlinks; deliberate deletion is cleanup-only.
        errors=[]
        for table in (self.handles,self.dirs):
            for key,h in list(table.items()):
                try:self.api.close(h);del table[key]
                except BaseException as error:errors.append(str(error))
        if errors:raise RuntimeError('collector handles retained: '+'; '.join(errors))
