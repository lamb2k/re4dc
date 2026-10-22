from pathlib import Path
import hashlib,json,struct
L=Path(__file__).parent;P=L.parent/'castle-controls21'
D=Path(r'C:\Flycast-Evidence\re4-dreamcast\castle18-20261018\Test21\recovered-j-content-20261021')
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
state=D/'route-walk-controlled-ch32-door022/data/disc.state'
assert sha(state)=='b63e07f2ebb8be87be27e051d4580d28c878a0495348c5f99792ff2dcab4f16a'
closed=json.loads((P/'r209-after022-closed-native-gates.json').read_text())
a=next(a for a in closed['areas']if a['no']=='0x16')
h={};exec((L/'audit-authoritative-life-extended-history-20261019.py').read_text().split('targets=[')[0],h)
raw=h['decode'](state);va,code=h['load_segments'](D.parent/'builds/c21jmW/re4dc-game.elf');rb=closed['RAM_offset']
def read(address,n):
 assert 0x8c000000<=address and address+n<=0x8d000000
 return raw[rb+address-0x8c000000:rb+address+n-0x8c000000]
for off in [0x4000,0x100000,0x120000,0x140000]:assert read(va+off,256)==code[off:off+256]
assert read(int(a['ptr'],16),0x9c).hex()==a['raw']
area={k:a[k]for k in ['enabled','type','checkFlag','trigger','checkType','floor','height']}
area.update(func=int(a['func'],16),quad=a['points'])
target=[a['center'][0],a['floor']+1,a['center'][1]]
target=list(struct.unpack('<3f',struct.pack('<3f',*target)))
# Convex original XZ polygon: all edge cross products at its centroid agree.
cross=[(a['points'][(i+1)%4][0]-v[0])*(target[2]-v[1])-(a['points'][(i+1)%4][1]-v[1])*(target[0]-v[0])for i,v in enumerate(a['points'])]
assert min(cross)>0 or max(cross)<0
assert a['floor']<target[1]+250<a['floor']+a['height']
wp=read(0x8c47fb58,1836)
assert struct.unpack_from('<I',wp,1176)[0]==3 and wp[1630]==3 and struct.unpack_from('<I',wp,1640)[0]==3
assert wp[1056:1080]==b'\0'*24
gotos=[wp[984+i*24:1008+i*24].hex()for i in range(3)]
assert all(bytes.fromhex(v)[21]==1 for v in gotos)
dwarf=json.loads((L/'controlled-ch32-drain014-frozen-DWARF.json').read_text())['classes']
assert int(dwarf['cCoord']['members']['pos']['offset'])==0x94 and int(dwarf['cUnit']['members']['be_flag']['offset'])==4
callback=read(area['func'],64)
out=dict(scope='SOURCE_ONLY closed retained gates and exact original trigger target; not live readiness or event acceptance.',state_sha256=sha(state),frame=closed['frame'],HP=closed['HP'],native_Key=closed['Key'],fresh_native_neutral_required=True,AEV16=area,target=target,target_recipe='Float32 original quad centroid XZ/floor+1; checkFlag0 selects pos+250, strictly inside original prism. No leader position guessed as player target.',convex_cross_products=cross,callback_bytes_hex=callback.hex(),callback_closed_sha256=hashlib.sha256(callback).hexdigest(),callback_asset_binding='Require independent native overlay mapping receipt before final qualified handback.',inherited_gotos=gotos,descriptor=dict(address=hex(0x8c47fb58+1056),bytes=24,entry=3,count_address=hex(0x8c47fb58+1176),count=4,published_last=True,maximum_successful_bytes=28,max_entry_unchanged=3),native_lift_recipe=dict(table_symbol='8c3bdd64',object_id=172,pos_offset=148,be_flag_offset=4,DWARF=sha(L/'controlled-ch32-drain014-frozen-DWARF.json')),inputs={str(p):sha(p)for p in [P/'r209-after022-closed-native-gates.json',P/'r209-after022-native-idle-leader-proof.json',P/'r209-after022-source-route-identities.json',L/'NEXT-CH32-SOURCE-CAPABILITY-20261022.json',L/'controlled-ch32-drain014-frozen-DWARF.json']})
p=L/'controlled023-retained-AEV16-qualification.json';assert not p.exists();p.write_text(json.dumps(out,indent=2)+'\n',newline='\n')
print(json.dumps(dict(qualification=sha(p),target=target,area=area,bytes=p.stat().st_size)))
