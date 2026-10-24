"""Exact IDEAL triangle shadows over complete eye-box x target-box products.

This module proves continuous real geometry only. Fractions enclose serialized
inputs exactly; interval inputs are caller-specified perturbations, not an
assertion about SH4, cell selection, raster samples, depth or actual emission.
"""
from fractions import Fraction as Q
from itertools import product


def vec(x):
    return tuple(Q(a) for a in x)


def sub(a, b):
    return tuple(x-y for x, y in zip(a, b))


def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def dot(a, b):
    return sum((x*y for x, y in zip(a, b)), Q(0))


def corners(box):
    lo, hi = map(vec, box)
    if len(lo) != 3 or len(hi) != 3 or any(a > b for a, b in zip(lo, hi)):
        raise ValueError('Invalid finite three-dimensional box')
    return tuple(product(*zip(lo, hi)))


def det(a, b, c):
    return dot(a, cross(b, c))


def h(a, b, e, t):
    return -det(sub(a, e), sub(b, e), sub(t, e))


class I:
    """Closed exact rational interval; no floating-point rounding is used."""
    __slots__ = ('lo', 'hi')

    def __init__(self, lo, hi=None):
        self.lo, self.hi = Q(lo), Q(lo if hi is None else hi)
        if self.lo > self.hi:
            raise ValueError('Reversed interval')

    @staticmethod
    def coerce(x):
        return x if isinstance(x, I) else I(x)

    def __add__(self, other):
        o = self.coerce(other)
        return I(self.lo+o.lo, self.hi+o.hi)

    __radd__ = __add__

    def __neg__(self):
        return I(-self.hi, -self.lo)

    def __sub__(self, other):
        return self + -self.coerce(other)

    def __rsub__(self, other):
        return self.coerce(other) + -self

    def __mul__(self, other):
        o = self.coerce(other)
        ends = (self.lo*o.lo, self.lo*o.hi, self.hi*o.lo, self.hi*o.hi)
        return I(min(ends), max(ends))

    __rmul__ = __mul__


def expand(box, radius):
    r = Q(radius)
    if r < 0:
        raise ValueError('Negative uncertainty')
    return tuple(x-r for x in vec(box[0])), tuple(x+r for x in vec(box[1]))


def prove(triangle, eye_box, target_box, vertex_error=0, eye_error=0,
          target_error=0, eye_clearance=0, target_clearance=0):
    """Return a sufficient certificate of ideal continuous strict occlusion.

    Fixed triangle: each edge determinant is separately affine in E and T.
    All 64 corner pairs bound the whole product by tensor interpolation.
    Uncertain triangle: interval determinants enclose every source choice at
    each corner pair; interpolation then applies to each fixed source choice.
    A single sigma is selected for the entire product, never per corner.
    Plane distance uses an L1 normal upper bound, conservative for L2 distance.
    A failed sufficient test means unknown, never visibility or absence.
    """
    tri = tuple(map(vec, triangle))
    if len(tri) != 3 or any(len(v) != 3 for v in tri):
        raise ValueError('Triangle arity')
    if not any(cross(sub(tri[1], tri[0]), sub(tri[2], tri[0]))):
        return dict(proven=False, reason='degenerate')
    r = Q(vertex_error)
    if r < 0 or Q(eye_clearance) < 0 or Q(target_clearance) < 0:
        raise ValueError('Negative uncertainty or clearance')
    a, b, c = [tuple(I(x-r, x+r) for x in v) for v in tri]
    es, ts = corners(expand(eye_box, eye_error)), corners(expand(target_box, target_error))
    normal = cross(sub(b, a), sub(c, a))
    norm_upper = sum(max(abs(x.lo), abs(x.hi)) for x in normal)
    se = [-det(sub(a, e), sub(b, e), sub(c, e)) for e in es]
    st = [-det(sub(a, t), sub(b, t), sub(c, t)) for t in ts]
    for sigma in (1, -1):
        signed_e = [x if sigma == 1 else -x for x in se]
        signed_t = [-x if sigma == 1 else x for x in st]
        me, mt = min(x.lo for x in signed_e), min(x.lo for x in signed_t)
        if me <= Q(eye_clearance)*norm_upper or mt <= Q(target_clearance)*norm_upper:
            continue
        minimum = None
        for u, v in ((a, b), (b, c), (c, a)):
            for e in es:
                for t in ts:
                    z = -det(sub(u, e), sub(v, e), sub(t, e))
                    z = z if sigma == 1 else -z
                    if z.lo <= 0:
                        return dict(proven=False, reason='edge_unknown')
                    minimum = z.lo if minimum is None else min(minimum, z.lo)
        return dict(proven=True, sigma=sigma, plane_eye_min=str(me),
                    plane_target_min=str(mt), edge_min=str(minimum),
                    normal_l1_upper=str(norm_upper), renderer_admitted=False)
    return dict(proven=False, reason='plane_unknown')


def nominal_filter(triangle, eye_box, target_box):
    """Float necessary filter only. False may discard useful work; never admits.

    Retained pairs MUST pass prove() with exact serialized operands. This
    acceleration cannot turn float error into an accepted geometry proof.
    """
    a, b, c = triangle
    normal = cross(sub(b, a), sub(c, a))
    es = tuple(product(*zip(*eye_box)))
    lo, hi = target_box
    def extrema(k, origin):
        base = sum(k[j]*(lo[j]-origin[j]) for j in range(3))
        ext = [k[j]*(hi[j]-lo[j]) for j in range(3)]
        return base+sum(min(0,x) for x in ext), base+sum(max(0,x) for x in ext)
    for sigma in (1, -1):
        n = tuple(sigma*x for x in normal)
        if min(dot(n,sub(e,a)) for e in es) <= 0 or extrema(n,a)[1] >= 0:
            continue
        good = True
        for u,v in ((a,b),(b,c),(c,a)):
            for e in es:
                k = tuple(sigma*x for x in cross(sub(e,u),sub(v,u)))
                if extrema(k,u)[0] <= 0:
                    good = False
                    break
            if not good:break
        if good:return True
    return False