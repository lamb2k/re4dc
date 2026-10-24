"""Grant-gated finite adapter. Default reads source pins ONLY, no scene input.
Only frozen ebfc reader may freshly authenticate the unchanged 75-case universe.
"""
import argparse
import collections
import dataclasses
import hashlib
import json
from pathlib import Path
import resource
import subprocess
import sys
import tempfile
import time
import types

# -B suppresses cache WRITES, not imports from an unchecked-hash .pyc.
# Authenticate and execute the SAME source bytes; never consult helper bytecache.
def _frozen_generic():
    path=Path(__file__).resolve().with_name('source_quad.py')
    raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!='2221649a8e347e567b4bf05d612ced71007db60a5678b01c95fc60ec61c4227f':
        raise ValueError('Frozen generic helper source hash changed')
    module=types.ModuleType('source_quad')
    module.__file__=str(path)
    sys.modules[module.__name__]=module # dataclass module identity before exec
    exec(compile(raw,module.__file__,'exec'),module.__dict__)
    return module

q=_frozen_generic()


GENERIC_SOURCE='975a976eb8888ee7ddc8a58c69e7b0907c89ea80'
GENERIC_REVIEW='8e4584e3a3a811b4d74f924529a299e3b2695d48d86135f0008b8762126e5cae'
READER_SOURCE='ebfc129bf010e4752494059468ed3ab04b7d315f'
PREPARATION_SOURCE='be113d594ed5c6b411d0fffaed84a61bcf4bff3f'
PLAN_SHA='24ef9acac6f1b616f832aa7a1cd36cce656cccb8ac51f4efa3e2f3e049bda324'
SEAL_SHA='786192cefc3309e10929fa33608f73133ee18f1cac94e021e8675909636f5ba6'
CONTROLS_SHA='4ffc4a2785c4ac26cff01941a54320c14a9fe9087455b6634aa7093181fafebc'
INPUT_CASES_SHA='fee71614fbf5bedd7e9a1c35cbb2d05edff5c119d1d8695560f43585f817ee8d'
PROFILE='SOURCE_QUAD24_ORIGINAL75_FIRST_NORMAL_V1'
POLICY='UNCHANGED_ORIGINALS_FULLPANELS_FIRST_SEEN_ONE_NORMAL_SIGN'
CAPS=(100000,12800000,2667,341376)
LIMITS=dict(candidate_attempts=CAPS[0],candidate_volume_upper=CAPS[1],final_original_checks=CAPS[2],final_volume_upper=CAPS[3],compute_seconds=115,wall_seconds=120,address_bytes=268435456,output_bytes=16777216,tail_bytes=65536,jobs=1)
GENERIC_PINS={'source_quad.py': '2221649a8e347e567b4bf05d612ced71007db60a5678b01c95fc60ec61c4227f', 'test_source_quad.py': '19bae47a41ee0d2849306a6f79ba6e050c5fe360bc9e6850c18ff100b38d29a0', 'README.md': 'f6d81653b8ecb131e939bed4ba4938391e1a567d462265542521ba17d02608d2'}
READER_PINS={'partition.py': 'f227a5bf26ae4d65ca97481f92d3e3220beee3cbbf6979cd8299ba1b827f0278', 'test_partition.py': 'c6a14d516e1fcf0a6ac5b2c1b1995bbabddb810112becff74bf0e1ba5f436191', 'prepare_private.py': '1ea2b8fe6bce38cef79982e99965179f180afe6a05b4fe6755143053b79af1ff', 'verify_private.py': 'ebac1f1d89ec0dccc3a6cd4c55ead210ade16dcf782ca3ec41f29b74cae5674e', 'test_preparation.py': 'c10f18797f25564ac582711f8c1bc1cc873316be1ca967b56c831e77a802256b', 'seal_private.py': 'bd1a1b052b48b7db46700baba99365131ebbe03066fb9a47dec61c1bbb5e244a', 'README.md': 'bba2d30b12f26473aaed2eae6f57570c7ab175b87ef91d4711f1aa8c7cd7eaad', 'PRIVATE-PREPARATION.md': '945cfc7aea5ce3f38b61047e0aba07f9af6244f104f692876191bd4ca70cd3e8', 'origin-before-helper-checkpoint.txt': '2521e0c5121485db437427b55cfbb02df70233cf492dbe609c6c06b79af0b809', 'runner.py': 'bbf860bb6b0627e467b3d7ab58d0feff16d0d08c6c37bdd7f2eee6e92f3c5f22', 'test_runner.py': '142563817da628ae3bc99e51ce3a5a845176cb9f08178387790d94f1aeebcddf', 'RUNNER.md': 'd64b726e45d47693c0c1e13a637514b8ed61094b2fbde0bfa5e7b3bc54e50884'}
OWNED=tuple(GENERIC_PINS)+('adapter.py','test_adapter.py','ADAPTER.md')


def token(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()


def pin(path):
    raw=Path(path).read_bytes()
    return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def require(path,sha):
    if pin(path)['sha256']!=sha:
        raise ValueError('Frozen input changed: '+str(path))


def own_sources(repo,source):
    if type(source)is not str or len(source)!=40 or any(c not in '0123456789abcdef' for c in source):
        raise ValueError('Exact adapter commit required')
    folder=Path(__file__).resolve().parent
    result={}
    for name in OWNED:
        path=folder/name;rel=path.relative_to(repo.resolve()).as_posix()
        raw=subprocess.check_output(['git','-C',str(repo),'show',source+':'+rel])
        if path.read_bytes()!=raw:
            raise ValueError('Adapter source changed: '+name)
        if name in GENERIC_PINS and hashlib.sha256(raw).hexdigest()!=GENERIC_PINS[name]:
            raise ValueError('Frozen generic source changed: '+name)
        result[name]=pin(path)
    return result


def load_reader(repo):
    """Verify public reader bytes before loading; called ONLY after authorization."""
    folder=repo/'port/dreamcast/tools/d367/triangle_partition24';raw={};pins={}
    for name,sha in READER_PINS.items():
        path=folder/name;rel=path.relative_to(repo.resolve()).as_posix()
        data=subprocess.check_output(['git','-C',str(repo),'show',READER_SOURCE+':'+rel])
        if hashlib.sha256(data).hexdigest()!=sha or path.read_bytes()!=data:
            raise ValueError('Frozen reader source changed: '+name)
        raw[name]=data;pins[name]=pin(path)
    def module(name,file):
        m=types.ModuleType(name);m.__file__=str(folder/file);sys.modules[name]=m
        exec(compile(raw[file],m.__file__,'exec'),m.__dict__)
        return m
    saved={name:sys.modules.get(name) for name in ('prepare_private','verify_private')}
    try:
        prep=module('quad24_frozen_prep','prepare_private.py');sys.modules['prepare_private']=prep
        verify=module('quad24_frozen_verify','verify_private.py');sys.modules['verify_private']=verify
        reader=module('quad24_frozen_reader','runner.py')
    finally:
        for name,previous in saved.items():
            if previous is None:sys.modules.pop(name,None)
            else:sys.modules[name]=previous
    return reader,pins


@dataclasses.dataclass(frozen=True)
class SourceMap:
    key: tuple
    face: object
    panel_index: object
    reason: object

@dataclasses.dataclass(frozen=True)
class Case:
    identifier: tuple
    inventory: q.Inventory
    eyes: q.EyeBox
    panels: tuple
    source_mappings: tuple
    input_case_fingerprint: str
    expected_fingerprint: str


def case_record(case):
    return (case.identifier,case.inventory.source_binding_sha256,case.inventory.expected_inventory_sha256,
            tuple((p.occurrence,p.indices,p.affine_sha256,p.vertices) for p in case.inventory.parents),
            (case.eyes.low,case.eyes.high,case.eyes.source_binding_sha256),
            tuple((p.identifier,p.record,p.source_binding_sha256,p.faces) for p in case.panels),
            tuple((s.key,s.face,s.panel_index,s.reason) for s in case.source_mappings),case.input_case_fingerprint)


def convert_case(old):
    """No L formation or coverage here. Preserve prebound inventory digest."""
    parents=tuple(q.Parent(p.occurrence,p.indices,p.affine_sha256,p.vertices) for p in old.inventory.parents)
    actual=q.inventory_digest(parents,old.inventory.source_binding_sha256)
    if type(actual)is not str or actual!=old.inventory.expected_inventory_sha256:
        raise ValueError('Original inventory serialization/binding mismatch')
    inventory=q.Inventory(parents,old.inventory.source_binding_sha256,old.inventory.expected_inventory_sha256)
    eyes=q.EyeBox(old.eye_box[0],old.eye_box[1],old.expected_fingerprint)
    panels=[];by_id={};by_record={};mappings=[];keys=set()
    for source in old.sources:
        if type(source.key)is not tuple or source.key in keys:
            raise ValueError('Complete ordered source keys required')
        keys.add(source.key)
        if source.reason:
            if source.fixed is not None:raise ValueError('Unrepresentable source supplied geometry')
            mappings.append(SourceMap(source.key,None,None,source.reason));continue
        oldpanel=source.fixed.panel
        if type(source.fixed.face)is not int or source.fixed.face not in (0,1):raise ValueError('Original source face')
        panel=q.PhysicalPanel(oldpanel.identifier,oldpanel.record,oldpanel.source_binding_sha256,oldpanel.faces)
        definition=(panel.record,panel.source_binding_sha256,panel.faces)
        if panel.identifier in by_id:
            index,previous=by_id[panel.identifier]
            if definition!=previous:raise ValueError('Full Panel ID alias')
        else:
            index=len(panels);by_id[panel.identifier]=(index,definition);panels.append(panel)
        if panel.record in by_record and by_record[panel.record]!=panel.identifier:
            raise ValueError('Full Panel record alias')
        by_record[panel.record]=panel.identifier
        mappings.append(SourceMap(source.key,source.fixed.face,index,None))
    if len(mappings)!=len(old.sources):raise ValueError('Source occurrence omitted')
    case=Case(old.identifier,inventory,eyes,tuple(panels),tuple(mappings),old.expected_fingerprint,'')
    return dataclasses.replace(case,expected_fingerprint=token(case_record(case)))


def bind_cases(reader_repo,prepared,ram):
    reader,pins=load_reader(reader_repo)
    original,cases,partition,modules=reader.bind(reader_repo,prepared,ram)
    if len(cases)!=75 or reader.prep.token([c.expected_fingerprint for c in cases])!=INPUT_CASES_SHA:
        raise ValueError('Unchanged authenticated75 cases required')
    if sum(len(c.inventory.parents) for c in cases)!=2667:
        raise ValueError('Complete original2667 occurrence census')
    converted=tuple(convert_case(c) for c in cases)
    return converted,dict(reader_sources=pins,frozen_reader_modules=modules,input_cases_sha256=INPUT_CASES_SHA,
                          converted_cases_sha256=token([c.expected_fingerprint for c in converted]),
                          original_occurrences=2667,source_occurrences=sum(len(c.source_mappings) for c in converted),
                          source_panel_occurrences=sum(len(c.panels) for c in converted))


def reservation(case):
    n=len(case.inventory.parents);s=len(case.panels)
    if not 1<=n<=q.MAX_PARENTS or type(s)is not int or s<0:
        raise ValueError('Finite complete wholecase required')
    return (n*s,128*n*s,n,128*n)


class Stop(Exception):pass
class CounterFault(Exception):pass

class Budget:
    def __init__(self,caps=CAPS,clock=time.monotonic,deadline=None):
        if type(caps)is not tuple or len(caps)!=4 or any(type(v)is not int or not 0<=v<=maximum for v,maximum in zip(caps,CAPS)):
            raise ValueError('Four bounded independent caps required')
        self.caps=caps;self.used=(0,0,0,0);self.active=None;self.clock=clock
        self.deadline=clock()+115 if deadline is None else deadline
    def check(self):
        if self.clock()>=self.deadline:raise Stop('UNKNOWN_WALL_BUDGET')
    def reserve(self,values):
        self.check()
        if self.active is not None:raise CounterFault('Nested case/refund before close')
        if type(values)is not tuple or len(values)!=4 or any(type(v)is not int or v<0 for v in values):
            raise CounterFault('Invalid complete reservation')
        if any(v>cap-used for v,cap,used in zip(values,self.caps,self.used)):return False
        self.active=[values,(0,0,0,0)];return True
    def take(self,values):
        self.check()
        if self.active is None or type(values)is not tuple or len(values)!=4 or any(type(v)is not int or v<0 for v in values):
            raise CounterFault('Invalid active work')
        if any(v>cap-used for v,cap,used in zip(values,self.active[0],self.active[1])):
            raise CounterFault('Wholecase work exceeded')
        self.active[1]=tuple(v+used for v,used in zip(values,self.active[1]));self.used=tuple(v+used for v,used in zip(values,self.used))
    def candidate(self):self.take((1,128,0,0))
    def final(self,n):self.take((0,0,n,128*n))
    def close(self):self.active=None
    def receipt(self):return dict(caps=self.caps,used=self.used,active_reservation=self.active,unused_refunded_only_after_case=True)


def make_assignment(panel,eyes):
    """ONE first-face normal sign per Panel/domain; no extra axis/search family."""
    try:
        limits=q.Limits();quad,definition=q._panel(panel,limits);ep=q._eyes(eyes,limits)
        normal=q._normal(definition[2][0],limits)
        for sign in (1,-1):
            functional=tuple(q._q(sign*x,limits) for x in normal)
            if min(q._dot(functional,e,limits) for e in ep)>max(q._dot(functional,s,limits) for s in quad):
                return q.Assignment(panel,functional,-sign)
        return q.Unknown('NO_FIXED_FIRST_NORMAL_DEPTH')
    except q._Refuse as error:return q.Unknown(str(error))
    except (MemoryError,OverflowError):return q.Unknown('MEMORY_ALLOCATION')


class Calls:
    def __init__(self):self.candidate_primitives=0;self.final_batches=0;self.certificate_formations=0


def solve(case,budget,calls):
    if token(case_record(case))!=case.expected_fingerprint:raise ValueError('Converted case drift')
    started=False;refusals=collections.Counter()
    try:
        if not budget.reserve(reservation(case)):return dict(status='UNTESTED_UNKNOWN_BUDGET',started=False)
        started=True;cache={};assignments=[];dependencies=set()
        for parent in case.inventory.parents:
            chosen=None
            for i,panel in enumerate(case.panels):
                budget.candidate() # includes/refunds no pre-reservation L or coverage work
                if i not in cache:
                    calls.certificate_formations+=1;cache[i]=make_assignment(panel,case.eyes);budget.check()
                assignment=cache[i]
                if type(assignment)is q.Unknown:
                    if assignment.reason=='MEMORY_ALLOCATION':raise Stop('UNKNOWN_MEMORY_ALLOCATION')
                    refusals[assignment.reason]+=1;continue
                calls.candidate_primitives+=1;answer=q.cover_triangle(case.eyes,parent,assignment);budget.check()
                if type(answer)is q.Unknown:
                    if answer.reason=='MEMORY_ALLOCATION':raise Stop('UNKNOWN_MEMORY_ALLOCATION')
                    refusals[answer.reason]+=1;continue
                if type(answer)is not q.TriangleOpportunity or answer.occurrence!=parent.occurrence or answer.panel!=panel.identifier or answer.volume_tests!=128 or answer.runtime_admitted is not False:
                    return dict(status='UNKNOWN_CANDIDATE_RESULT',started=True,partial_discarded=True)
                chosen=assignment;break
            if chosen is None:
                return dict(status='UNKNOWN_NO_FIXED_PANEL',started=True,first_uncovered_original=parent.occurrence[-1],partial_discarded=True,refusals=dict(refusals))
            dependencies.add(chosen.panel.identifier)
            if len(dependencies)>16:return dict(status='UNKNOWN_GLOBAL_PANEL_LIMIT',started=True,partial_discarded=True)
            assignments.append(chosen)
        if len(assignments)!=len(case.inventory.parents):raise CounterFault('Incomplete original assignment')
        budget.final(len(assignments));calls.final_batches+=1
        final=q.cover_assigned(case.inventory,case.eyes,tuple(assignments));budget.check()
        if type(final)is q.Unknown:return dict(status='UNKNOWN_FINAL_'+final.reason,started=True,partial_discarded=True)
        expected_records=tuple(sorted({a.panel.record for a in assignments}))
        if (type(final)is not q.AssignedOpportunity or final.inventory_sha256!=case.inventory.expected_inventory_sha256
            or final.original_occurrences!=tuple(p.occurrence for p in case.inventory.parents)
            or final.dependencies!=tuple(sorted(dependencies)) or final.physical_dependencies!=expected_records
            or len(final.triangles)!=len(assignments) or final.volume_tests!=128*len(assignments) or final.runtime_admitted is not False
            or any(type(t)is not q.TriangleOpportunity or t.occurrence!=p.occurrence or t.panel!=a.panel.identifier or t.volume_tests!=128 or t.runtime_admitted is not False for t,p,a in zip(final.triangles,case.inventory.parents,assignments))):
            return dict(status='UNKNOWN_FINAL_INCOMPLETE_RESULT',started=True,partial_discarded=True)
        return dict(status='NOMINAL_EXACT_REAL_OPPORTUNITY_ONLY',started=True,complete_originals=len(assignments),
                    inventory_sha256=final.inventory_sha256,input_sha256=final.input_sha256,dependencies=final.dependencies,
                    physical_dependencies=final.physical_dependencies,
                    assignments=[dict(original=p.occurrence,panel=a.panel.identifier,L=[str(x) for x in a.functional],orientation=a.orientation) for p,a in zip(case.inventory.parents,assignments)],
                    minimum_margins=dict(eye_source=str(min(t.minimum_eye_source_gap for t in final.triangles)),source_target=str(min(t.minimum_source_target_gap for t in final.triangles)),convex=str(min(t.minimum_convex_volume for t in final.triangles)),outer=str(min(t.minimum_outer_volume for t in final.triangles))),refusals=dict(refusals),runtime_admitted=False)
    except Stop as error:return dict(status=str(error),started=started,partial_discarded=True)
    except CounterFault:return dict(status='UNKNOWN_COUNTER_BUDGET',started=started,partial_discarded=True)
    except (MemoryError,OverflowError):return dict(status='UNKNOWN_MEMORY_ALLOCATION',started=started,partial_discarded=True)
    finally:
        if started:budget.close()


def execute(cases,budget,calls):
    rows=[];halt=None
    for case in cases:
        before=budget.used
        if halt:answer=dict(status=halt,started=False)
        else:
            try:answer=solve(case,budget,calls)
            except (MemoryError,OverflowError):answer=dict(status='UNKNOWN_MEMORY_ALLOCATION',started=False,partial_discarded=True)
            if answer['status'] in ('UNTESTED_UNKNOWN_BUDGET','UNKNOWN_WALL_BUDGET','UNKNOWN_COUNTER_BUDGET','UNKNOWN_MEMORY_ALLOCATION','UNKNOWN_FINAL_MEMORY_ALLOCATION'):halt=answer['status']
        rows.append(dict(case=case.identifier,input_case_fingerprint=case.input_case_fingerprint,case_fingerprint=case.expected_fingerprint,**answer,candidate_attempts=budget.used[0]-before[0],candidate_volume_upper=budget.used[1]-before[1],final_original_checks=budget.used[2]-before[2],final_volume_upper=budget.used[3]-before[3]))
    return rows


def grant_binding(source,review_sha,reader_repo,prepared,out):
    return dict(issuer='/root',approved=True,scope='SOURCE_QUAD24_PRIVATE_ORIGINAL75_ONLY',profile=PROFILE,policy=POLICY,
                adapter_source=source,review_sha256=review_sha,generic_source=GENERIC_SOURCE,generic_review_sha256=GENERIC_REVIEW,
                reader_source=READER_SOURCE,preparation_source=PREPARATION_SOURCE,plan_sha256=PLAN_SHA,seal_sha256=SEAL_SHA,controls_sha256=CONTROLS_SHA,
                input_cases_sha256=INPUT_CASES_SHA,case_count=75,original_occurrences=2667,limits=LIMITS,
                reader_repo=str(reader_repo.resolve()),prepared_directory=str(prepared.resolve()),output=str(out.resolve()),new_rays=0,ledger_accesses=0,runtime_admitted=False)


def authorize(grant,grant_sha,review,review_sha,source,reader_repo,prepared,out):
    if any(v is None for v in (grant,grant_sha,review,review_sha)):
        raise ValueError('Execute requires separately pinned root grant and source review')
    require(grant,grant_sha);require(review,review_sha)
    if json.loads(grant.read_text())!=grant_binding(source,review_sha,reader_repo,prepared,out):
        raise ValueError('Root grant source/profile/cases/caps/path/review mismatch')
    return dict(grant=pin(grant),review=pin(review))


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo',type=Path,required=True);ap.add_argument('--expected-source',required=True)
    ap.add_argument('--reader-repo',type=Path,required=True);ap.add_argument('--prepared-directory',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--execute',action='store_true');ap.add_argument('--grant',type=Path);ap.add_argument('--grant-sha256');ap.add_argument('--review',type=Path);ap.add_argument('--review-sha256')
    a=ap.parse_args();start=time.monotonic();resource.setrlimit(resource.RLIMIT_AS,(LIMITS['address_bytes'],)*2)
    if a.out.exists() or any(a.out.resolve().is_relative_to(p.resolve()) for p in (a.repo,a.reader_repo,a.prepared_directory)):
        raise ValueError('Fresh external output outside all preserved roots required')
    sources=own_sources(a.repo,a.expected_source)
    result=dict(classification='HELD_SOURCE_ONLY_NO_PRIVATE_INPUTS_OR_PREDICATES',source=a.expected_source,profile=PROFILE,policy=POLICY,
                owned_sources=sources,limits=LIMITS,grant_template=grant_binding(a.expected_source,'<independent-adapter-review-sha256>',a.reader_repo,a.prepared_directory,a.out),
                private_reader_invocations=0,candidate_primitives=0,final_batches=0,certificate_formations=0,input_cases_sha256=INPUT_CASES_SHA,
                input_authentication='NOT_RUN',other9600_cases='UNTESTED_UNKNOWN',new_rays=0,ledger_accesses=0,runtime_admitted=False,numeric_raster_current_source_receipts='UNQUALIFIED')
    if a.execute:
        result['authorization']=authorize(a.grant,a.grant_sha256,a.review,a.review_sha256,a.expected_source,a.reader_repo,a.prepared_directory,a.out)
        with tempfile.TemporaryDirectory(prefix='source-quad24-',dir='/dev/shm') as temporary:
            result['private_reader_invocations']=1;cases,binding=bind_cases(a.reader_repo,a.prepared_directory,Path(temporary))
            budget=Budget(deadline=start+115);calls=Calls()
            result.update(classification='NOMINAL_EXACT_REAL_SEARCH_NO_RUNTIME_CERTIFICATE',input_authentication='FROZEN_EBFC_FRESH_BIND',binding=binding,
                          plan=[dict(case=c.identifier,originals=len(c.inventory.parents),full_panels=len(c.panels),source_mappings=[dataclasses.asdict(s) for s in c.source_mappings],reservation=reservation(c),case_fingerprint=c.expected_fingerprint) for c in cases],
                          results=execute(cases,budget,calls),work=budget.receipt())
            result.update(candidate_primitives=calls.candidate_primitives,final_batches=calls.final_batches,certificate_formations=calls.certificate_formations)
    result['seconds']=time.monotonic()-start;result['peak_rss_kib']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    raw=(json.dumps(result,indent=1,default=str)+'\n').encode()
    if len(raw)+LIMITS['tail_bytes']>LIMITS['output_bytes'] or time.monotonic()-start>=LIMITS['wall_seconds']:
        raise ValueError('Output/wall cap; no result published')
    a.out.mkdir();(a.out/'report.json').write_bytes(raw)
    print(json.dumps(dict(classification=result['classification'],report=pin(a.out/'report.json'),seconds=result['seconds'],candidate_primitives=result['candidate_primitives'],final_batches=result['final_batches'])),flush=True)

if __name__=='__main__':main()
