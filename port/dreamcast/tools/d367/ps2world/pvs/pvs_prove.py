#!/usr/bin/env python3
"""Continuous triangle certificates for cluster PVS. See README-proof.md.

This never infers invisibility from ray samples. A single actual triangle must
separate the complete eye box and target box. Independent vertex uncertainty is
bounded with outward-rounded interval arithmetic. Every corner combination is
checked; the signed tetrahedra are separately affine in eye and target.
"""
import itertools
import numpy as np

SIGNS = np.array(list(itertools.product((0., 1.), repeat=3)))


def corners(lo, hi):
    return np.where(SIGNS != 0, np.asarray(hi), np.asarray(lo))


def add(a, b):
    return np.nextafter(a[0] + b[0], -np.inf), np.nextafter(a[1] + b[1], np.inf)


def neg(a):
    return -a[1], -a[0]


def sub(a, b):
    return add(a, neg(b))


def mul(a, b):
    v = np.stack((a[0]*b[0], a[0]*b[1], a[1]*b[0], a[1]*b[1]))
    return np.nextafter(v.min(0), -np.inf), np.nextafter(v.max(0), np.inf)


def component(a, i):
    return a[0][..., i], a[1][..., i]


def cross(a, b):
    pairs = ((1, 2), (2, 0), (0, 1))
    v = [sub(mul(component(a, i), component(b, j)), mul(component(a, j), component(b, i))) for i, j in pairs]
    return np.stack([x[0] for x in v], -1), np.stack([x[1] for x in v], -1)


def dot(a, b):
    v = mul(a, b)
    return add(add(component(v, 0), component(v, 1)), component(v, 2))


def interval(v, error=0.):
    v = np.asarray(v, dtype=np.float64)
    return np.nextafter(v-error, -np.inf), np.nextafter(v+error, np.inf)


def triangle_hides(triangle, eye_lo, eye_hi, target_lo, target_hi,
                   two_sided=False, front_sign=1, vertex_error=32., clearance=2000.):
    """True only for strict continuous all-eye/all-target occlusion.

    clearance is a plane-normal distance, before independent vertex uncertainty.
    Eye/target bounds must already enclose every applicable LOD and all float
    transform uncertainty. Ambiguity, an edge, NaN, reversed sides, clipping
    proximity and degenerate geometry all retain the target.
    """
    tri = np.asarray(triangle, np.float64)
    if tri.shape != (3,3) or not np.isfinite(tri).all(): return False
    arrays=[np.asarray(v,np.float64) for v in (eye_lo,eye_hi,target_lo,target_hi)]
    if any(v.shape!=(3,) or not np.isfinite(v).all() for v in arrays): return False
    elo,ehi,tlo,thi=arrays
    if np.any(elo>ehi) or np.any(tlo>thi) or not (vertex_error>=0 and clearance>0): return False
    ec,tc=corners(elo,ehi),corners(tlo,thi)
    A,B,C=[interval(v,vertex_error) for v in tri]
    normal=cross(sub(B,A),sub(C,A))
    # Upper bound on uncertain normal length, rounded outward.
    magnitudes=np.maximum(abs(normal[0]),abs(normal[1]))
    # Outward L1 bound avoids relying on a library norm's internal rounding.
    norm_max=float(np.nextafter(np.nextafter(magnitudes[0]+magnitudes[1],np.inf)+magnitudes[2],np.inf))
    if not np.isfinite(norm_max) or norm_max<=0: return False
    side_e=dot(normal,sub(interval(ec),A))
    side_t=dot(normal,sub(interval(tc),A))
    direction=0
    clear_bound=np.nextafter(clearance*norm_max,np.inf)
    target_bound=np.nextafter(32.*norm_max,np.inf)
    if np.all(side_e[0] > clear_bound) and np.all(side_t[1] < -target_bound): direction=1
    elif two_sided and np.all(side_e[1] < -clear_bound) and np.all(side_t[0] > target_bound): direction=-1
    elif front_sign==-1 and np.all(side_e[1] < -clear_bound) and np.all(side_t[0] > target_bound): direction=-1
    if not direction or (not two_sided and direction!=front_sign): return False
    # e and t each range over eight corners; uncertain actual vertices are
    # intervals, never candidate sampled surfaces. Strict edge determinants
    # prove every continuous segment crosses the interior of this triangle.
    E=interval(ec[:,None,:]); T=interval(tc[None,:,:])
    for U,V in ((A,B),(B,C),(C,A)):
        d=dot(cross(sub(U,E),sub(V,E)),sub(T,E))
        if direction==1 and not np.all(d[1]<0): return False
        if direction==-1 and not np.all(d[0]>0): return False
    return True


def quad_hides(triangles, boundary, eye_lo, eye_hi, target_lo, target_hi,
               two_sided=False, vertex_error=32., clearance=2000.):
    """Actual shared-edge triangle pair, with a convex projected boundary.

    The caller must authenticate the two triangles and their common edge and
    boundary exactly. Both real triangles separate the entire volumes; the
    projected boundary is strictly convex for all eyes. Thus its interior is
    the union of the two projected triangles, including their common diagonal.
    No sampled or filled rectangle is introduced, even with vertex uncertainty.
    """
    triangles=np.asarray(triangles,np.float64);boundary=np.asarray(boundary,np.float64)
    if triangles.shape!=(2,3,3) or boundary.shape!=(4,3):return False
    if not np.isfinite(triangles).all() or not np.isfinite(boundary).all():return False
    arrays=[np.asarray(v,np.float64) for v in (eye_lo,eye_hi,target_lo,target_hi)]
    if any(v.shape!=(3,) or not np.isfinite(v).all() for v in arrays):return False
    elo,ehi,tlo,thi=arrays
    if np.any(elo>ehi) or np.any(tlo>thi) or not(vertex_error>=0 and clearance>0):return False
    # Authenticate exactly two shared vertices, matching directed common edge,
    # and a boundary made from the four remaining directed source edges.
    edges={};verts=set()
    for tri in triangles:
        for a,b in zip(tri,np.roll(tri,-1,axis=0)):
            a,b=tuple(a),tuple(b);verts.update((a,b))
            reverse=(b,a)
            if reverse in edges:del edges[reverse]
            else:edges[(a,b)]=1
    expected={(tuple(a),tuple(b)) for a,b in zip(boundary,np.roll(boundary,-1,axis=0))}
    if len(verts)!=4 or set(edges)!=expected or len(edges)!=4:return False
    ec,tc=corners(elo,ehi),corners(tlo,thi)
    common=set(map(tuple,triangles[0])) & set(map(tuple,triangles[1]))
    if len(common)!=2:return False
    ca,cb=sorted(common)
    thirds=[next(iter(set(map(tuple,t))-common)) for t in triangles]
    e=interval(ec)
    dn=cross(sub(interval(ca,vertex_error),e),sub(interval(cb,vertex_error),e))
    ds=[dot(dn,sub(interval(v,vertex_error),e)) for v in thirds]
    if not ((np.all(ds[0][1]<0) and np.all(ds[1][0]>0)) or
            (np.all(ds[1][1]<0) and np.all(ds[0][0]>0))):return False
    direction=None
    for tri in triangles:
        A,B,C=[interval(v,vertex_error) for v in tri]
        normal=cross(sub(B,A),sub(C,A))
        mag=np.maximum(abs(normal[0]),abs(normal[1]))
        norm=float(np.nextafter(np.nextafter(mag[0]+mag[1],np.inf)+mag[2],np.inf))
        if not np.isfinite(norm) or norm<=0:return False
        se=dot(normal,sub(interval(ec),A));st=dot(normal,sub(interval(tc),A))
        bound=np.nextafter(clearance*norm,np.inf);target=np.nextafter(32.*norm,np.inf)
        if np.all(se[0]>bound) and np.all(st[1]<-target):d=1
        elif two_sided and np.all(se[1]<-bound) and np.all(st[0]>target):d=-1
        else:return False
        if direction is not None and direction!=d:return False
        direction=d
    E=interval(ec[:,None,:]);T=interval(tc[None,:,:])
    for i in range(4):
        A=interval(boundary[i],vertex_error);B=interval(boundary[(i+1)%4],vertex_error)
        n=cross(sub(A,E),sub(B,E))
        dt=dot(n,sub(T,E))
        if direction==1 and not np.all(dt[1]<0):return False
        if direction==-1 and not np.all(dt[0]>0):return False
        # Every other vertex must project strictly inside this boundary edge.
        # These are independent intervals too, so convexity survives every
        # admitted perturbation of the actual source vertices.
        for j in ((i+2)%4,(i+3)%4):
            dv=dot(n,sub(interval(boundary[j],vertex_error),E))
            if direction==1 and not np.all(dv[1]<0):return False
            if direction==-1 and not np.all(dv[0]>0):return False
    return True
