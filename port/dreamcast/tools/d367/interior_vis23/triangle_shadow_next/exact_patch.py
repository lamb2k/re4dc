"""Exact IDEAL finite-chain coverage of an actual indexed triangulated disk.

No hull, welding, flattening or hole fill. Shared source IDs are single physical
variables. This oracle does not establish source provenance or renderer state.
"""
from collections import defaultdict,deque
from fractions import Fraction as Q
from exact_shadow import I,vec,sub,cross,dot,det,corners,expand
from exact_union import signed_lower


def indexed_disk(triangles):
    faces=tuple(tuple(t) for t in triangles)
    if not faces:raise ValueError('empty_faces')
    if any(len(t)!=3 or len(set(t))!=3 or any(type(i) is not int for i in t) for t in faces):raise ValueError('face_indices')
    if len({frozenset(t) for t in faces})!=len(faces):raise ValueError('duplicate_faces')
    vertices={i for t in faces for i in t};edges=defaultdict(list);incident=defaultdict(list)
    for fi,t in enumerate(faces):
        for v in t:incident[v].append(fi)
        for a,b in zip(t,t[1:]+t[:1]):edges[tuple(sorted((a,b)))].append((fi,a,b))
    outer=[];adj=[set() for t in faces]
    for edge,uses in edges.items():
        if len(uses)==1:outer.append(uses[0][1:])
        elif len(uses)==2:
            first,second=uses
            if first[1:]!=second[1:][::-1]:raise ValueError('interior_winding')
            adj[first[0]].add(second[0]);adj[second[0]].add(first[0])
        else:raise ValueError('nonmanifold_edge')
    visited={0};queue=deque([0])
    while queue:
        for fi in adj[queue.popleft()]:
            if fi not in visited:visited.add(fi);queue.append(fi)
    if len(visited)!=len(faces):raise ValueError('disconnected_faces')
    if len(vertices)-len(edges)+len(faces)!=1:raise ValueError('euler_not_one')
    outgoing={};incoming={}
    for a,b in outer:
        if a in outgoing or b in incoming:raise ValueError('pinched_boundary')
        outgoing[a]=b;incoming[b]=a
    if not outer or set(outgoing)!=set(incoming):raise ValueError('open_boundary')
    start=min(outgoing);cycle=[start]
    for _ in range(len(outer)):
        nxt=outgoing[cycle[-1]]
        if nxt==start:break
        if nxt in cycle:raise ValueError('boundary_self_repeat')
        cycle.append(nxt)
    if outgoing[cycle[-1]]!=start or len(cycle)!=len(outer):raise ValueError('multiple_boundary_cycles')
    boundary_vertices=set(cycle);links={}
    for v in vertices:
        graph=defaultdict(set);link_edges=set()
        for fi in incident[v]:
            a,b=[i for i in faces[fi] if i!=v];key=tuple(sorted((a,b)))
            if key in link_edges:raise ValueError('duplicate_link_edge')
            link_edges.add(key);graph[a].add(b);graph[b].add(a)
        reached={next(iter(graph))};queue=deque(reached)
        while queue:
            for u in graph[queue.popleft()]:
                if u not in reached:reached.add(u);queue.append(u)
        if reached!=set(graph):raise ValueError('disconnected_vertex_link')
        degrees={u:len(ns) for u,ns in graph.items()}
        if v in boundary_vertices:
            endpoints={u for u,d in degrees.items() if d==1}
            if endpoints!={outgoing[v],incoming[v]} or any(d not in (1,2) for d in degrees.values()):raise ValueError('boundary_link_not_path')
            links[v]='path'
        else:
            if len(graph)<3 or any(d!=2 for d in degrees.values()):raise ValueError('interior_link_not_cycle')
            links[v]='cycle'
    return dict(faces=faces,vertices=sorted(vertices),boundary=tuple(cycle),edges=len(edges),interior_edges=len(edges)-len(outer),euler=1,vertex_links=links,kind='Authenticated abstract indexed disk only')


def prove_patch(vertices,triangles,eye_box,target_box,vertex_error=0,eye_error=0,target_error=0,eye_clearance=0,target_clearance=0,boundary_mode="strict_convex"):
    """Sufficient exact/interval full-box finite-chain triangle coverage.

    Directed boundaries cancel to the real boundary chain. Strict-convex mode
    establishes winding one; boundary-kernel mode establishes winding >= one.
    Positive face orientations supply nonnegative triangle coverage counts.
    The finite CLOSED triangle union covers internal edges/vertices by closure.
    Every actual face plane separates E/T, so a real hit precedes the target.
    """
    if boundary_mode not in ("strict_convex","boundary_kernel"):raise ValueError("boundary_mode")
    try:topology=indexed_disk(triangles)
    except ValueError as error:return dict(proven=False,reason='topology',detail=str(error))
    faces=topology['faces'];cycle=topology['boundary'];used=topology['vertices']
    nominal={i:vec(vertices[i]) for i in used}
    if any(len(v)!=3 for v in nominal.values()):raise ValueError('position_arity')
    normals=[cross(sub(nominal[t[1]],nominal[t[0]]),sub(nominal[t[2]],nominal[t[0]])) for t in faces]
    if any(not any(n) for n in normals):return dict(proven=False,reason='degenerate_face')
    r=Q(vertex_error)
    if r<0 or Q(eye_clearance)<0 or Q(target_clearance)<0:raise ValueError('negative_uncertainty_or_clearance')
    # One physical variable per SAME actual source index, shared by ALL faces.
    v={i:tuple(I(x-r,x+r) for x in nominal[i]) for i in used}
    es=corners(expand(eye_box,eye_error));ts=corners(expand(target_box,target_error))
    plane_data=[]
    for face in faces:
        a,b,c=[v[i] for i in face];normal=cross(sub(b,a),sub(c,a));norm=sum(max(abs(x.lo),abs(x.hi)) for x in normal)
        se=[-det(sub(a,e),sub(b,e),sub(c,e)) for e in es]
        st=[-det(sub(a,t),sub(b,t),sub(c,t)) for t in ts]
        plane_data.append((norm,se,st))
    sigma=None;margins=[]
    for sign in (1,-1):
        candidate=[(min(signed_lower(x,sign) for x in se),min(signed_lower(-x,sign) for x in st),norm) for norm,se,st in plane_data]
        if all(a>Q(eye_clearance)*n and b>Q(target_clearance)*n for a,b,n in candidate):sigma=sign;margins=candidate;break
    if sigma is None:return dict(proven=False,reason='face_plane_or_orientation_unknown')
    direction=tuple(-sigma*x for x in normals[0]);chart_min=None
    for e in es:
        for point in list(v.values())+list(ts):
            value=dot(direction,sub(point,e));lower=value.lo if isinstance(value,I) else value
            if lower<=0:return dict(proven=False,reason='chart_unknown')
            chart_min=lower if chart_min is None else min(chart_min,lower)
    # Finish the ENTIRE convex boundary stage before target-edge tests.
    convex_min=None
    if boundary_mode=="strict_convex":
        for k,ia in enumerate(cycle):
            ib=cycle[(k+1)%len(cycle)];a,b=v[ia],v[ib]
            for j in cycle:
                if j in (ia,ib):continue
                for e in es:
                    value=-det(sub(a,e),sub(b,e),sub(v[j],e));lower=signed_lower(value,sigma)
                    if lower<=0:return dict(proven=False,reason='boundary_convexity_unknown',edge=[ia,ib],other_vertex=j,interval_lower=str(lower),nominal_collinear=not any(cross(sub(nominal[ib],nominal[ia]),sub(nominal[j],nominal[ia]))))
                    convex_min=lower if convex_min is None else min(convex_min,lower)
    edge_min=None
    for k,ia in enumerate(cycle):
        ib=cycle[(k+1)%len(cycle)];a,b=v[ia],v[ib]
        for e in es:
            for t in ts:
                value=-det(sub(a,e),sub(b,e),sub(t,e));lower=signed_lower(value,sigma)
                if lower<=0:return dict(proven=False,reason='target_edge_unknown',edge=[ia,ib])
                edge_min=lower if edge_min is None else min(edge_min,lower)
    return dict(proven=True,boundary_mode=boundary_mode,coverage_winding='one' if boundary_mode=='strict_convex' else 'at_least_one',sigma=sigma,faces=len(faces),topology=topology,chart_direction=[str(x) for x in direction],chart_min=str(chart_min),convex_min=str(convex_min),target_edge_min=str(edge_min),face_plane_margins=[dict(eye=str(a),target=str(b),normal_l1_upper=str(n)) for a,b,n in margins],shared_endpoints='One correlated physical variable per actual index/cache/kernel/transform/clip identity; real renderer construction still unqualified',renderer_admitted=False)
