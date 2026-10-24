"""Exact IDEAL coverage by two actual shared-index triangles, never a hull fill.

Shared endpoints are single physical variables in both triangles. Callers must
bind those IDs to the same actual meshlet cache indices/kernel/transform/clip
construction; coordinate-equal copies alone do not establish a renderer seam.
"""
from fractions import Fraction as Q
from exact_shadow import I,vec,sub,cross,dot,det,corners,expand


def boundary(triangles):
    ts=tuple(tuple(t) for t in triangles)
    if len(ts)!=2 or any(len(t)!=3 or len(set(t))!=3 or any(type(i) is not int for i in t) for t in ts):raise ValueError('Invalid source triangle indices')
    shared=set(ts[0])&set(ts[1]);used=set(ts[0])|set(ts[1])
    if len(shared)!=2 or len(used)!=4:raise ValueError('Exactly one actual shared-index edge required')
    common=[];outer=[]
    for t in ts:
        for a,b in zip(t,t[1:]+t[:1]):
            (common if {a,b}==shared else outer).append((a,b))
    if len(common)!=2 or common[0]!=common[1][::-1]:raise ValueError('Shared source edge must have opposite directed use')
    outgoing={a:b for a,b in outer}
    if len(outer)!=4 or len(outgoing)!=4 or len(set(outgoing.values()))!=4:raise ValueError('Boundary is not a simple four-edge cycle')
    cycle=[min(used)]
    for _ in range(3):cycle.append(outgoing[cycle[-1]])
    if len(set(cycle))!=4 or outgoing[cycle[-1]]!=cycle[0]:raise ValueError('Boundary is not one cycle')
    return ts,tuple(cycle),tuple(sorted(shared))


def signed_lower(value,sigma):return value.lo if sigma==1 else -value.hi


def prove_union(vertices,triangles,eye_box,target_box,vertex_error=0,eye_error=0,target_error=0,eye_clearance=0,target_clearance=0):
    """Sufficient continuous IDEAL union, with full corner/interval predicates.

    Positive common chart denominators make angular projection finite. Strict
    convex boundary plus opposite shared-diagonal sides makes the two CLOSED
    projected source triangles partition that quad. Both real planes separate
    E and T, so whichever actual triangle contains the target ray intersects
    before T. The internal diagonal is the same real edge in both triangles.
    Every predicate encloses the full E x T product, not camera point samples.
    """
    try:ts,cycle,shared=boundary(triangles)
    except ValueError as error:return dict(proven=False,reason='topology',detail=str(error))
    used=set(cycle);nominal={i:vec(vertices[i]) for i in used}
    if any(len(v)!=3 for v in nominal.values()):raise ValueError('Position arity')
    normals=[cross(sub(nominal[t[1]],nominal[t[0]]),sub(nominal[t[2]],nominal[t[0]])) for t in ts]
    if any(not any(n) for n in normals):return dict(proven=False,reason='degenerate')
    r=Q(vertex_error)
    if r<0 or Q(eye_clearance)<0 or Q(target_clearance)<0:raise ValueError('Negative uncertainty or clearance')
    # Exactly ONE uncertain physical point per actual cache-index identity.
    # Reusing these same variables preserves the actual diagonal connectivity.
    v={i:tuple(I(x-r,x+r) for x in nominal[i]) for i in used}
    es=corners(expand(eye_box,eye_error));targets=corners(expand(target_box,target_error))
    plane_data=[]
    for t in ts:
        a,b,c=[v[i] for i in t];normal=cross(sub(b,a),sub(c,a));norm=sum(max(abs(x.lo),abs(x.hi)) for x in normal)
        se=[-det(sub(a,e),sub(b,e),sub(c,e)) for e in es]
        st=[-det(sub(a,p),sub(b,p),sub(c,p)) for p in targets]
        plane_data.append((norm,se,st))
    sigma=None;plane_margins=[]
    for sign in (1,-1):
        margins=[(min(signed_lower(x,sign) for x in se),min(signed_lower(-x,sign) for x in st),norm) for norm,se,st in plane_data]
        if all(a>Q(eye_clearance)*n and b>Q(target_clearance)*n for a,b,n in margins):sigma=sign;plane_margins=margins;break
    if sigma is None:return dict(proven=False,reason='plane_unknown')
    # Fixed exact chart direction; uncertain normals are not substituted for it.
    direction=tuple(-sigma*x for x in normals[0]);chart_min=None
    for e in es:
        for point in list(v.values())+list(targets):
            value=dot(direction,sub(point,e));lower=value.lo if isinstance(value,I) else value
            if lower<=0:return dict(proven=False,reason='chart_unknown')
            chart_min=lower if chart_min is None else min(chart_min,lower)
    a,b=[v[i] for i in shared];thirds=[v[next(i for i in t if i not in shared)] for t in ts]
    diagonal=[[-det(sub(a,e),sub(b,e),sub(c,e)) for e in es] for c in thirds]
    if not any(all(signed_lower(x,s)>0 for x in diagonal[0]) and all(signed_lower(x,-s)>0 for x in diagonal[1]) for s in (1,-1)):return dict(proven=False,reason='diagonal_unknown')
    convex_min=None;edge_min=None
    for k in range(4):
        a,b=v[cycle[k]],v[cycle[(k+1)%4]]
        for e in es:
            for j in ((k+2)%4,(k+3)%4):
                c=v[cycle[j]];value=-det(sub(a,e),sub(b,e),sub(c,e));lower=signed_lower(value,sigma)
                if lower<=0:return dict(proven=False,reason='convexity_unknown')
                convex_min=lower if convex_min is None else min(convex_min,lower)
            for target in targets:
                value=-det(sub(a,e),sub(b,e),sub(target,e));lower=signed_lower(value,sigma)
                if lower<=0:return dict(proven=False,reason='edge_unknown')
                edge_min=lower if edge_min is None else min(edge_min,lower)
    return dict(proven=True,sigma=sigma,boundary_indices=cycle,shared_indices=shared,chart_direction=[str(x) for x in direction],chart_min=str(chart_min),convex_min=str(convex_min),outer_edge_min=str(edge_min),plane_margins=[dict(eye=str(a),target=str(b),normal_l1_upper=str(n)) for a,b,n in plane_margins],shared_uncertainty='One correlated physical variable per actual meshlet index, reused in both real source triangles',renderer_admitted=False)
