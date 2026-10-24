"""Order-preserving strip partitioning for an offline estimate only.

No triangle permutation, cyclic rotation, attribute change or degenerate removal.
A candidate is retained only when it reduces corners; callers own material/group
admission. Local indices remain bytes and each strip count remains <=255.
"""
def triangles(strips):
    out=[]
    for strip in strips:
        if not 3<=len(strip)<=255:raise ValueError('strip length')
        for i in range(len(strip)-2):
            a,b,c=strip[i:i+3]
            out.append((b,a,c) if i&1 else (a,b,c))
    return out

def ordered_partition(strips,corners,allow=True):
    original=[list(s) for s in strips]
    if not allow:return original
    if not 1<=len(corners)<=256:raise ValueError('meshlet corner limit')
    canonical={};ids=[]
    for i,c in enumerate(corners):
        key=tuple(c);ids.append(canonical.setdefault(key,i))
    if any(not 0<=q<len(corners) for s in original for q in s):raise ValueError('local index')
    before=triangles(original)
    ts=[tuple(ids[q] for q in t) for t in before]
    # Dynamic programming handles parity resets: greedily joining the first
    # next triangle can split its remaining source strip and increase traffic.
    n=len(ts);cost=[n+1]*(n+1);end=[None]*n;cost[n]=0
    for i in range(n-1,-1,-1):
        path=list(ts[i]);j=i
        while True:
            v=1+cost[j+1]
            if v<cost[i] or (v==cost[i] and j>end[i]):
                cost[i]=v;end[i]=j
            if j+1==n or len(path)==255:break
            a,b=path[-2:];pair=(b,a) if (len(path)-2)&1 else (a,b)
            if pair!=ts[j+1][:2]:break
            path.append(ts[j+1][2]);j+=1
    candidate=[];i=0
    while i<n:
        j=end[i];candidate.append(list(ts[i])+[ts[k][2] for k in range(i+1,j+1)]);i=j+1
    if sum(map(len,candidate))>=sum(map(len,original)):return original
    decode=lambda ss:[tuple(tuple(corners[q]) for q in t) for t in triangles(ss)]
    if decode(candidate)!=decode(original):raise AssertionError('ordered triangle/provoking attributes changed')
    return candidate

def grouped_partition(strips,corners,ends,allow=True):
    if not ends or ends[-1]!=len(strips) or any(a>b for a,b in zip([0]+ends,ends)):
        raise ValueError('group partition')
    out=[];new_ends=[];start=0
    for stop in ends:
        out.extend(ordered_partition(strips[start:stop],corners,allow))
        new_ends.append(len(out));start=stop
    return out,new_ends

