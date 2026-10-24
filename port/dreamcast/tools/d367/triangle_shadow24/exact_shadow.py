"""Bounded exact-real prerequisite only. No renderer or scene admission.

A successful primitive covers one COMPLETE target triangle by ONE fixed source
triangle for every point in the convex hull of the supplied eye vertices.
All inputs are deeply immutable tuples of exact int/Fraction scalars. No float,
implicit epsilon, source search, AABB substitution or endpoint source switching.
"""
from dataclasses import dataclass
from fractions import Fraction

MAX_BITS = 256
MAX_EYES = 64
MAX_TARGETS = 1024
MAX_EDGE_TESTS = 73728
MAX_PANELS = 16


@dataclass(frozen=True)
class Unknown:
    reason: str

    def __bool__(self):
        raise TypeError("UNKNOWN is not a visibility decision")


@dataclass(frozen=True)
class TriangleProof:
    sign: int
    cartesian_pairs: int
    min_eye_plane: Fraction
    min_target_plane: Fraction
    min_edge_volume: Fraction


@dataclass(frozen=True)
class Panel:
    """Caller-authenticated FULL production Panel, with BOTH oriented faces.

    This helper does not authenticate the identifier or actual emission. A later
    adapter must bind the same full Panel and its complete production receipt.
    """
    identifier: int
    faces: tuple


@dataclass(frozen=True)
class SourceFace:
    panel: Panel
    face: int


@dataclass(frozen=True)
class AssignedProof:
    dependencies: tuple
    assignments: tuple
    triangles: tuple


class _Refuse(Exception):
    pass


def _tuple(x, minimum, maximum, reason):
    if type(x) is not tuple or not minimum <= len(x) <= maximum:
        raise _Refuse(reason)
    return x


def _scalar(x):
    if type(x) not in (int, Fraction):
        raise _Refuse("NON_RATIONAL")
    q = Fraction(x)
    if q.numerator.bit_length() > MAX_BITS or q.denominator.bit_length() > MAX_BITS:
        raise _Refuse("INPUT_BITS")
    return q


def _point(x):
    return tuple(_scalar(v) for v in _tuple(x, 3, 3, "POINT_ARITY"))


def _triangle(x):
    return tuple(_point(p) for p in _tuple(x, 3, 3, "TRIANGLE_ARITY"))


def _eyes(x):
    return tuple(_point(p) for p in _tuple(x, 1, MAX_EYES, "EYE_COUNT"))


def _sub(a, b):
    return tuple(a[i] - b[i] for i in range(3))


def _cross(a, b):
    return (a[1]*b[2] - a[2]*b[1], a[2]*b[0] - a[0]*b[2], a[0]*b[1] - a[1]*b[0])


def _dot(a, b):
    return sum((a[i]*b[i] for i in range(3)), Fraction(0))


def _normal(t):
    n = _cross(_sub(t[1], t[0]), _sub(t[2], t[0]))
    if n == (0, 0, 0):
        raise _Refuse("DEGENERATE_SOURCE")
    return n


def _plane(n, a, p):
    return _dot(n, _sub(p, a))


def _edge(u, v, e, t):
    # det(E-U,V-U,T-U), with H_AB(E,C)=d(E).
    return _dot(_sub(e, u), _cross(_sub(v, u), _sub(t, u)))


def _prove(eyes, source, target):
    n = _normal(source)
    de = tuple(_plane(n, source[0], e) for e in eyes)
    if de[0] == 0:
        raise _Refuse("EYE_PLANE")
    sign = 1 if de[0] > 0 else -1
    if any(sign*d <= 0 for d in de):
        raise _Refuse("EYE_SIDE")
    dt = tuple(_plane(n, source[0], t) for t in target)
    if any(sign*d >= 0 for d in dt):
        raise _Refuse("TARGET_DEPTH")
    minimum = None
    for i in range(3):
        u, v = source[i], source[(i+1) % 3]
        for e in eyes:
            for t in target:
                h = sign * _edge(u, v, e, t)
                if h <= 0:
                    raise _Refuse("EDGE_VOLUME")
                minimum = h if minimum is None else min(minimum, h)
    return TriangleProof(sign, len(eyes)*3, min(sign*d for d in de),
                         min(-sign*d for d in dt), minimum)


def eye_box(low, high):
    """Exact closed box vertices; negative coordinates/zero extents are valid.

    Reversed bounds refuse. This is an EYE-domain constructor, never a target
    AABB substitute or proof that an actual camera is in this declared domain.
    """
    try:
        lo, hi = _point(low), _point(high)
        if any(lo[i] > hi[i] for i in range(3)):
            raise _Refuse("REVERSED_BOUNDS")
        return tuple((x, y, z) for x in (lo[0], hi[0])
                     for y in (lo[1], hi[1]) for z in (lo[2], hi[2]))
    except _Refuse as e:
        return Unknown(str(e))


def cover_triangle(eye_vertices, source_triangle, target_triangle):
    """One fixed source for ALL eye/target Cartesian products. Failure UNKNOWN."""
    try:
        return _prove(_eyes(eye_vertices), _triangle(source_triangle), _triangle(target_triangle))
    except _Refuse as e:
        return Unknown(str(e))


def _panel(p):
    if type(p) is not Panel or type(p.identifier) is not int or not 0 <= p.identifier < (1 << 32):
        raise _Refuse("PANEL_ID")
    faces = tuple(_triangle(t) for t in _tuple(p.faces, 2, 2, "PANEL_FACES"))
    for t in faces:
        _normal(t)
    return faces


def cover_assigned(eye_vertices, target_triangles, fixed_sources):
    """Cover EVERY supplied target triangle with one fixed SourceFace each.

    Distinct whole production Panel dependencies are AND requirements, <=16.
    Separate equally long tuples prevent zip-truncating unassigned targets.
    Caller must independently prove that this is the COMPLETE actual emitted
    target geometry/effective LOD and authenticate every full source Panel.
    """
    try:
        eyes = _eyes(eye_vertices)
        targets = _tuple(target_triangles, 1, MAX_TARGETS, "TARGET_COUNT")
        sources = _tuple(fixed_sources, 1, MAX_TARGETS, "ASSIGNMENT_COUNT")
        if len(targets) != len(sources):
            raise _Refuse("ASSIGNMENT_COUNT")
        if len(targets)*len(eyes)*9 > MAX_EDGE_TESTS:
            raise _Refuse("WORK_LIMIT")
        panels, assignments, proofs = {}, [], []
        for i in range(len(targets)):
            source = sources[i]
            if type(source) is not SourceFace or type(source.face) is not int or source.face not in (0, 1):
                raise _Refuse("PANEL_FACE")
            faces = _panel(source.panel)
            identifier = source.panel.identifier
            if identifier in panels and panels[identifier] != faces:
                raise _Refuse("CONFLICTING_PANEL")
            panels[identifier] = faces
            if len(panels) > MAX_PANELS:
                raise _Refuse("PANEL_LIMIT")
            proofs.append(_prove(eyes, faces[source.face], _triangle(targets[i])))
            assignments.append((identifier, source.face))
        return AssignedProof(tuple(sorted(panels)), tuple(assignments), tuple(proofs))
    except _Refuse as e:
        return Unknown(str(e))
