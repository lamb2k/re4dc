"""Finite original-triangle adapter. DEFAULT SOURCE ONLY; fresh root grant required.
No cost extraction, new discovery, builder, runtime/data/schema path or rays.
"""
import argparse
import dataclasses
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import tempfile
import time
import types

F7='f7fb7da46359694262b84cb78a3a7dfa4fc0fa4a'
CHUNKS='8644f59d271ab0a1ab1cc40761c9883374980b6d'
# Exact source hashes, not bytecache identity.
PIN_A='083c2dd804a82ed49804a8baeb186857cb901eb6e247703962cadc6b749821ab'
PIN_C='0ce22907cf912417e12b76568432604a84525732d7a40be720a9e3c4337f0a16'
CHUNKS_REVIEW='a9954d511a2be908df0dcd6d9a5b2431db6b7cf60fed1ddf4654559c0895734c'
EXPOSURE_SHA='22b2fe4dc83c0a0ba846eefb822fe1dead4bbbaa850b1e838dc5eaaadc56d57c'

def load(name, file, sha):
    path=Path(__file__).resolve().with_name(file);raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=sha:raise ValueError('PINNED_SOURCE_DRIFT '+file)
    module=types.ModuleType(name);module.__file__=str(path);sys.modules[name]=module
    exec(compile(raw,module.__file__,'exec'),module.__dict__)
    return module

a=load('original_chunks_frozen_f7','adapter.py',PIN_A)
c=load('original_chunks_reviewed','original_chunks.py',PIN_C)
q=c.q
PROFILE='SOURCE_QUAD24_ORIGINAL_TRIANGLE_PARTITIONS_FINITE75_V1'
POLICY='ALL_ORIGINALS_FIXED_FIRST_NORMAL_COMPLETE_DRAW_PARTITION'
CAPS=c.CAPS
LIMITS=dict(candidate_attempts=CAPS[0],candidate_volume_upper=CAPS[1],final_original_checks=CAPS[2],final_volume_upper=CAPS[3],
            compute_seconds=115,wall_seconds=120,address_bytes=268435456,output_bytes=16777216,tail_bytes=65536,jobs=1,numeric_threads=1)
OWN=('original_chunks_adapter.py','test_original_chunks_adapter.py','CHUNKS-ADAPTER.md')

class Halt(Exception):pass

def check(deadline,clock=time.monotonic):
    if clock()>=deadline:raise Halt('UNKNOWN_WALL_BUDGET')

def bridge(old):
    """Module q classes differ: copy exact data and MATCH original prebound digest."""
    if a.token(a.case_record(old))!=old.expected_fingerprint:raise ValueError('CASE_FINGERPRINT')
    parents=tuple(q.Parent(p.occurrence,p.indices,p.affine_sha256,p.vertices) for p in old.inventory.parents)
    actual=q.inventory_digest(parents,old.inventory.source_binding_sha256)
    if type(actual)is not str or actual!=old.inventory.expected_inventory_sha256:raise ValueError('ORIGINAL_INVENTORY_SERIALIZATION')
    inv=q.Inventory(parents,old.inventory.source_binding_sha256,old.inventory.expected_inventory_sha256)
    eyes=q.EyeBox(old.eyes.low,old.eyes.high,old.eyes.source_binding_sha256)
    panels=tuple(q.PhysicalPanel(p.identifier,p.record,p.source_binding_sha256,p.faces) for p in old.panels)
    copied=dataclasses.replace(old,inventory=inv,eyes=eyes,panels=panels)
    if a.case_record(copied)!=a.case_record(old) or a.token(a.case_record(copied))!=old.expected_fingerprint:
        raise ValueError('UNCHANGED_COMPLETE_CASE_SERIALIZATION')
    return copied

def universe(cases):
    if type(cases)is not tuple or len(cases)!=75 or sum(len(x.inventory.parents) for x in cases)!=2667:
        raise ValueError('EXACT75_COMPLETE2667')
    if tuple(sum(a.reservation(x)[i] for x in cases) for i in range(4))!=CAPS:
        raise ValueError('EXACT_NEW_EXHAUSTIVE_PLAN')
    by_rank={}
    for old in cases:
        if len(old.identifier)!=10 or old.identifier[-3:-1]!=('hut',647):raise ValueError('SAME_HUT647')
        by_rank.setdefault(old.identifier[0],[]).append(old)
    if set(by_rank)!=set(range(25)):raise ValueError('EXACT25PHYSICAL_TARGETS')
    for rows in by_rank.values():
        if tuple(x.identifier[-1] for x in rows)!=(2000,500,250):raise ValueError('ORDERED_THREE_DOMAINS')
        if len({x.inventory.expected_inventory_sha256 for x in rows})!=1:raise ValueError('SAME_ORIGINAL_INVENTORY')
        if any(tuple(x.identifier[1:7])!=x.inventory.parents[0].occurrence[:6] for x in rows):raise ValueError('PHYSICAL_TARGET_IDENTITY')
    return by_rank

def solve(old,budget,deadline,calls,clock=time.monotonic):
    """Complete ORIGINAL partition, no first-uncovered early return or retries."""
    local=bridge(old);parents=local.inventory.parents
    check(deadline,clock)
    try:budget.reserve(len(parents),len(local.panels))
    except c.Refuse as error:raise Halt('UNKNOWN_'+str(error))
    chosen=[];reasons=[];cache={}
    for parent in parents:
        found=None;reason='NO_FIXED_FULL_PANEL'
        for index,panel in enumerate(local.panels):
            check(deadline,clock);budget.candidate()  # before L formation OR coverage
            if index not in cache:
                value=a.make_assignment(old.panels[index],old.eyes)
                if type(value)is a.q.Unknown:
                    cache[index]=q.Unknown(value.reason)
                elif type(value)is a.q.Assignment:
                    cache[index]=q.Assignment(panel,value.functional,value.orientation)
                else:raise Halt('UNKNOWN_ASSIGNMENT_RESULT')
            value=cache[index]
            if type(value)is q.Unknown:
                if value.reason=='MEMORY_ALLOCATION':raise Halt('UNKNOWN_MEMORY_ALLOCATION')
                reason=value.reason;continue
            calls['candidate_primitives']+=1
            proof=q.cover_triangle(local.eyes,parent,value)
            check(deadline,clock)
            if type(proof)is q.TriangleOpportunity:found=value;break
            if type(proof)is not q.Unknown:raise Halt('UNKNOWN_PRIMITIVE_RESULT')
            if proof.reason=='MEMORY_ALLOCATION':raise Halt('UNKNOWN_MEMORY_ALLOCATION')
            reason=proof.reason
        chosen.append(found);reasons.append(None if found is not None else reason)
    check(deadline,clock)
    # Final budget calls are individually deadline-checked while preserving exact
    # reviewed Budget class identity; no predicate or library source is modified.
    original_final=budget.final
    def final():
        check(deadline,clock);original_final();calls['final_primitives']+=1
    budget.final=final
    try:result=c.validate(c.Partition(local.inventory,local.eyes,tuple(chosen),tuple(reasons)),budget)
    finally:budget.final=original_final
    check(deadline,clock)
    if type(result)is not c.Validated:raise Halt('UNKNOWN_FINAL_'+result.reason)
    return local,result

def partition_row(local,result):
    parents=local.inventory.parents
    covered=tuple(i for i,p in enumerate(result.proofs) if p is not None)
    draw=tuple(i for i,p in enumerate(result.proofs) if p is None)
    cover_indices={v for i in covered for v in parents[i].indices};draw_indices={v for i in draw for v in parents[i].indices}
    return dict(status='NOMINAL_COMPLETE_ORIGINAL_PARTITION_ONLY',complete_originals=len(parents),
                inventory_sha256=local.inventory.expected_inventory_sha256,covered_originals=covered,unproved_draw_originals=draw,
                draw_reasons=tuple((i,result.partition.reasons[i]) for i in draw),
                fixed_assignments=tuple((i,q._assignment_record(result.partition.assignments[i])) for i in covered),
                final_proofs=tuple(dataclasses.asdict(result.proofs[i]) for i in covered),dependencies=result.dependencies,
                covered_triangle_corner_references=3*len(covered),covered_local_indices=tuple(sorted(cover_indices)),
                unproved_draw_local_indices=tuple(sorted(draw_indices)),exclusively_covered_local_indices=tuple(sorted(cover_indices-draw_indices)),
                actual_removed_transform_corners=None,modelled_ms=None,runtime_admitted=False)

def run(cases,budget,deadline,clock=time.monotonic):
    rows=[];completed={};halt=None;calls=dict(candidate_primitives=0,final_primitives=0)
    for old in cases:
        before=(budget.candidates,budget.finals)
        if halt:row=dict(status=halt,started=False,nominal_cell_union_complete=False,retain_all_originals=True)
        else:
            try:
                local,result=solve(old,budget,deadline,calls,clock)
                completed[old.identifier]=(local,result);row=partition_row(local,result);row['started']=True
            except (Halt,c.Refuse,MemoryError,OverflowError) as error:
                halt='UNKNOWN_MEMORY_ALLOCATION' if isinstance(error,(MemoryError,OverflowError)) else str(error)
                row=dict(status=halt,started=True,nominal_cell_union_complete=False,retain_all_originals=True,partial_discarded=True)
        row.update(case=old.identifier,input_case_fingerprint=old.input_case_fingerprint,case_fingerprint=old.expected_fingerprint,
                   candidate_attempts=budget.candidates-before[0],candidate_volume_upper=128*(budget.candidates-before[0]),
                   final_original_checks=budget.finals-before[1],final_volume_upper=128*(budget.finals-before[1]))
        rows.append(row)
    domains=[];effective={}
    for size in (2000,500,250):
        selected=[old for old in cases if old.identifier[-1]==size]
        if len(selected)!=25 or any(old.identifier not in completed for old in selected):
            deps=q.Unknown('INCOMPLETE_25LET_DOMAIN')
        else:deps=c.cell_dependencies(tuple(completed[old.identifier][1] for old in selected))
        ok=type(deps)is tuple
        domains.append(dict(size_mm=size,all25_complete=all(old.identifier in completed for old in selected) and len(selected)==25,
                            global_full_panel_dependencies=deps if ok else None,status='NOMINAL_CELL_UNION_ONLY' if ok else deps.reason,
                            runtime_admitted=False))
        for old in selected:effective[old.identifier]=ok
    signatures=[]
    for rank in range(25):
        oldrows=[x for x in cases if x.identifier[0]==rank]
        if len(oldrows)!=3 or any(x.identifier not in completed for x in oldrows):
            signatures.append(dict(rank=rank,status='UNQUALIFIED_INCOMPLETE_THREE_DOMAINS'));continue
        results=[]
        for old in oldrows:
            local,r=completed[old.identifier]
            if not effective.get(old.identifier,False):
                # Failed GLOBAL cell union means draw ALL; never keep hidden bits.
                safe=c.Partition(local.inventory,local.eyes,(None,)*len(local.inventory.parents),('GLOBAL_CELL_UNQUALIFIED',)*len(local.inventory.parents))
                r=c.validate(safe,budget)
                if type(r)is not c.Validated:raise ValueError('CONSERVATIVE_DRAW_PARTITION')
            results.append(r)
        local=completed[oldrows[0].identifier][0]
        material_scope=a.token(('ORIGINAL_PARENT_PART_SCOPE_ONLY',local.inventory.source_binding_sha256,local.inventory.parents[0].occurrence[:3]))
        gs=c.groups(tuple(results),material_scope)
        if type(gs)is not tuple:
            signatures.append(dict(rank=rank,status='UNQUALIFIED_'+gs.reason));continue
        signatures.append(dict(rank=rank,status='NOMINAL_SIGNATURE_PARTITION_ONLY',material_scope='ORIGINAL_PART_IDENTITY_ONLY_DESCRIPTOR_BYTES_NOT_EXTRACTED',
                               groups=tuple(dict(mask=g.mask,ordinals=g.ordinals,original_oriented_indices=tuple(p.indices for p in g.parents)) for g in gs),
                               group_count=len(gs),drawn_group_counts=tuple(sum(not ((g.mask>>i)&1) for g in gs) for i in range(3)),
                               cost_gate='UNESTABLISHED',runtime_admitted=False))
    for row in rows:row['nominal_cell_union_complete']=effective.get(tuple(row['case']),False)
    for i,domain in enumerate(domains):
        selected=[row for row in rows if row['case'][-1]==domain['size_mm']]
        domain['nominal_per_let_covered_originals_before_global_union']=sum(len(row.get('covered_originals',())) for row in selected)
        domain['covered_originals_after_global_union']=sum(len(row.get('covered_originals',())) for row in selected if row['nominal_cell_union_complete'])
        domain['covered_triangle_corner_references_after_global_union']=3*domain['covered_originals_after_global_union']
        domain['sum_per_let_exclusive_local_index_slots']=sum(len(row.get('exclusively_covered_local_indices',())) for row in selected if row['nominal_cell_union_complete'])
        domain['exclusive_slot_count_is_not_unique_pool_vertices_or_transforms']=True
        domain['proposed_drawn_signature_groups']=sum(s.get('drawn_group_counts',(0,0,0))[i] for s in signatures)
        domain['complete_signature_group_roster']=all('groups' in s for s in signatures)
        domain['actual_removed_transform_corners']=None
        domain['modelled_ms']=None
    return dict(results=rows,domains=domains,signatures=signatures,work=dict(caps=budget.caps,reserved=budget.reserved,
                candidate_attempts=budget.candidates,candidate_volume_upper=128*budget.candidates,
                final_original_checks=budget.finals,final_volume_upper=128*budget.finals,reservations_never_refunded=True),calls=calls,halt=halt)

def own_sources(repo,source):
    if type(source)is not str or len(source)!=40 or any(x not in '0123456789abcdef' for x in source):raise ValueError('EXACT_ADAPTER_SOURCE_REQUIRED')
    pins=a.own_sources(repo,F7)
    folder=Path(__file__).resolve().parent
    for name,commit in tuple((n,CHUNKS) for n in ('original_chunks.py','test_original_chunks.py','ORIGINAL-CHUNKS.md'))+tuple((n,source) for n in OWN):
        path=folder/name;rel=path.relative_to(repo.resolve()).as_posix();raw=subprocess.check_output(['git','-C',str(repo),'show',commit+':'+rel])
        if path.read_bytes()!=raw:raise ValueError('EXACT_OWNED_SOURCE '+name)
        pins[name]=a.pin(path)
    return pins

def grant_binding(source,review_sha,reader_repo,prepared,exposure,out):
    return dict(issuer='/root',approved=True,scope='SOURCE_QUAD24_ORIGINAL_TRIANGLE_PARTITIONS_FINITE75_ONLY',profile=PROFILE,policy=POLICY,
                adapter_source=source,adapter_review_sha256=review_sha,frozen_binding_source=F7,original_chunks_source=CHUNKS,
                original_chunks_review_sha256=CHUNKS_REVIEW,generic_source=a.GENERIC_SOURCE,generic_review_sha256=a.GENERIC_REVIEW,
                reader_source=a.READER_SOURCE,preparation_source=a.PREPARATION_SOURCE,plan_sha256=a.PLAN_SHA,seal_sha256=a.SEAL_SHA,
                controls_sha256=a.CONTROLS_SHA,input_cases_sha256=a.INPUT_CASES_SHA,case_count=75,physical_lets=25,original_occurrences=2667,
                limits=LIMITS,reader_repo=str(reader_repo.resolve()),prepared_directory=str(prepared.resolve()),
                exposure_report=str(exposure.resolve()),exposure_report_sha256=EXPOSURE_SHA,output=str(out.resolve()),
                new_rays=0,ledger_accesses=0,runtime_admitted=False,cost_extraction=False)

def authorize(args):
    if any(x is None for x in (args.grant,args.grant_sha256,args.review,args.review_sha256)):
        raise ValueError('SEPARATE_NEW_ROOT_GRANT_AND_REVIEW_REQUIRED')
    a.require(args.grant,args.grant_sha256);a.require(args.review,args.review_sha256)
    if json.loads(args.grant.read_bytes())!=grant_binding(args.expected_source,args.review_sha256,args.reader_repo,args.prepared_directory,args.exposure_report,args.out):
        raise ValueError('NEW_PROFILE_SOURCE_CAPS_PATHS_GRANT_MISMATCH')
    return dict(grant=a.pin(args.grant),review=a.pin(args.review))

def exposure_rows(path,cases):
    a.require(path,EXPOSURE_SHA);report=json.loads(path.read_bytes());expected={tuple(x.identifier[1:7]) for x in cases}
    rows=report['targets']
    if len(rows)!=25 or {tuple(t['physical']) for t in rows}!=expected:raise ValueError('EXACT_TARGET_EXPOSURE_METADATA')
    return tuple(dict(rank=t['rank'],physical=t['physical'],host_preSG_corner_records=t['known_exposure']['host_preSG_corners'],
                      actual_submitted_vertices=None,actual_removed_transform_corners=None) for t in rows)

def numeric_environment():
    keys=('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','VECLIB_MAXIMUM_THREADS')
    values={k:os.environ.get(k) for k in keys}
    if any(v!='1' for v in values.values()):raise ValueError('EXPLICIT_ONE_NUMERIC_THREAD_REQUIRED')
    return values

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ('repo','reader-repo','prepared-directory','exposure-report','out'):ap.add_argument('--'+name,type=Path,required=True)
    ap.add_argument('--expected-source',required=True);ap.add_argument('--execute',action='store_true')
    ap.add_argument('--grant',type=Path);ap.add_argument('--grant-sha256');ap.add_argument('--review',type=Path);ap.add_argument('--review-sha256')
    args=ap.parse_args();start=time.monotonic();resource.setrlimit(resource.RLIMIT_AS,(268435456,)*2)
    if args.out.exists() or any(args.out.resolve().is_relative_to(p.resolve()) for p in (args.repo,args.reader_repo,args.prepared_directory)):
        raise ValueError('EXCLUSIVE_EXTERNAL_OUTPUT_REQUIRED')
    pins=own_sources(args.repo,args.expected_source)
    result=dict(classification='HELD_SOURCE_ONLY_ZERO_PRIVATE_CALLS',source=args.expected_source,profile=PROFILE,policy=POLICY,
                owned_sources=pins,limits=LIMITS,grant_template=grant_binding(args.expected_source,'<independent-new-adapter-review-sha256>',args.reader_repo,args.prepared_directory,args.exposure_report,args.out),
                private_reader_invocations=0,new_rays=0,ledger_accesses=0,other9600_cases='UNTESTED_UNKNOWN',runtime_admitted=False,
                cost_extraction=False,modelled_ms=None,yield_gate='UNESTABLISHED',numeric_raster_current_source_receipts='UNQUALIFIED')
    if args.execute:
        result['authorization']=authorize(args)  # BEFORE reader/prepared/exposure access
        result['numeric_environment']=numeric_environment()
        with tempfile.TemporaryDirectory(prefix='original-chunks75-',dir='/dev/shm') as temporary:
            result['private_reader_invocations']=1
            cases,binding=a.bind_cases(args.reader_repo,args.prepared_directory,Path(temporary))
            universe(cases);exposure=exposure_rows(args.exposure_report,cases);check(start+115)
            budget=c.Budget();answer=run(cases,budget,start+115)
            result.update(classification='NOMINAL_ORIGINAL_PARTITION_SEARCH_NO_RUNTIME_ADMISSION',binding=binding,
                          host_exposure=exposure,host_preSG_cohort_corners=sum(t['host_preSG_corner_records'] for t in exposure),
                          plan=tuple(dict(case=x.identifier,case_fingerprint=x.expected_fingerprint,complete_case_record=a.case_record(x),reservation=a.reservation(x)) for x in cases),**answer)
    result['seconds']=time.monotonic()-start;result['peak_rss_kib']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    raw=(json.dumps(result,indent=1,default=str)+'\n').encode()
    if len(raw)+65536>16777216 or time.monotonic()-start>=120:raise ValueError('OUTPUT_OR_WALL_CAP_NO_PUBLISH')
    args.out.mkdir();(args.out/'report.json').write_bytes(raw)
    print(json.dumps(dict(classification=result['classification'],report=a.pin(args.out/'report.json'),seconds=result['seconds'])),flush=True)

if __name__=='__main__':main()
