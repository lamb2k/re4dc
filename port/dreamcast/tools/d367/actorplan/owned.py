#!/usr/bin/env python3
"""owned.py <cg dir>... : actorplan lane. Per drawn frame (PACE_MODE=off arms: every tick drawn), MODELLED nominal
(hwsim_cg): the owned character path (re4dc_actor_transaction_draw minus the PS2 world flush it triggers) split into
vertex kernels / pose palettes / setup, and the object path (re4dc_draw_model_part), plus top setup functions."""
import sys,os,re,bisect,collections
VERT=re.compile(r'^(re4dc_avk_|Part::whole|Part::strips|pass_positions|pass_lights|re4dc_sk1|avk_build_dirs)')
POSE=re.compile(r'^(owner_ganado_palettes|owner_leon_palettes|re4dc_coarse_skin_groups|re4dc_coarse_skin_bones|re4dc_sh4_MTXConcat|re4dc_sh4_MTXInverse|registry_palettes|owner_.*_palettes)')
def load(P):
    syms=[]
    for l in open(os.path.join(P,'cg.syms.txt')):
        p=l.rstrip('\n').split(' ',2)
        if len(p)==3: syms.append((int(p[0],16),p[2]))
    syms.sort(); sa=[a for a,_ in syms]
    def nm(a):
        i=bisect.bisect_right(sa,a)-1; n=re.sub(r'\(anonymous namespace\)::','',syms[i][1])
        return n.split('(')[0] if '(' in n and not n.startswith('(') else n[:80]
    nodes={};kids=collections.defaultdict(list)
    f=open(os.path.join(P,'cg.cg.tsv'));next(f)
    for l in f:
        i,par,e,s,c=l.split('\t');i=int(i);par=int(par);nodes[i]=[par,int(e,16),float(s),int(c)]
        if i: kids[par].append(i)
    nfr=sum(1 for _ in open(os.path.join(P,'cgsim.frames.tsv')))-1
    fn={n:(nm(nodes[n][1]) if n else '<root>') for n in nodes}
    return nodes,kids,fn,nfr
def sub(nodes,kids,fn,root,excl=None):
    self_=collections.Counter();calls=collections.Counter();rc=0
    st=[(0,False)]
    while st:
        n,ins=st.pop()
        if ins and excl and excl.search(fn[n]): continue
        if not ins and root.search(fn[n]): ins=True; rc+=nodes[n][3]
        if ins: self_[fn[n]]+=nodes[n][2]; calls[fn[n]]+=nodes[n][3]
        for c in kids.get(n,[]): st.append((c,ins))
    return self_,calls,rc
for P in sys.argv[1:]:
    nodes,kids,fn,nfr=load(P); K=200000.0*nfr
    tot=sum(v[2] for v in nodes.values())/K
    s,c,rc=sub(nodes,kids,fn,re.compile(r'^re4dc_actor_transaction_draw$'),re.compile(r'^re4dc_ps2_world_before_owned_tr$'))
    v=sum(x for k,x in s.items() if VERT.search(k))/K; p=sum(x for k,x in s.items() if POSE.search(k))/K
    a=sum(s.values())/K
    s2,c2,rc2=sub(nodes,kids,fn,re.compile(r'^re4dc_draw_model_part$'))
    v2=sum(x for k,x in s2.items() if VERT.search(k))/K; a2=sum(s2.values())/K
    s3,c3,rc3=sub(nodes,kids,fn,re.compile(r'^ModelRender$'))
    print('%s: frames %d total %.2f ms/frame | ModelRender %.2f | OWNED tx %.1f calls: all %.3f vertex %.3f pose %.3f SETUP %.3f | OBJECTS draw_model_part %.1f calls: all %.3f vertex %.3f SETUP %.3f'%(
        os.path.basename(os.path.dirname(P.rstrip('/'))) or P,nfr,tot,sum(s3.values())/K,rc/nfr,a,v,p,a-v-p,rc2/nfr,a2,v2,a2-v2))
    rows=[(x,k) for k,x in s.items() if not VERT.search(k) and not POSE.search(k)]
    rows.sort(reverse=True)
    print('   owned setup top: '+', '.join('%s %.3f (%.1f)'%(k[:40],x/K,c[k]/nfr) for x,k in rows[:40]))
