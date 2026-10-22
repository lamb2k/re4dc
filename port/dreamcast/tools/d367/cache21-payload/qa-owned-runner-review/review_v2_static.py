"""Corrected successor source/hash/AST only; no imports/native/query/test actions."""
import ast,datetime,hashlib,json,pathlib
Q=pathlib.Path(r'\\wsl.localhost\Ubuntu-24.04\root\probe\codex-qa21-death-repair\port\dreamcast\tools\d367');P=Q/'qa21_nontrace_owned_runner_v2';B=Q/'qa21_nontrace_owned_runner_v1';OUT=pathlib.Path(__file__).parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();dump=lambda n:ast.dump(n,include_attributes=False)
manifest=json.loads((P/'SOURCE_ONLY_MANIFEST.json').read_text());assert sha(P/'SOURCE_ONLY_MANIFEST.json')=='c0c76c772d05b1c6fa22ceed725f260c1e0c5cbb84863b118795a95b472e9383';pins=[]
for name,row in manifest['files'].items():
 p=P/name;assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256'],name;pins.append(dict(path=name,bytes=p.stat().st_size,sha256=sha(p)))
assert sha(P/'COLLECTOR_CONTRACT.json')=='ff15e0f1ae5dd059a01f71bd25245b16c977f576ece6f8c0d07ff6b30a4546b1';assert sha(P/'parent_reference_broker.py')=='4d77a1871d197a91c4cdf8321afbcd44dc929ee7118fefaa5691b499024df75f'
v1=json.loads((B/'SOURCE_ONLY_MANIFEST.json').read_text());assert sha(B/'SOURCE_ONLY_MANIFEST.json')=='d15859daa1f98a4b76f53432feee947b6e5f9acc405bab702429f2b0c27603fb'
for name,row in v1['files'].items():assert (B/name).stat().st_size==row['bytes'] and sha(B/name)==row['sha256'],name
functions=lambda path:{(c.name+'.' if c is not None else '')+n.name:n for c,body in [(None,ast.parse(path.read_text()).body)]+[(x,x.body) for x in ast.parse(path.read_text()).body if isinstance(x,ast.ClassDef)] for n in body if isinstance(n,ast.FunctionDef)}
changes=[];same=[]
for file in ['native_reference_api.py','parent_reference_broker.py']:
 old=functions(B/file);new=functions(P/file);assert old.keys()==new.keys()
 for name in old:
  if dump(old[name])==dump(new[name]):same.append(file+':'+name)
  else:changes.append(file+':'+name)
assert changes==['native_reference_api.py:WindowsApi.stat','parent_reference_broker.py:Broker.resource_guard','parent_reference_broker.py:Broker.marker_proof']
byteexact=['checkpoint_runner18.child.py','checkpoint_runner18.original.txt','reference_collector.py','child_reference_proxy.py','guest-profile-v2.json','retained-all-track-declarations.json','PROPOSAL_INPUT.json','runner-origin.json','run_source_tests.py']
for n in byteexact:assert (P/n).read_bytes()==(B/n).read_bytes(),n
broker=functions(P/'parent_reference_broker.py');marker=broker['Broker.marker_proof'];text=ast.unparse(marker)
for token in ['self.marker_original = self.api.stat(self.marker_handle)',"retained['deleted']","retained['directory']","retained['creation_filetime'] <= 0",'retained != self.marker_original','now != self.marker_original','poststat != self.marker_original','before = current()','after = current()']:
 assert token in text,token
assert len([n for n in ast.walk(marker) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='open_file'])==3
cap=next(n for n in ast.walk(broker['Broker.resource_guard']) if isinstance(n,ast.Compare) and isinstance(n.left,ast.Call) and isinstance(n.left.func,ast.Attribute) and n.left.func.attr=='evidence_bytes');assert isinstance(cap.ops[0],ast.GtE) and cap.comparators[0].value==60000000
native=functions(P/'native_reference_api.py')['WindowsApi.stat'];assert "creation_filetime=basic.creation" in ast.unparse(native)
coverage=[]
for platform,want in [('linux','59747627f36f8672e44d3d35b1ff4a53338612fc7e9f471a13afc59efc9508d9'),('windows','9a17dedc26ef220214e90c33f8c46c386d8fe8c048a359cb279102184c217c34')]:
 p=P/('receipt-'+platform+'.json');assert sha(p)==want;r=json.loads(p.read_text());assert r['tests']==48 and r['successful'] is True
 for n,h in r['source_sha256'].items():assert sha(P/n)==h,(platform,n)
 coverage.append(dict(platform=platform,receipt=sha(p),retained_tests=48,current_source_hashes=True,rerun=False))
oldtests=functions(B/'test_owned_runner.py');newtests=functions(P/'test_owned_runner.py')
for name,node in oldtests.items():assert name in newtests and dump(node)==dump(newtests[name]),name
newtestnames=[name for name in newtests if name not in oldtests and '.test_' in name];assert len(newtestnames)==10
frozen=json.loads((P/'frozen-source-proof.json').read_text());resolve=lambda n:pathlib.Path('C:/'+n[7:]) if n.startswith('/mnt/c/') else pathlib.Path(r'\\wsl.localhost\Ubuntu-24.04')/pathlib.Path(n.lstrip('/'))
for name,row in frozen['frozen_505f_files'].items():p=resolve(name);assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256'],name
v1review=json.loads((P/'V1_REVIEW.json').read_text());assert sha(pathlib.Path(v1review['path']))==v1review['sha256']=='67bdcba217d0deb139bfcc850404aa75f45084e41f87905f5959d679f277e2d1'
report=dict(scope='SOURCE/hash/AST/retained receipts only; no imports/tests/nativequery/image/preflight/build/guest/adoption',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),candidate='627c4fde9216823ea208a913b8d1173569053be9',disposition='CLEAR bounded source-only corrected collector/runner components; no adoption/native qualification',manifest=sha(P/'SOURCE_ONLY_MANIFEST.json'),pins=pins,v1_pins_preserved=len(v1['files']),only_changed_production_methods=changes,unchanged_production_methods=same,byteexact_components=byteexact,marker_source=ast.get_source_segment((P/'parent_reference_broker.py').read_text(),marker),evidence_cap_exact_GTE=True,retained_coverage=coverage,new_direct_test_methods=newtestnames,all_prior_test_AST_unchanged=True,frozen_505f_files_verified=len(frozen['frozen_505f_files']),v1_block_review_sha256=v1review['sha256'],limitations=['Injected handle/path separation tests do not establish nativeWindows sharing/disposition/IPC compatibility or wallclockfeasibility','Initial native metadata is pinned on firstacceptedmarker open; no replacement reseal thereafter','Namespace/delete is not atomic; concurrentcleanupincident mustdisqualify/preserve remainingevidence','Futureouter/inner adoption/allocation schema/pins/proxycontext/deadline-arm/brokerclose-beforebackendclose wiring remainsrequired','No505f/profile4c/failed13bf/threecurrentreferences/nativequery/image/preflight/guest orproductionrecipe changed'])
(OUT/'review-627c4f.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(disposition=report['disposition'],pins=len(pins),v1preserved=len(v1['files']),changedmethods=len(changes),unchangedmethods=len(same),newtests=len(newtestnames),frozen505f=len(frozen['frozen_505f_files']))))