#!/usr/bin/env python3
"""Strict trace bridge for ONE separately allocated private programme controller."""
import gzip
import hashlib
import json
import lzma
import re
from pathlib import Path
import struct
import tool_closure as tools
import trace_closure792_03 as trace

READ_FLAGS=['O_RDONLY','O_RDONLY|O_CLOEXEC']
WRITE_FLAGS=['O_WRONLY|O_CREAT|O_TRUNC','O_WRONLY|O_CREAT|O_TRUNC|O_CLOEXEC','O_RDWR|O_CREAT|O_TRUNC']
TRACE_PREFIX=['/usr/bin/strace','-f','-qq','-v','-x','-s','262144','-yy','-e','trace=execve,execveat,open,openat,openat2,creat,unlink,unlinkat']

def read_json(path):
    path=Path(path)
    data=path.read_bytes()
    return json.loads(gzip.decompress(data)if path.suffix=='.gz'else lzma.decompress(data)if path.suffix=='.xz'else data)

def symbol_span(path):
    """Exact ELF32 LE image-ID span and independently computed text identity."""
    data=Path(path).read_bytes()
    if data[:6]!=b'\x7fELF\x01\x01':raise ValueError('require ELF32 LE')
    table=struct.unpack_from('<I',data,32)[0];stride,count,strings=struct.unpack_from('<HHH',data,46)
    if stride!=40:raise ValueError('ELF section stride')
    sections=[struct.unpack_from('<10I',data,table+i*stride)for i in range(count)]
    names=sections[strings];names=data[names[4]:names[4]+names[5]]
    text=next(h for h in sections if names[h[0]:names.find(b'\0',h[0])]==b'.text')
    blob=data[text[4]:text[4]+(text[5]&~3)];fnv=2166136261
    for(word,)in struct.iter_unpack('<I',blob):fnv=((fnv^word)*16777619)&0xffffffff
    found=[]
    for h in sections:
        if h[1]!=2:continue
        strs=sections[h[6]];strs=data[strs[4]:strs[4]+strs[5]]
        for off in range(h[4],h[4]+h[5],h[9] or 16):
            name,value,size,info,other,index=struct.unpack_from('<IIIBBH',data,off)
            if strs[name:strs.find(b'\0',name)]==b'_re4dc_image_id':
                target=sections[index];found.append(target[4]+value-target[3])
    if len(found)!=1:raise ValueError('image-ID symbol uniqueness')
    at=found[0]
    if data[at:at+8]!=struct.pack('<2I',0x31444952,0x31444952):raise ValueError('image-ID pre-marker')
    return dict(offset=at,bytes=len(data),masked_sha256=hashlib.sha256(data[:at]+b'\0'*8+data[at+8:]).hexdigest(),expected=struct.pack('<2I',fnv,len(blob)).hex())

class Gate:
    def __init__(self,plan,expected,root,context):
        self.plan=plan;self.root=Path(root);self.context=Path(context);self.pending=None;self.records=[]
        if str(self.root)!=plan['future_root']:raise ValueError('unit root differs')
        allpins=plan['source_tool_snapshot']['pins']+plan['stdlib_pins']+plan['source_bridge_pins']
        bypath={}
        for row in allpins:
            if row['path'] in bypath and any(row[k]!=bypath[row['path']][k]for k in ('resolved','bytes','sha256','mode','symlink_target')):raise ValueError('ambiguous frozen pin')
            bypath.setdefault(row['path'],row)
        self.frozen=list(bypath.values())
        # All snapshot pins are rehashed NOW before any allocated child; historical source pins are not fresh receipts.
        self.fresh_pre=[tools.pin(row['path'],row['role'])for row in self.frozen]
        if not tools.same_pins(self.frozen,self.fresh_pre):raise ValueError('source frozen tool/loader/library/stdlib drift')
        self.expected=[tools.pin(row['path'],'immutable-source-object-header')for row in expected.values()]
        if any(row['sha256']!=expected[row['path']]['sha256'] or row['bytes']!=expected[row['path']]['bytes']for row in self.expected):raise ValueError('unit source/object prehash differs')
        self.check_absence()
        self.pre_maps=sorted(tools.mapped_host_elfs())
        if not set(self.pre_maps)<={row['resolved']for row in self.frozen}:raise ValueError('unplanned controller ELF mapping')
    def check_absence(self):
        if any(Path(path).exists()for path in self.plan['absence']):raise ValueError('loader/tool lookup/bytecode absence changed')
    def pure_post(self):
        self.check_absence();now=[tools.pin(row['path'],row['role'])for row in self.frozen]
        if not tools.same_pins(self.expected,[tools.pin(row['path'],row['role'])for row in self.expected]):raise ValueError('unit source/object aliases or bytes changed')
        if not tools.same_pins(self.fresh_pre,now):raise ValueError('fresh unit tool/plugin/loader/stdlib/source pre/post differs')
        if not tools.mapped_host_elfs()<={row['resolved']for row in self.frozen}:raise ValueError('unplanned post controller ELF')
        return dict(fresh_pre_post_exact=True,pins=now,controller_maps=sorted(tools.mapped_host_elfs()),all_actual_trace_steps=len(self.records))
    def input_policies(self,mutable_path=None):
        rows={}
        candidates=[*self.frozen,*self.expected]
        generated=[self.root/'objects/native_static-linked.o',self.root/'out/re4dc-game.elf',self.root/'shift.elf',self.context/'obj/overlay-a.ld',self.context/'obj/overlay-shift.ld']
        candidates += [tools.pin(p,'generated-input-prechild')for p in generated if p.is_file()]
        for row in candidates:
            actual=tools.pin(row['path'],row['role'])
            if actual!=row:raise ValueError('prechild immutable input changed: '+row['path'])
            resolved=actual['resolved']
            if mutable_path is not None and resolved==str(Path(mutable_path).resolve()):continue
            aliases={actual['path'],resolved}
            for original in list(aliases):
                try:aliases.add(str(Path(original).relative_to(self.context)))
                except ValueError:pass
                prefix='/root/probe/codex-texture-rect21/port/dreamcast/game/platform/'
                if original.startswith(prefix):aliases.update({'platform/'+original[len(prefix):],str(self.context/'platform'/original[len(prefix):])})
            if resolved not in rows:rows[resolved]=dict(pin=actual,aliases=sorted(aliases),read_flags=list(READ_FLAGS))
            else:rows[resolved]['aliases']=sorted(set(rows[resolved]['aliases'])|aliases)
        for policy in self.plan.get('input_aliases',[]):
            frozen=policy['pin'];resolved=frozen['resolved']
            if resolved not in rows or tools.pin(frozen['path'],frozen['role'])!=frozen or any(rows[resolved]['pin'][key]!=frozen[key]for key in ('resolved','bytes','sha256','mode','symlink_target')):raise ValueError('explicit input alias pin differs')
            for alias in policy['aliases']:
                if not Path(alias).is_absolute()or str(Path(alias).resolve(strict=True))!=resolved:raise ValueError('explicit input alias target differs')
                rows[resolved]['aliases']=sorted(set(rows[resolved]['aliases'])|{alias})
        return list(rows.values())
    def before(self,name,command):
        if self.pending is not None or name not in self.plan['steps'] or command!=self.plan['steps'][name]['command']:raise ValueError('unknown/changed/reordered planned command')
        expected_order=self.plan['order'][len(self.records)]
        if name!=expected_order:raise ValueError('programme step order differs')
        self.check_absence();step=self.plan['steps'][name];mutable=self.root/'out/re4dc-game.elf'if name=='patch-image-id'else None
        inputs=self.input_policies(mutable)
        directories=set(self.plan['read_directories'])|{str(Path(row['pin']['resolved']).parent)for row in inputs}|{str(self.context),str(self.context/'obj'),str(self.root/'empty-pyc')}
        contract=dict(root_returncode=0,owned_temp=str(self.root/'temp'),inputs=inputs,executions=step['executions'],required_executions=list(range(len(step['executions']))),required_reads=step.get('required_reads',[]),read_directories=sorted(directories),special_reads={'/dev/null':['O_RDONLY','O_RDONLY|O_CLOEXEC']},writes=[dict(path=p,flags=WRITE_FLAGS)for p in step['outputs']],temporary_writes=[dict(root=str(self.root/'temp'),profile='gcc_resolution',flags=['O_RDWR|O_CREAT|O_EXCL','O_RDWR|O_CREAT|O_EXCL|O_CLOEXEC','O_WRONLY|O_CREAT|O_TRUNC','O_WRONLY|O_CREAT|O_TRUNC|O_CLOEXEC','O_WRONLY'])],transient_data=step.get('transient_data',[]))
        pending=dict(name=name,contract=contract,mutable=mutable,pre_span=symbol_span(mutable)if mutable else None,pre_mutable=tools.pin(mutable,'generated-mutable-data')if mutable else None)
        self.pending=pending
        return TRACE_PREFIX+['-o',str(self.root/(name+'.strace'))]+command,step['environment']
    def after(self,name,returncode):
        pending=self.pending
        if not pending or pending['name']!=name:raise ValueError('missing matching prechild contract')
        contract=pending['contract'];contract['root_returncode']=returncode
        if pending['mutable']is not None:
            p=pending['mutable'];before=pending['pre_span'];data=p.read_bytes();at=before['offset']
            if len(data)!=before['bytes']or data[at:at+8].hex()!=before['expected']or hashlib.sha256(data[:at]+b'\0'*8+data[at+8:]).hexdigest()!=before['masked_sha256']:raise ValueError('ID patch changed outside independently reviewed8B span')
            binary=str(Path('/opt/toolchains/dc/sh-elf/bin').resolve());python=str(Path('/usr/bin/python3').resolve())
            contract['mutable_data']=[dict(pre_pin=pending['pre_mutable'],post_pin=tools.pin(p,'generated-mutable-data'),prechecked_and_reviewed_span_verified=True,aliases=[str(p)],readers=[python,str(Path(binary+'/sh-elf-objcopy').resolve()),str(Path(binary+'/sh-elf-nm').resolve())],writers=[python],read_flags=READ_FLAGS,write_flags=['O_WRONLY|O_CREAT|O_TRUNC|O_CLOEXEC'],reads=3,writes=1)]
        path=self.root/(name+'.strace');result=trace.validate(path.read_text(),contract)
        saved=dict(name=name,result=result,actual_returncode=returncode,contract=contract,ID_patch_span=pending['pre_span'])
        (self.root/(name+'-trace-contract.json.gz')).write_bytes(gzip.compress(json.dumps(saved,sort_keys=True).encode(),mtime=0))
        compressed=path.with_suffix('.strace.gz');compressed.write_bytes(gzip.compress(path.read_bytes(),mtime=0))
        if gzip.decompress(compressed.read_bytes())!=path.read_bytes():raise ValueError('trace compression equality')
        path.unlink();self.records.append(dict(name=name,result=result));self.pending=None
        return result


def compare_driver(a,b,owned_temp):
    pattern=re.compile(rb'"-plugin-opt=-fresolution=('+re.escape(str(owned_temp).encode())+rb'/cc[A-Za-z0-9]{6}\.res)"')
    ma=list(pattern.finditer(a));mb=list(pattern.finditer(b))
    if len(ma)!=1 or len(mb)!=1:return False
    for data,m in ((a,ma[0]),(b,mb[0])):
        token=m.group(1)
        if data.count(token)!=1:return False
        end=data.find(b'\n',m.start());line=data[data.rfind(b'\n',0,m.start())+1:end if end!=-1 else len(data)]
        if not line.lstrip().startswith(b'/opt/toolchains/dc/sh-elf/libexec/gcc/sh-elf/15.2.0/collect2 '):return False
    return a[:ma[0].start(1)]+b'<OWNED_TEMP>'+a[ma[0].end(1):]==b[:mb[0].start(1)]+b'<OWNED_TEMP>'+b[mb[0].end(1):]
