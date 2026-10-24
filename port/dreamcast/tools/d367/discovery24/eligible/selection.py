"""Observe exact frozen replay membership; numeric source statements unchanged."""
import ast,copy,hashlib,types,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
REPLAY_SHA='ab898d521a2e16832802c6af62208eb9ec5696090208665d01aa048c2f4993dc'
DECODER_SHA='ab6c403b16db7efd7f8d9ed4fc81c88dafdfcc673946438da6377d6c19cbafcd'

def observed_ast(raw):
    if hashlib.sha256(raw).hexdigest()!=REPLAY_SHA:raise ValueError('Frozen numeric replay bytes')
    original=ast.parse(raw);tree=copy.deepcopy(original);fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='replay')
    counts=[0,0,0]
    # The one visibility branch in the actual for-li walk, not any cluster/
    # placement test or unconditional count. Restore/remove hooks below to prove
    # every original AST node/expression remains byte-for-AST unchanged.
    for node in ast.walk(fn):
        if not isinstance(node,ast.For) or not isinstance(node.target,ast.Name) or node.target.id!='ci':continue
        indices=[i for i,n in enumerate(node.body) if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='level' and isinstance(n.value,ast.UnaryOp)]
        if len(indices)!=1:raise ValueError('Exact cluster initialization')
        hook=ast.parse('_selected_lets=[]').body[0];hook._observer=True;node.body.insert(indices[0]+1,hook);counts[0]+=1
    for node in ast.walk(fn):
        if isinstance(node,ast.For) and isinstance(node.target,ast.Name) and node.target.id=='li':
            matches=[n for n in node.body if isinstance(n,ast.If) and isinstance(n.test,ast.Call) and isinstance(n.test.func,ast.Name) and n.test.func.id=='visible']
            if len(matches)!=1:raise ValueError('Exact visible-let branch')
            branch=matches[0]
            if [n.target.id for n in branch.body if isinstance(n,ast.AugAssign) and isinstance(n.target,ast.Name)]!=['count','lets'] or len(branch.body)!=2:raise ValueError('Numeric visibility count body')
            hook=ast.parse('_selected_lets.append(li)').body[0];hook._observer=True;branch.body.append(hook);counts[1]+=1
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and isinstance(node.func.value,ast.Name) and node.func.value.id=='out' and node.func.attr=='append':
            if len(node.args)!=1 or not isinstance(node.args[0],ast.Call) or not isinstance(node.args[0].func,ast.Name) or node.args[0].func.id!='dict':raise ValueError('Exact output row')
            node.args[0].keywords.append(ast.keyword(arg='selected_meshlet_ids',value=ast.Name(id='_selected_lets',ctx=ast.Load())));counts[2]+=1
    if counts!=[1,1,1]:raise ValueError('Observer cardinality')
    restored=copy.deepcopy(tree)
    class Remove(ast.NodeTransformer):
        def visit_Assign(self,n):return None if getattr(n,'_observer',False) else self.generic_visit(n)
        def visit_Expr(self,n):return None if getattr(n,'_observer',False) else self.generic_visit(n)
        def visit_Call(self,n):
            n=self.generic_visit(n)
            n.keywords=[k for k in n.keywords if k.arg!='selected_meshlet_ids'];return n
    restored=Remove().visit(restored)
    if ast.dump(restored,include_attributes=False)!=ast.dump(original,include_attributes=False):raise ValueError('Observer changed original numeric AST')
    return ast.fix_missing_locations(tree)

def load():
    replay=(HERE/'reference_replay.py').read_bytes();decoder=(HERE/'reference_r4im.py').read_bytes()
    if hashlib.sha256(decoder).hexdigest()!=DECODER_SHA:raise ValueError('Frozen decoder bytes')
    rm=types.ModuleType('discovery_frozen_replay');rm.__file__=str(HERE/'reference_replay.py')
    dm=types.ModuleType('discovery_frozen_decoder');dm.__file__=str(HERE/'reference_r4im.py')
    exec(compile(decoder,dm.__file__,'exec'),dm.__dict__)
    exec(compile(observed_ast(replay),rm.__file__,'exec'),rm.__dict__)
    return rm,dm

def select(rm,pkg,camera,expected):
    import struct
    words=camera['view_bits']+camera['projection_bits']+[camera['far_bits']]
    if len(words)!=20:raise ValueError('Complete12view+7projection+far required; no viewport reconstruction')
    cam=[struct.unpack('<f',struct.pack('<I',int(w,16)))[0] for w in words]
    rows=rm.replay(pkg,cam,5.,4.)
    plain=[{k:v for k,v in r.items() if k!='selected_meshlet_ids'} for r in rows]
    if plain!=expected:raise ValueError('Exact318-row frozen R6 replay mismatch')
    for row in rows:
        ids=row['selected_meshlet_ids']
        if len(ids)!=len(set(ids)) or len(ids)!=row['meshlets']:raise ValueError('Observed membership counts')
        if sum(pkg.lets[li]['vc'] for li in ids)!=row['corners']:raise ValueError('Observed membership corners')
    return rows
