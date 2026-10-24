"""PUBLIC composition only. No files/assets/private binding or execution CLI.
Every result is nominal exact-real only; never renderer admission or measured gain.
"""
from dataclasses import dataclass
import hashlib
from pathlib import Path
import sys
import types

def _generic():
    path = Path(__file__).resolve().with_name('source_quad.py')
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != '2221649a8e347e567b4bf05d612ced71007db60a5678b01c95fc60ec61c4227f':
        raise ValueError('FROZEN_GENERIC_SOURCE')
    module = types.ModuleType('source_quad')
    module.__file__ = str(path)
    sys.modules['source_quad'] = module
    exec(compile(raw, module.__file__, 'exec'), module.__dict__)
    return module

q = _generic()
PROFILE = 'SOURCE_QUAD24_ORIGINAL_TRIANGLE_PARTITIONS_PUBLIC_V1'
# NEW proposed exhaustive profile, derived from the saved 75-case plan.
# No permission to bind/evaluate actual scenes is conveyed by these constants.
CAPS = (116088, 14859264, 2667, 341376)
MAX_CASES = 75

@dataclass(frozen=True)
class Partition:
    inventory: q.Inventory
    eyes: q.EyeBox
    assignments: tuple  # EXACT original order; None means retain original draw
    reasons: tuple      # None iff assigned; otherwise explicit conservative draw

@dataclass(frozen=True)
class Validated:
    partition: Partition
    proofs: tuple       # One complete final proof per covered original, else None
    dependencies: tuple
    classification: str = 'NOMINAL_ORIGINAL_PARTITION_ONLY'
    runtime_admitted: bool = False
    def __bool__(self):
        raise TypeError('Nominal partition is not a visibility decision')

@dataclass(frozen=True)
class Group:
    mask: int           # Three fixed cells; 0 remains drawn in ALL cells
    ordinals: tuple     # Original occurrence IDs, never new/clipped geometry
    parents: tuple      # Preserve oriented indices, coordinates and affine token

class Refuse(Exception):
    pass

def _integer(x, maximum):
    if type(x) is not int or not 0 <= x <= maximum:
        raise Refuse('BOUNDED_INTEGER')
    return x

class Budget:
    """Whole-case reservations persist; no refund/reset/retry mechanism.
    Reservation counts are worst-case; attempts counts are actual public calls.
    """
    def __init__(self, caps=CAPS):
        if type(caps) is not tuple or len(caps) != 4:
            raise Refuse('CAPS')
        self.caps = tuple(_integer(x, m) for x, m in zip(caps, CAPS))
        self.reserved = (0, 0, 0, 0)
        self.cases = self.candidates = self.finals = 0
    def reserve(self, n, panels):
        _integer(n, q.MAX_PARENTS); _integer(panels, 1036)
        wanted = (n*panels, 128*n*panels, n, 128*n)
        new = tuple(a+b for a,b in zip(self.reserved, wanted))
        if self.cases >= MAX_CASES or any(a>b for a,b in zip(new,self.caps)):
            raise Refuse('WHOLE_CASE_BUDGET')
        self.reserved = new
        self.cases += 1
    def candidate(self):
        if self.candidates >= self.reserved[0]:
            raise Refuse('CANDIDATE_COUNTER')
        self.candidates += 1
    def final(self):
        if self.finals >= self.reserved[2]:
            raise Refuse('FINAL_COUNTER')
        self.finals += 1

def _inventory(inv):
    if type(inv) is not q.Inventory:
        raise Refuse('COMPLETE_ORIGINAL_INVENTORY')
    actual = q.inventory_digest(inv.parents, inv.source_binding_sha256)
    if type(actual) is not str or actual != inv.expected_inventory_sha256:
        raise Refuse('ORIGINAL_INVENTORY_BINDING')
    return inv.parents

def _panel_bijection(assignments):
    ids, records = {}, {}
    for a in assignments:
        if a is None:
            continue
        if type(a) is not q.Assignment:
            raise Refuse('FIXED_FULL_PANEL')
        # Full original faces/shared corners are validated, without predicates.
        try:
            _, definition = q._panel(a.panel, q.Limits())
        except q._Refuse as error:
            raise Refuse(str(error))
        p = a.panel
        if p.identifier in ids and ids[p.identifier] != definition:
            raise Refuse('PHYSICAL_PANEL_ID_ALIAS')
        if p.record in records and records[p.record] != p.identifier:
            raise Refuse('PHYSICAL_PANEL_RECORD_ALIAS')
        ids[p.identifier] = definition
        records[p.record] = p.identifier
    if len(ids) > 16:
        raise Refuse('GLOBAL_CELL_FULL_PANEL_LIMIT')
    return tuple(sorted(ids))

def validate(partition, budget):
    """Complete covered/draw bijection AND final fixed-source proof of EACH cover.
    Failure returns UNKNOWN: caller must retain ALL originals for that result.
    No subset inventory is fabricated for generic cover_assigned.
    """
    try:
        if type(partition) is not Partition or type(budget) is not Budget:
            raise Refuse('PARTITION')
        parents = _inventory(partition.inventory)
        q._eyes(partition.eyes, q.Limits())
        if (type(partition.assignments) is not tuple or type(partition.reasons) is not tuple
            or len(partition.assignments) != len(parents) or len(partition.reasons) != len(parents)):
            raise Refuse('COMPLETE_COVERED_DRAW_BIJECTION')
        deps = _panel_bijection(partition.assignments)
        proofs = []
        for parent, a, reason in zip(parents, partition.assignments, partition.reasons):
            if a is None:
                if type(reason) is not str or not 0 < len(reason) <= 128:
                    raise Refuse('EXPLICIT_UNPROVED_DRAW')
                proofs.append(None)
            else:
                if reason is not None:
                    raise Refuse('COVER_DRAW_OVERLAP')
                budget.final()  # Every attempt charged BEFORE the predicate
                proof = q.cover_triangle(partition.eyes, parent, a)
                if (type(proof) is not q.TriangleOpportunity or proof.occurrence != parent.occurrence
                    or proof.panel != a.panel.identifier or proof.volume_tests != 128 or proof.runtime_admitted):
                    raise Refuse('FINAL_COVERED_SUBSET_FAILURE')
                proofs.append(proof)
        return Validated(partition, tuple(proofs), deps)
    except (Refuse, q._Refuse, TypeError, ValueError, MemoryError, OverflowError) as error:
        return q.Unknown('MEMORY_ALLOCATION' if isinstance(error,(MemoryError,OverflowError)) else str(error))

def evaluate(inventory, eyes, candidates, budget):
    """Visit EVERY original, even after an unproved original; fixed candidate order.
    Candidate list is caller-authenticated; no normal/axis/geometry search here.
    More than16 selected dependencies conservatively refuses this WHOLE result.
    """
    try:
        parents = _inventory(inventory)
        if type(candidates) is not tuple or len(candidates) > 1036 or type(budget) is not Budget:
            raise Refuse('CANDIDATE_ROSTER')
        # Alias-check ALL supplied candidates before the first coverage call.
        # The candidate pool may exceed16; only the selected dependency union may not.
        ids, records = {}, {}
        for a in candidates:
            if type(a) is not q.Assignment:
                raise Refuse('FIXED_FULL_PANEL')
            _, definition = q._panel(a.panel, q.Limits())
            p=a.panel
            if (p.identifier in ids and ids[p.identifier] != definition) or (p.record in records and records[p.record] != p.identifier):
                raise Refuse('CANDIDATE_PANEL_ALIAS')
            ids[p.identifier]=definition; records[p.record]=p.identifier
        budget.reserve(len(parents), len(candidates))
        assigned, reasons = [], []
        for parent in parents:
            found = None
            reason = 'NO_FIXED_FULL_PANEL'
            for a in candidates:
                budget.candidate()
                proof = q.cover_triangle(eyes, parent, a)
                if type(proof) is q.TriangleOpportunity:
                    found = a
                    break
                if type(proof) is not q.Unknown:
                    raise Refuse('INVALID_CANDIDATE_RESULT')
                if proof.reason == 'MEMORY_ALLOCATION':
                    raise Refuse('MEMORY_ALLOCATION')
                reason = proof.reason
            assigned.append(found)
            reasons.append(None if found is not None else reason)
        return validate(Partition(inventory, eyes, tuple(assigned), tuple(reasons)), budget)
    except (Refuse, q._Refuse, TypeError, ValueError, MemoryError, OverflowError) as error:
        return q.Unknown('MEMORY_ALLOCATION' if isinstance(error,(MemoryError,OverflowError)) else str(error))

def _checked_result(r):
    if type(r) is not Validated or r.runtime_admitted or r.classification != 'NOMINAL_ORIGINAL_PARTITION_ONLY':
        raise Refuse('VALIDATED_CELL_RESULT')
    p=r.partition
    if type(p) is not Partition:
        raise Refuse('PARTITION')
    parents=_inventory(p.inventory)
    q._eyes(p.eyes,q.Limits())
    if any(type(x) is not tuple or len(x)!=len(parents) for x in (r.proofs,p.assignments,p.reasons)):
        raise Refuse('COMPLETE_CELL_RESULT')
    if r.dependencies != _panel_bijection(p.assignments):
        raise Refuse('DEPENDENCY_RESULT_BINDING')
    for parent,a,reason,proof in zip(parents,p.assignments,p.reasons,r.proofs):
        if a is None:
            if proof is not None or type(reason) is not str or not 0<len(reason)<=128:
                raise Refuse('DRAW_PROOF_OVERLAP')
        else:
            digest=q._account(((p.eyes.low,p.eyes.high,p.eyes.source_binding_sha256),
                               q._parent_record(parent),q._assignment_record(a)),q.Limits())
            if (reason is not None or type(proof) is not q.TriangleOpportunity
                or proof.occurrence!=parent.occurrence or proof.panel!=a.panel.identifier
                or proof.input_sha256!=digest or proof.volume_tests!=128 or proof.runtime_admitted
                or min(proof.minimum_eye_source_gap,proof.minimum_source_target_gap,
                       proof.minimum_convex_volume,proof.minimum_outer_volume)<=0):
                raise Refuse('FINAL_RESULT_BINDING')
    return parents

def cell_dependencies(results):
    """AND union across ALL included lets in ONE identical whole eye domain.
    Per-inventory provenance tokens remain distinct; compare full numeric boxes.
    Caller separately authenticates identical camera/cell provenance.
    Reject a different cell, duplicate physical parent, aliases or union>16.
    Does not reauthenticate assets or make a runtime certificate.
    """
    try:
        if type(results) is not tuple or not 0 < len(results) <= 25:
            raise Refuse('COMPLETE_CELL_RESULTS')
        eyes, physical, assignments = None, set(), []
        for r in results:
            parents = _checked_result(r)
            p = r.partition
            if eyes is None: eyes = p.eyes
            if (p.eyes.low,p.eyes.high) != (eyes.low,eyes.high):
                raise Refuse('IDENTICAL_COMPLETE_EYE_DOMAIN')
            key = parents[0].occurrence[:6]
            if key in physical:
                raise Refuse('DUPLICATE_PHYSICAL_PARENT')
            physical.add(key)
            if len(r.proofs) != len(parents) or len(p.assignments) != len(parents):
                raise Refuse('COMPLETE_CELL_RESULT')
            for parent,a,proof in zip(parents,p.assignments,r.proofs):
                if a is None:
                    if proof is not None: raise Refuse('DRAW_PROOF_OVERLAP')
                elif (type(proof) is not q.TriangleOpportunity or proof.occurrence != parent.occurrence
                      or proof.panel != a.panel.identifier or proof.runtime_admitted):
                    raise Refuse('FINAL_RESULT_BINDING')
                assignments.append(a)
        return _panel_bijection(tuple(assignments))
    except (Refuse, q._Refuse, TypeError, ValueError, MemoryError, OverflowError) as error:
        return q.Unknown('MEMORY_ALLOCATION' if isinstance(error,(MemoryError,OverflowError)) else str(error))

def groups(results, material_sha256):
    """Exactly THREE cells, same complete let+material; no across-parent welding.
    Material SHA is an explicit caller assertion, never a provenance receipt.
    Each original occurs in exactly one mask; unknown coverage means mask bit0.
    """
    try:
        if type(results) is not tuple or len(results) != 3 or any(type(r) is not Validated for r in results):
            raise Refuse('THREE_COMPLETE_PARTITIONS')
        if (type(material_sha256) is not str or len(material_sha256)!=64
            or any(c not in '0123456789abcdef' for c in material_sha256)):
            raise Refuse('EXPLICIT_MATERIAL_SCOPE_REQUIRED')
        for r in results: _checked_result(r)
        inv=results[0].partition.inventory
        parents=_inventory(inv)
        if any(r.partition.inventory != inv or len(r.proofs)!=len(parents) for r in results):
            raise Refuse('IDENTICAL_ORIGINAL_INVENTORY')
        if len({(r.partition.eyes.low,r.partition.eyes.high) for r in results}) != 3:
            raise Refuse('THREE_DISTINCT_CELL_DOMAINS')
        masks={}
        for i,parent in enumerate(parents):
            mask=sum((1<<cell) for cell,r in enumerate(results) if type(r.proofs[i]) is q.TriangleOpportunity)
            masks.setdefault(mask,[]).append(parent)
        return tuple(Group(mask, tuple(p.occurrence[-1] for p in ps), tuple(ps)) for mask,ps in sorted(masks.items()))
    except (Refuse, q._Refuse, TypeError, ValueError, MemoryError, OverflowError) as error:
        return q.Unknown('MEMORY_ALLOCATION' if isinstance(error,(MemoryError,OverflowError)) else str(error))

def explicit_triangle_list_cost(groups_, index_bytes, header_bytes):
    """Exact arithmetic for a DECLARED NEW independent-triangle list encoding ONLY.
    Not original strip cost, duplication, SH4 cost, emitted asset or a gain model.
    Header excludes any unstated outer table/alignment/vertex/material overhead.
    """
    try:
        if type(groups_) is not tuple or not 0 < len(groups_) <= 8:
            raise Refuse('GROUPS')
        if type(index_bytes) is not int or index_bytes not in (1,2,4):
            raise Refuse('INDEX_WIDTH')
        _integer(header_bytes, 4096)
        seen=set(); occurrences=set(); count=0
        for group in groups_:
            if type(group) is not Group or type(group.mask) is not int or group.mask in seen or not 0 <= group.mask <= 7:
                raise Refuse('UNIQUE_SIGNATURE_GROUPS')
            seen.add(group.mask)
            if len(group.parents)!=len(group.ordinals) or not group.parents:
                raise Refuse('GROUP_BIJECTION')
            for ordinal,parent in zip(group.ordinals,group.parents):
                if type(parent) is not q.Parent or type(ordinal) is not int or ordinal!=parent.occurrence[-1] or ordinal in occurrences:
                    raise Refuse('GROUP_ORIGINAL_BIJECTION')
                occurrences.add(ordinal)
            count += len(group.parents)
        if occurrences != set(range(count)):
            raise Refuse('COMPLETE_GROUP_ORIGINALS')
        return {'encoding':'PROPOSED_INDEPENDENT_TRIANGLE_LIST_ONLY',
                'triangles':count,'corner_records':3*count,'index_bytes':3*count*index_bytes,
                'group_header_bytes':len(groups_)*header_bytes,
                'known_subtotal_bytes':3*count*index_bytes+len(groups_)*header_bytes,
                'actual_strip_delta_bytes':None,'actual_vertex_duplication_bytes':None,
                'modelled_ms':None,'yield_gate':'UNESTABLISHED'}
    except (Refuse, q._Refuse, TypeError, ValueError, MemoryError, OverflowError) as error:
        return q.Unknown('MEMORY_ALLOCATION' if isinstance(error,(MemoryError,OverflowError)) else str(error))
