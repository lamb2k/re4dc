#!/usr/bin/env python3
"""Read-only selected-data attribution for Leon transitions / R100 shooting.
Emits metadata and absolute ISO LBA ranges, never payloads or game changes.
"""
import argparse,hashlib,json,struct,zlib
from pathlib import Path
import animation_cache_audit as cache

def u32(b,o):return struct.unpack_from('<I',b,o)[0]
def body(d):
    kind,n,_,off=struct.unpack_from('<4I',d,32)
    if kind or off+n>len(d):raise ValueError('native wrapper range')
    return d[off:off+n]
def directory(b):
    n=u32(b,0)
    if n>8192 or 16+n*8>len(b):raise ValueError('directory')
    return struct.unpack_from('<%dI'%n,b,16),[b[16+n*4+i*4:20+n*4+i*4]for i in range(n)]
def span(e,o,n):return dict(first_lba=e+o//2048,last_lba=e+(o+n-1)//2048,bytes=n)
def key_for(raw):
    f=2166136261
    for c in raw:f=((f^c)*16777619)&0xffffffff
    return '%08x-%08x'%(zlib.crc32(raw),f)
def effect_keys(b,slot,selected):
    offsets,tags=directory(b);eb=offsets[slot];h=struct.unpack_from('<12I',b,eb)
    if h[0]!=11:raise ValueError('EFF version')
    ids=eb+h[1];tpls=eb+h[6];n=u32(b,ids);refs={}
    if b'NTR\0'in tags:
        p=offsets[tags.index(b'NTR\0')]
        for i in range(u32(b,p+12)):
            rec,head,tpl=struct.unpack_from('<3I',b,p+32+12*i)
            refs[head]=(rec,tpl)
    out=[]
    for i in range(n):
        tid=struct.unpack_from('<H',b,ids+4+i*8)[0]
        if tid not in selected:continue
        tpl=tpls+u32(b,tpls+4+i*4);magic,count,desc=struct.unpack_from('<3I',b,tpl)
        if magic!=0x20af30:raise ValueError('TPL magic')
        for j in range(count):
            ih,ph=struct.unpack_from('<2I',b,tpl+desc+j*8);ih+=tpl
            ht,w,fmt,pixel=struct.unpack_from('<HHII',b,ih)
            if ih in refs:
                rec,tr=refs[ih];crc,fnv=struct.unpack_from('<2I',b,rec+8);key='%08x-%08x'%(crc,fnv);method='validated native identity record'
            else:
                if fmt not in (8,9):raise ValueError('raw texture needs reviewed indexed layout')
                ph+=tpl;pn=struct.unpack_from('<H',b,ph)[0];pf,pp=struct.unpack_from('<2I',b,ph+4)
                bw,bh=(8,8)if fmt==8 else(8,4);size=((w+bw-1)//bw)*((ht+bh-1)//bh)*32
                raw=struct.pack('<5I',w,ht,fmt,pf,pn*2)+b[tpl+pixel:tpl+pixel+size]+b[tpl+pp:tpl+pp+pn*2]
                key=key_for(raw);method='native_ui full_hash metadata + source indices + current palette'
            out.append(dict(tex_id=tid,pattern=j,width=w,height=ht,format=fmt,key=key,method=method))
    return out

def casing_keys(b):
    """Selected Ruger cartridge TPL (source WEP_ARC_PTR(9))."""
    offsets,tags=directory(b);tpl=offsets[9-4]
    if tags[9-4]!=b'TPL\0':raise ValueError('cartridge TPL tag')
    magic,count,desc=struct.unpack_from('<3I',b,tpl)
    if magic!=0x20af30:raise ValueError('cartridge TPL magic')
    refs={};p=offsets[tags.index(b'NTR\0')]
    for i in range(u32(b,p+12)):
        rec,head,_=struct.unpack_from('<3I',b,p+32+12*i);refs[head]=rec
    out=[]
    for j in range(count):
        ih,ph=struct.unpack_from('<2I',b,tpl+desc+8*j)
        ht,w,fmt,pixel=struct.unpack_from('<HHII',b,tpl+ih)
        if ph or fmt not in (3,14):raise ValueError('review changed cartridge layout')
        if tpl+ih not in refs:raise ValueError('cartridge requires selected native identity record')
        crc,fnv=struct.unpack_from('<2I',b,refs[tpl+ih]+8);key='%08x-%08x'%(crc,fnv)
        out.append(dict(archive='em/wep02.drs',role='cartridge-model',arc=9,
                        pattern=j,width=w,height=ht,format=fmt,key=key,
                        method='validated native identity record; raw placeholder pixels are not the texture identity'))
    return out


def raw_effect_sequence(b,slot,sequence):
    offsets,tags=directory(b);eb=offsets[slot];h=struct.unpack_from('<12I',b,eb);lst=eb+h[2];dat=eb+h[8]
    for i in range(u32(b,lst)):
        if struct.unpack_from('<H',b,lst+4+i*8)[0]!=sequence:continue
        head=dat+u32(b,dat+4+i*4);num=struct.unpack_from('<H',b,head)[0]
        if b'ESQ\0'in tags:raise ValueError('sequence parser requires ordinary selected weapon records')
        return [dict(effect_id=b[head+48+300*j+1],tex_id=b[head+48+300*j+2],time=struct.unpack_from('<H',b,head+48+300*j+4)[0])for j in range(num)]
    raise ValueError('sequence missing')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo',type=Path,required=True);p.add_argument('--source-root',type=Path,required=True)
    p.add_argument('--iso',type=Path,required=True);p.add_argument('--manifest',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();iso=cache.module(a.repo/'port/dreamcast/tools/d367/fullplay/fp_iso.py','fp_iso_read')
    tr=iso.Track(a.iso,45000);files={n.lstrip('/'):(e,s)for n,e,s in iso.files(tr)};manifest=json.loads(a.manifest.read_text())
    def read(name):
        e,n=files[name];d=tr.read_bytes(e,n)
        if manifest[name]['size']!=n or manifest[name]['sha256']!=cache.sha(d):raise ValueError('manifest '+name)
        return d
    em=cache.archive(read('em/em12.drs'),'em/em12.drs');wep=cache.archive(read('em/wep02.drs'),'em/wep02.drs')
    wb=body(read('em/wep02.drs'));cb=body(read('etc/core.das'));co,ct=directory(cb)
    fx=[dict(archive='em/wep02.drs',owner=0x36,**v)for v in effect_keys(wb,0,[0x21,0x22])]
    fx += [dict(archive='etc/core.das',owner=0,**v)for v in effect_keys(cb,ct.index(b'EFF\0'),[0x1e,0x1f])]
    fx += casing_keys(wb)
    life=co[0x7c//4-4]
    if cb[life:life+5]!=b'2.00\0' or ct[0x7c//4-4]!=b'UWF\0':raise ValueError('review changed HUD unit format')
    ammo_units=[dict(unit_id=cb[life+8+i*0x8c+4],tex_id=cb[life+8+i*0x8c+11])for i in range(cb[life+5])if cb[life+8+i*0x8c+4]in(0xb,0xa,0x17)]
    if len(ammo_units)!=3 or any(v['tex_id']!=0x27 for v in ammo_units):raise ValueError('review changed ammo digit binding')
    fx += [dict(archive='etc/core.das',role='hud-ammo-digit',source_uses_pattern=v['pattern']<10,**v)for v in effect_keys(cb,0x74//4-4,[0x27])]

    pe,pn=files['dc/tex.pak'];header=tr.read(pe);count,idx,dat=struct.unpack_from('<3I',header,12)
    if header[:8]!=b'RE4PAK1\0' or idx%2048:raise ValueError('texpack header')
    index=tr.read_bytes(pe+idx//2048,dat-idx)
    if zlib.crc32(index)!=u32(header,24):raise ValueError('texpack index CRC')
    pack={('%08x-%08x'%(c,f)):(o,n,i)for i,(c,f,o,n)in enumerate(struct.iter_unpack('<4I',index[:count*16]))}
    for f in fx:
        if f['key']not in pack:raise ValueError('effect key absent '+f['key'])
        o,n,i=pack[f['key']];f['texture_pack']=dict(offset=o,index_sector=pe+(idx+i*16)//2048,**span(pe,o,n))
    ge,gn=files['dc/native/ganado/ganado_lod.re4gl'];gh=tr.read(ge);levels=u32(gh,8);stride=(u32(gh,16)-64)//levels;ginfo=[]
    for level in [0,2]:
        rec=tr.read_bytes(ge,(level+1)*stride+64)[64+level*stride:64+(level+1)*stride]
        name=rec[:8].rstrip(b'\0').decode();o,n,skin=struct.unpack_from('<3I',rec,8)
        ginfo.append(dict(level=level,name=name,skin_bytes=skin,**span(ge,o*32,n)))
    paths=['src/game/cockpit.cpp','src/game/id_tex.cpp','src/game/id_sys.cpp','include/id_sys.h','src/game/obj10.cpp','port/dreamcast/game/model_bridge.cpp','port/dreamcast/game/ui_bridge.cpp','src/game/sscrn.cpp','src/game/pl_wep.cpp','src/game/read.cpp','src/game/pl_sub.cpp','src/game/pl_leon.cpp','src/game/pl_body.cpp','src/wep/pl_handgun.cpp','src/wep/objRuger.cpp','src/wep02/wep02.cpp','src/st1/r100.cpp','src/em10/em10.cpp','src/game/eff_sys.cpp','src/game/est.cpp','src/game/snd.cpp','src/game/snd_iss0.cpp','port/dreamcast/game/coarse_actor_leon_hands.inc','port/dreamcast/game/actor_pl08_pack_check.inc','port/dreamcast/game/coarse_ganado_lod.inc','port/dreamcast/game/platform/native_ui.cpp','port/dreamcast/game/platform/native_movie.cpp','port/dreamcast/game/platform/native_motion.cpp','port/dreamcast/game/platform/audio_aica.cpp']
    read_source=(a.source_root/'src/game/read.cpp').read_text();load=read_source[read_source.index('void ReadWepData(u32 no, u32 type)\n{'):]
    combat={hex(i):em['clips'].get(str(i))for i in [0x26,0x28,0x2a,0x2c,0x2e,0x30,0x32,0x33,0x35,0x37,0x39,0x49,0x51,0x67,0x6b,0x6c]}
    for clip in combat.values():
        if clip and clip['state'].startswith('cached-'):
            name='dc/mot/'+clip['key']+'.fcv';d=read(name)
            if key_for(d)!=clip['key'] or len(d)!=clip['bytes']:raise ValueError('FCV identity '+name)
            e,n=files[name];clip['disc_file']=dict(path=name,**span(e,0,n))
    head=cache.evaluate_set(em,[0x2c,0x2e,0x30])
    head['conclusion']='Conditional v2 three-cold working set across independently reacting actors; spill/pool/pressure and actual overlap decide reload risk, not strict-v3 overflow.'
    report=dict(schema='re4-transition-read-audit-v1',source_ref='9eb83d59; hashes pinned per file',iso=str(a.iso),manifest_sha256=cache.sha(a.manifest.read_bytes()),
        source=[dict(path=x,sha256=cache.sha((a.source_root/x).read_bytes()))for x in paths],
        r100_archive={k:v for k,v in em.items()if k!='clips'},weapon_archive={k:v for k,v in wep.items()if k!='clips'},
        damage_head_set=head,combat_literals=combat,
        archive_extents={n:span(files[n][0],0,files[n][1])for n in ['em/em12.drs','em/wep02.drs','etc/core.das']},
        texture_pack_index=dict(path='dc/tex.pak',manifest_identity=manifest['dc/tex.pak'],extent=pe,index_offset=idx,index_bytes=dat-idx,index_crc='%08x'%u32(header,24)),
        weapon_fire_sequence0=raw_effect_sequence(wb,0,0),ammo_hud_units=ammo_units,effect_texture_keys=fx,ganado_render_package=ginfo,
        weapon_guard=dict(set_before_release=load.index('oldWepId = no;')<load.index('ReleaseWepData();'),release_resets_old_id='oldWepId = 0xFF;'in read_source[read_source.index('void ReleaseWepData()\n{'):read_source.index('void re4dc_weapon_heap4_room_reset')],qualification='single current-archive guard; release resets key; no multi-weapon warm archive cache'),
        cautions=['R100Init pre-reads module12; first appearance may instead be lazy render package/texture/motion admission',
          'v2 three-cold-set finding is conditional on active actors and actual spill/pool/global pressure; not proof of fresh thrash',
          'muzzle source sequence and packed keys identify possible reads; first-use versus repeated loads requires actual counters',
          'absolute LBA is ISO9660 extent; drive FAD may add150; observer must verify its convention',
          'shot sound normal one-shot path queues resident bank samples; streaming bank/event admission paths remain separate'])
    assert any(v['key']=='951a629c-a43ebab7' and v.get('role')=='hud-ammo-digit' and v['pattern']==9 for v in fx)
    assert any(v['key']=='48c096e1-fcd52e2d' and v.get('role')=='hud-ammo-digit' and v['pattern']==8 for v in fx)
    assert len(report['weapon_fire_sequence0'])==9
    assert {x['tex_id']for x in report['weapon_fire_sequence0']}=={0,0x1e,0x1f,0x22,0xff}
    assert report['damage_head_set']['distinct_cold']==3 and not report['damage_head_set']['strict_two_slab_overflow']
    a.output.write_text(json.dumps(report,indent=2)+'\n');tr.f.close()
    print(json.dumps(dict(effect_patterns=len(fx),source_files=len(paths),guard=report['weapon_guard'],output=str(a.output))))
if __name__=='__main__':main()