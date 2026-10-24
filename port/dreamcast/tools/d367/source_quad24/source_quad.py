"""Exact-real perspective union of TWO actual triangles; never a runtime cut.
Caller authenticates source assets/complete inventories and current receipts.
No files, scans, floating point, interval or runtime paths are used here.
"""
from dataclasses import dataclass
from fractions import Fraction as Q
from itertools import product
import hashlib
import json

MAX_PARENTS = 256
MAX_BITS = 256
MAX_VOLUMES = 32768
MAX_BYTES = 1024 * 1024
MAX_PANELS = 16

@dataclass(frozen=True)
class Unknown:
    reason: str
    def __bool__(self):
        raise TypeError('UNKNOWN is not a visibility decision')

@dataclass(frozen=True)
class Parent:
    occurrence: tuple  # placement, field, part, cluster, effectiveLOD, let, ordinal
    indices: tuple  # original oriented local corner IDs, unchanged
    affine_sha256: str
    vertices: tuple

@dataclass(frozen=True)
class Inventory:
    parents: tuple
    source_binding_sha256: str
    expected_inventory_sha256: str

@dataclass(frozen=True)
class PhysicalPanel:
    identifier: int
    record: tuple  # placement, field, part, cluster, let, TWO ordered triples
    source_binding_sha256: str  # caller binds effectiveLOD/affine/full actual source
    faces: tuple  # exactly the two actual triangles, in record order

@dataclass(frozen=True)
class EyeBox:
    low: tuple
    high: tuple
    source_binding_sha256: str

@dataclass(frozen=True)
class Assignment:
    panel: PhysicalPanel
    functional: tuple  # ONE fixed nonzero rational L, not a substituted plane
    orientation: int  # ONE fixed +1 or -1 for the complete eye/target domain

@dataclass(frozen=True)
class Limits:
    max_parents: int = MAX_PARENTS
    max_bits: int = MAX_BITS
    max_volume_tests: int = MAX_VOLUMES
    max_serialized_bytes: int = MAX_BYTES  # accounting bound, not Python RSS

@dataclass(frozen=True)
class TriangleOpportunity:
    occurrence: tuple
    panel: int
    input_sha256: str
    minimum_eye_source_gap: Q
    minimum_source_target_gap: Q
    minimum_convex_volume: Q
    minimum_outer_volume: Q
    volume_tests: int
    runtime_admitted: bool = False
    def __bool__(self):
        raise TypeError('Exact-real opportunity is not a runtime decision')

@dataclass(frozen=True)
class AssignedOpportunity:
    inventory_sha256: str
    input_sha256: str
    original_occurrences: tuple
    dependencies: tuple
    physical_dependencies: tuple
    triangles: tuple
    volume_tests: int
    runtime_admitted: bool = False
    def __bool__(self):
        raise TypeError('Exact-real opportunity is not a runtime decision')

class _Refuse(Exception):
    pass


def _tuple(value, low, high, reason):
    if type(value) is not tuple or not low <= len(value) <= high:
        raise _Refuse(reason)
    return value


def _uint(value, maximum=0xffffffff):
    if type(value) is not int or not 0 <= value <= maximum:
        raise _Refuse('IDENTITY_INTEGER')
    return value


def _hash(value):
    if type(value) is not str or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
        raise _Refuse('PROVENANCE_HASH')
    return value


def _limits(value):
    if type(value) is not Limits:
        raise _Refuse('LIMITS')
    for actual, maximum in zip((value.max_parents, value.max_bits, value.max_volume_tests, value.max_serialized_bytes),
                               (MAX_PARENTS, MAX_BITS, MAX_VOLUMES, MAX_BYTES)):
        if type(actual) is not int or not 0 <= actual <= maximum:
            raise _Refuse('LIMITS')
    return value


def _q(value, limits):
    if type(value) not in (int, Q):
        raise _Refuse('NON_RATIONAL')
    # Check before Fraction conversion as well as every arithmetic result.
    numerator, denominator = (value, 1) if type(value) is int else (value.numerator, value.denominator)
    if max(abs(numerator).bit_length(), denominator.bit_length()) > limits.max_bits:
        raise _Refuse('ARITHMETIC_BITS')
    return Q(value)


def _point(value, limits):
    return tuple(_q(x, limits) for x in _tuple(value, 3, 3, 'POINT_ARITY'))


def _triangle(value, limits):
    return tuple(_point(p, limits) for p in _tuple(value, 3, 3, 'TRIANGLE_ARITY'))


def _sub(a, b, limits):
    return tuple(_q(x-y, limits) for x, y in zip(a, b))


def _dot(a, b, limits):
    terms = tuple(_q(x*y, limits) for x, y in zip(a, b))
    return _q(_q(terms[0]+terms[1], limits)+terms[2], limits)


def _cross(a, b, limits):
    return tuple(_q(_q(a[i]*b[j], limits)-_q(a[j]*b[i], limits), limits)
                 for i, j in ((1, 2), (2, 0), (0, 1)))


def _normal(triangle, limits):
    return _cross(_sub(triangle[1], triangle[0], limits), _sub(triangle[2], triangle[0], limits), limits)


def _volume(eye, a, b, c, limits):
    # Exact cancellation makes the repeated eye affine, not three independent eyes.
    return _dot(_sub(a, eye, limits), _cross(_sub(b, a, limits), _sub(c, a, limits), limits), limits)


def _serial(value):
    if type(value) in (int, str):
        return value
    if type(value) is Q:
        return str(value)
    if type(value) is tuple:
        return [_serial(x) for x in value]
    raise _Refuse('SERIALIZATION_TYPE')


def _account(value, limits):
    raw = json.dumps(_serial(value), separators=(',', ':')).encode('ascii')
    if len(raw) > limits.max_serialized_bytes:
        raise _Refuse('MEMORY_ACCOUNTING_BUDGET')
    return hashlib.sha256(raw).hexdigest()


def _parent(parent, limits):
    if type(parent) is not Parent:
        raise _Refuse('PARENT_TYPE')
    for value in _tuple(parent.occurrence, 7, 7, 'ORIGINAL_OCCURRENCE'):
        _uint(value)
    indices = _tuple(parent.indices, 3, 3, 'ORIGINAL_INDICES')
    for index in indices:
        _uint(index, 255)
    if len(set(indices)) != 3:
        raise _Refuse('DEGENERATE_PARENT')
    _hash(parent.affine_sha256)
    triangle = _triangle(parent.vertices, limits)
    if not any(_normal(triangle, limits)):
        raise _Refuse('DEGENERATE_PARENT')  # never omit an original occurrence
    return triangle


def _parents(parents, limits):
    _tuple(parents, 1, limits.max_parents, 'PARENT_BUDGET')
    physical = None
    for ordinal, parent in enumerate(parents):
        _parent(parent, limits)
        if parent.occurrence[-1] != ordinal:
            raise _Refuse('ORIGINAL_OCCURRENCE_ORDER')
        if physical is None:
            physical = parent.occurrence[:6]
        if parent.occurrence[:6] != physical:
            raise _Refuse('WRONG_ORIGINAL_PARENT')
    return parents


def _parent_record(parent):
    return parent.occurrence, parent.indices, parent.affine_sha256, parent.vertices


def inventory_digest(parents, source_binding_sha256, limits=Limits()):
    """Digest an EXTERNALLY authenticated complete original inventory, not assets."""
    try:
        limits = _limits(limits)
        _parents(parents, limits)
        return _account((_hash(source_binding_sha256), tuple(_parent_record(p) for p in parents)), limits)
    except _Refuse as error:
        return Unknown(str(error))
    except (MemoryError, OverflowError):
        return Unknown('MEMORY_ALLOCATION')


def _eyes(eyes, limits):
    if type(eyes) is not EyeBox:
        raise _Refuse('COMPLETE_EYE_BOX')
    low, high = _point(eyes.low, limits), _point(eyes.high, limits)
    _hash(eyes.source_binding_sha256)
    if any(a > b for a, b in zip(low, high)):
        raise _Refuse('EYE_BOX_ORDER')
    # Include all eight Cartesian corners even for a zero-width axis.
    return tuple(tuple(v) for v in product(*zip(low, high)))


def _panel(panel, limits):
    if type(panel) is not PhysicalPanel:
        raise _Refuse('FULL_PHYSICAL_PANEL')
    _uint(panel.identifier)
    _hash(panel.source_binding_sha256)
    record = _tuple(panel.record, 11, 11, 'PHYSICAL_PANEL_RECORD')
    for value in record[:5]:
        _uint(value)
    for value in record[5:]:
        _uint(value, 255)
    a, b = record[5:8], record[8:11]
    if len(set(a)) != 3 or len(set(b)) != 3 or len(set(a) & set(b)) != 2 or len(set(a) | set(b)) != 4:
        raise _Refuse('TWO_ADJACENT_ACTUAL_TRIANGLES')
    faces = tuple(_triangle(t, limits) for t in _tuple(panel.faces, 2, 2, 'TWO_ACTUAL_FACES'))
    if not all(any(_normal(t, limits)) for t in faces):
        raise _Refuse('DEGENERATE_SOURCE')
    points = {}
    for index, point in zip(record[5:], faces[0]+faces[1]):
        if index in points and points[index] != point:
            raise _Refuse('SHARED_REALIZED_CORNER')
        points[index] = point
    if len(set(points.values())) != 4:
        raise _Refuse('COINCIDENT_SOURCE_CORNERS')
    ea = tuple(zip(a, a[1:]+a[:1]))
    eb = tuple(zip(b, b[1:]+b[:1]))
    shared = tuple(edge for edge in ea if edge[::-1] in eb)
    if len(shared) != 1:
        raise _Refuse('OPPOSITE_SHARED_EDGE')
    diagonal = shared[0]
    boundary = tuple(edge for edge in ea+eb if edge not in (diagonal, diagonal[::-1]))
    if len(boundary) != 4 or len({u for u, v in boundary}) != 4 or len({v for u, v in boundary}) != 4:
        raise _Refuse('FOUR_EDGE_BOUNDARY')
    successor = dict(boundary)
    order = [min(points)]
    for _ in range(3):
        order.append(successor[order[-1]])
    if len(set(order)) != 4 or successor[order[-1]] != order[0]:
        raise _Refuse('ONE_BOUNDARY_CYCLE')
    return tuple(points[index] for index in order), (record, panel.source_binding_sha256, faces)


def _assignment(assignment, limits):
    if type(assignment) is not Assignment:
        raise _Refuse('FIXED_FULL_PANEL_ASSIGNMENT')
    quad, definition = _panel(assignment.panel, limits)
    functional = _point(assignment.functional, limits)
    if not any(functional):
        raise _Refuse('NONZERO_FIXED_FUNCTIONAL')
    if type(assignment.orientation) is not int or assignment.orientation not in (-1, 1):
        raise _Refuse('FIXED_ORIENTATION')
    return quad, definition, functional, assignment.orientation


def _assignment_record(assignment):
    p = assignment.panel
    return p.identifier, p.record, p.source_binding_sha256, p.faces, assignment.functional, assignment.orientation


def _work(parents, limits):
    # All 4*8 consecutive and 4*8*3 outer volumes for EVERY original triangle.
    if parents * 128 > limits.max_volume_tests:
        raise _Refuse('VOLUME_WORK_BUDGET')


def _cover(eyes, eye_points, parent, assignment, validated, limits):
    quad, definition, functional, orientation = validated
    target = parent.vertices
    le = tuple(_dot(functional, e, limits) for e in eye_points)
    ls = tuple(_dot(functional, s, limits) for s in quad)
    lt = tuple(_dot(functional, t, limits) for t in target)
    eye_gap = _q(min(le)-max(ls), limits)
    target_gap = _q(min(ls)-max(lt), limits)
    if eye_gap <= 0:
        raise _Refuse('EYE_SOURCE_DEPTH')
    if target_gap <= 0:
        raise _Refuse('SOURCE_TARGET_DEPTH')
    convex = []
    outer = []
    for i in range(4):
        a, b, c = quad[i], quad[(i+1) % 4], quad[(i+2) % 4]
        for eye in eye_points:
            volume = _q(orientation * _volume(eye, a, b, c, limits), limits)
            if volume <= 0:
                raise _Refuse('PROJECTED_CONVEXITY')
            convex.append(volume)
            for t in target:
                volume = _q(orientation * _volume(eye, a, b, t, limits), limits)
                if volume <= 0:
                    raise _Refuse('OUTER_CONE')
                outer.append(volume)
    digest = _account(((eyes.low, eyes.high, eyes.source_binding_sha256), _parent_record(parent), _assignment_record(assignment)), limits)
    return TriangleOpportunity(parent.occurrence, assignment.panel.identifier, digest, eye_gap, target_gap,
                               min(convex), min(outer), 128)


def cover_triangle(eyes, parent, assignment, limits=Limits()):
    """ONE whole original triangle over ONE whole eye box, fixed actual union.
    Exact-real opportunity only; this is NOT wholelet/inventory authentication.
    """
    try:
        limits = _limits(limits)
        eye_points = _eyes(eyes, limits)
        _parent(parent, limits)
        validated = _assignment(assignment, limits)
        _work(1, limits)
        _account(((eyes.low, eyes.high, eyes.source_binding_sha256), _parent_record(parent), _assignment_record(assignment)), limits)
        return _cover(eyes, eye_points, parent, assignment, validated, limits)
    except _Refuse as error:
        return Unknown(str(error))
    except (MemoryError, OverflowError):
        return Unknown('MEMORY_ALLOCATION')


def cover_assigned(inventory, eyes, assignments, limits=Limits()):
    """Every original parent; <=16 FULL physical Panel dependencies ANDed.
    Missing/error/limit/degenerate input returns UNKNOWN, never a subset proof.
    """
    try:
        limits = _limits(limits)
        if type(inventory) is not Inventory:
            raise _Refuse('COMPLETE_ORIGINAL_INVENTORY')
        parents = _parents(inventory.parents, limits)
        binding = _hash(inventory.source_binding_sha256)
        expected = _hash(inventory.expected_inventory_sha256)
        actual = _account((binding, tuple(_parent_record(p) for p in parents)), limits)
        if actual != expected:
            raise _Refuse('ORIGINAL_INVENTORY_BINDING')
        eye_points = _eyes(eyes, limits)
        _tuple(assignments, len(parents), len(parents), 'COMPLETE_ORIGINAL_ASSIGNMENT')
        _work(len(parents), limits)  # before the first coverage volume
        by_id, by_record, validated = {}, {}, []
        for assignment in assignments:
            value = _assignment(assignment, limits)
            panel = assignment.panel
            definition = value[1]
            if panel.identifier in by_id and by_id[panel.identifier] != definition:
                raise _Refuse('PHYSICAL_PANEL_ID_ALIAS')
            if panel.record in by_record and by_record[panel.record] != panel.identifier:
                raise _Refuse('PHYSICAL_PANEL_RECORD_ALIAS')
            by_id[panel.identifier] = definition
            by_record[panel.record] = panel.identifier
            if len(by_id) > MAX_PANELS:
                raise _Refuse('GLOBAL_FULL_PANEL_LIMIT')
            validated.append(value)
        digest = _account((actual, (eyes.low, eyes.high, eyes.source_binding_sha256),
                           tuple(_parent_record(p) for p in parents),
                           tuple(_assignment_record(a) for a in assignments)), limits)
        triangles = tuple(_cover(eyes, eye_points, parent, assignment, value, limits)
                          for parent, assignment, value in zip(parents, assignments, validated))
        return AssignedOpportunity(expected, digest, tuple(p.occurrence for p in parents),
                                   tuple(sorted(by_id)), tuple(sorted(by_record)), triangles, 128*len(parents))
    except _Refuse as error:
        return Unknown(str(error))
    except (MemoryError, OverflowError):
        return Unknown('MEMORY_ALLOCATION')
