#!/usr/bin/env python3
"""One alpha-native batch: conversion, decoded BASE policy gate, held records separate."""
from pathlib import Path
from array import array
import argparse,collections,ctypes,hashlib,importlib,json,math,random,shutil,struct,sys,time,zlib
HERE=Path(__file__).resolve().parent;TOOLS=HERE.parents[1];sys.path[:0]=[str(HERE),str(TOOLS),str(TOOLS/'d367')]
import compact_alpha as compact,convert_tpl as tpl,mipmap_vq as vq,mipmap_twiddled as tw,rectangular_vq as rect,scoped_candidate as scoped,tr_classify as classifier
sha=lambda b:hashlib.sha256(b).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--evidence',type=Path,required=True);a=p.parse_args();O,E=a.out,a.evidence;assert set(x.name for x in O.iterdir())=={'nearest64.so','alpha-metric.so'};assert E.exists();cap=8*1024**2;floor=18*1024**3+64*1024**2;assert shutil.disk_usage('/mnt/c').free>=floor+cap
 def size(root):return sum(x.stat().st_size for x in root.rglob('*')if x.is_file())
 def guard(extra=0):assert 2*(size(O)+extra)+size(E)+524288<cap and shutil.disk_usage('/mnt/c').free>=floor,('resource',size(O),size(E),extra)
 def write(path,b):
  guard(len(b));path.parent.mkdir(parents=True,exist_ok=True)
  with path.open('xb')as f:f.write(b)
 def emit(path,d):write(path,(json.dumps(d,indent=2)+'\n').encode())
 R=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/texture-rect21-20261021');I=R/'native-bindings-01/bindings.json';bind=json.loads(I.read_text());assert sha(I.read_bytes())=='e24a1ee4150c91f1228879f92bb9e6e934176fc6d3c1011f45c265ea8d606003';A=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/texture-consumers21-native-coverage-20261021/remaining756-keys.json');rows=sorted([x for x in json.loads(A.read_text())if x['format']in(1,2)],key=lambda x:(x['format'],x['layout'],x['height'],x['width'],x['key']));assert len(rows)==142 and sum(x['material_refs']for x in rows)==508
 P=Path('/root/re4data/private/mipmap21-release21-pack-recovery-20261021/tex.pak');raw=P.read_bytes();assert sha(raw)=='18fcee11491f2c1f212863d6d6b572b3997f691b2e990217e1c2518f134021ef';v,n,ioff,doff,crc=struct.unpack_from('<5I',raw,8);index={tuple(struct.unpack_from('<4I',raw,ioff+16*i)[:2]):struct.unpack_from('<4I',raw,ioff+16*i)[2:]for i in range(n)}
 current=Path('/root/re4data/private/texture-canonical1004-20261021/tex.pak')
 with current.open('rb')as f:h=f.read(2048);v,n,ioff,doff,crc=struct.unpack_from('<5I',h,8);f.seek(ioff);idx=f.read(n*16)
 occupied={tuple(struct.unpack_from('<4I',idx,16*i)[:2])for i in range(n)}|{(0x3662c0aa,0xc9e71c00),(0xfefdf580,0xf15c1f47)}
 prior_names=['texture-rect21-next415-20261021-v1','texture-rect21-next177-20261022-v2','texture-rect21-next4-vertical-20261022-v1','texture-rect21-next18-twiddled-20261022-v1'];priorpins={}
 for name in prior_names:
  q=Path('/root/re4data/private')/name/'conversion-receipt.json';b=q.read_bytes();priorpins[str(q)]=sha(b);occupied.update(tuple(int(z,16)for z in x['scoped_key'].split('-'))for x in json.loads(b)['selected'])
 coverage=Path('/root/re4data/private/mipmap21-fullpack-core-pairs-coverage-20261021/coverage.json');cov=json.loads(coverage.read_text());occupied.update(tuple(int(z,16)for z in x['key'].split('-'))for x in cov['loose_and_quality_rows'])
 # Independent decoded source/base/mip functions, both native layouts and both alpha formats.
 oracle=R/'oracle-02/oracle.so';L=ctypes.CDLL(str(oracle));V=L.rect_oracle_decode;T=ctypes.CDLL('/root/re4data/private/texture-rect21-next18-twiddled-20261022-v1/rect-twiddled-oracle.so').rect_oracle_decode
 for f in(V,T):f.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_uint,ctypes.c_uint,ctypes.c_uint,ctypes.c_void_p,ctypes.c_size_t]
 decoders={2:L.mipmap_oracle_decode,1:L.mipmap_oracle_decode_twiddled}
 for f in decoders.values():f.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_uint,ctypes.c_uint,ctypes.c_int,ctypes.c_uint,ctypes.c_void_p,ctypes.c_size_t]
 def pixels(blob,w,h):
  hd=tpl.HEADER.unpack_from(blob);t=tpl.TEXTURE.unpack_from(blob,48);payload=blob[t[4]:t[4]+t[5]];buf=(ctypes.c_ubyte*(4*w*h))();assert({2:V,1:T}[t[7]])(payload,len(payload),t[3],w,h,buf,len(buf))==len(buf);return bytes(buf)
 filter_controls=[]
 for fmt,transparent_red,opaque_green,expected_alpha in[(1,0x7c00,0x83e0,255),(2,0x0f00,0xf0f0,136)]:
  words=tpl.twiddle_16bpp([transparent_red if x%2==0 else opaque_green for y in range(16)for x in range(32)],32,16);payload=struct.pack('<512H',*words);tx=[bytes(64),32,16,fmt,144,len(payload),0,1,0];body=tpl.TEXTURE.pack(*tx)+payload;hd=[tpl.MAGIC,tpl.VERSION,48,96,1,48,144,len(payload),zlib.crc32(body)&0xffffffff,0,0];source=tpl.HEADER.pack(*hd)+body;src=pixels(source,32,16);assert compact.shorter_square(source,src)==source;compact_base=compact.shorter_square(source,src,enabled=True);got=pixels(compact_base,16,16);assert got==bytes([0,255,0,expected_alpha])*256
  mx=1 if fmt==1 else 15;scale=255 if fmt==1 else 17;old=classifier.tex_class((dict(collections.Counter(x//scale for x in src[3::4])),mx));new=classifier.tex_class((dict(collections.Counter(x//scale for x in got[3::4])),mx));assert old!=new;assert classifier.part_class(0,False,old)==classifier.part_class(0,False,new)=='OP';assert classifier.part_class(2,False,old)!=classifier.part_class(2,False,new);assert classifier.part_class(2,True,old)==classifier.part_class(2,True,new)=='VA';filter_controls.append(dict(format=fmt,hidden_transparent_red_does_not_bleed=True,expected_base_alpha=expected_alpha,texture_class_before=old,texture_class_after=new,actual_part_policy_OP_VA_equal_TRdiffers=True,default_off_byteexact=True))
 lib=ctypes.CDLL(str(O/'nearest64.so'));fn=lib.rect21_nearest64;fn.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_void_p,ctypes.c_size_t,ctypes.c_size_t,ctypes.c_void_p];original=vq._nearest
 def fast(targets,book,engine):
  if engine!='rect21_c64':return original(targets,book,engine)
  if not targets:return [],engine
  aa=array('i',(c for x in targets for c in x));bb=array('i',(c for x in book for c in x));assert aa.itemsize==bb.itemsize==4;A=(ctypes.c_int32*len(aa)).from_buffer(aa);B=(ctypes.c_int32*len(bb)).from_buffer(bb);out=(ctypes.c_ubyte*len(targets))();assert fn(A,len(targets),B,len(book),len(targets[0]),out)==0;return list(out),engine
 vq._nearest=fast
 metric=ctypes.CDLL(str(O/'alpha-metric.so')).alpha_metric;metric.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_uint,ctypes.c_uint,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p];rng=random.Random(22142);metric_controls=[]
 for ratio in(2,4,8):
  side=8;w=side*ratio;src=bytes(rng.randrange(256)for _ in range(w*side*4));dst=bytes(rng.randrange(256)for _ in range(side*side*4));sse=(ctypes.c_uint64*4)();maximum=(ctypes.c_uint*4)();cross=ctypes.c_uint();assert metric(src,dst,w,side,sse,maximum,ctypes.byref(cross))==0;d=[[]for _ in range(4)];cross_ref=0;den=2*ratio
  for y in range(side):
   for x in range(w):
    q=rect.sample(dst,side,side,(x+.5)/w,(y+.5)/side)
    for c in range(4):d[c].append(round(den*(src[(y*w+x)*4+c]-q[c])))
    cross_ref+=((src[(y*w+x)*4+3]>=128)!=(q[3]>=128))
  assert list(sse)==[sum(z*z for z in x)for x in d]and list(maximum)==[max(map(abs,x))for x in d]and cross.value==cross_ref;metric_controls.append(dict(ratio=ratio,pixels=w*side,RGBAmetric_and_coverage_exact=True))
 # Verified original metadata bytes; absent profiles remain explicit held reasons.
 files=json.loads((R/'image-plan-04/baseline-file-identities.json').read_text())['files'];metadata={};meta_receipts=[];BISO=R/'standalone-B-01/gdemu/track03.iso'
 with BISO.open('rb')as f:
  for x in bind['matched_worlds']:
   room=x['path'].split('/')[2];original_world=(R/'native-bindings-01/inputs'/x['path']).read_bytes();assert sha(original_world)==x['sha256'];wh=struct.unpack_from('<4s7I',original_world);path='/dc/native/'+room+'/ps2-world.r4tc';m=files.get(path)
   if not m:metadata[room]=None;meta_receipts.append(dict(room=room,status='MISSING_ORIGINAL_R4TC',world_original_crc=wh[5]));continue
   f.seek((m['extent']-45000)*2048);b=f.read(m['bytes']);assert sha(b)==m['sha256'];h=struct.unpack_from('<4s5I',b);assert h[:3]==(b'R4TC',1,1)and h[3]==wh[3]and h[4]==wh[5]and h[5]==zlib.crc32(b[24:24+h[3]])&0xffffffff;assert len(b)==24+((h[3]+3)&~3);metadata[room]=b[24:24+h[3]];write(O/'inputs/metadata'/room/'ps2-world.r4tc',b);meta_receipts.append(dict(room=room,status='EXACT_ORIGINAL_R4TC',bytes=len(b),sha256=sha(b),header_hex=b[:24].hex(),extent=m['extent'],world_original_crc=wh[5]))
 emit(O/'original-metadata.json',dict(ISO_prior_whole_identity='e9efca156ff9b11005af57688accc085c9e568ceef32c2085e8a2d8f789db434; individual metadata FULL SHA freshly checked',files=meta_receipts))
 started=time.monotonic();results=[];held=[];qualified=[];class_checks=[];controls=[];images=[]
 from PIL import Image,ImageDraw
 for row in rows:
  key=tuple(int(z,16)for z in row['key'].split('-'));off,n=index[key];blob=raw[off:off+n];assert sha(blob)==row['source_package_sha256'];head=tpl.HEADER.unpack_from(blob);t=tpl.TEXTURE.unpack_from(blob,48);w,side,fmt=t[1:4];layout=t[7];assert(fmt,layout,t[6])==(row['format'],row['layout'],0)
  refs=bind['bindings'][row['key']];assert len(refs)==row['material_refs']and all(x['width']==w and x['height']==side and x['render_pass']in(0,1,2)and x['flags']in(0,1)for x in refs)
  before=pixels(blob,w,side);assert compact.shorter_square(blob,before)==blob;base=compact.shorter_square(blob,before,enabled=True,engine='rect21_c64');module={2:vq,1:tw}[layout];candidate,_=module.add_mipmaps(base,enabled=True,engine='rect21_c64');native=module.read_native_vq(candidate)if layout==2 else module.read_native_twiddled(candidate);after=pixels(base,side,side);assert native.texture[3]==fmt and native.texture[6]==4 and native.texture[7]==layout and native.header[8]==zlib.crc32(candidate[48:])&0xffffffff
  if layout==2:assert native.codebook==blob[144:2192]
  levels=[]
  for level in range(side.bit_length()):
   s=1<<level;buf=(ctypes.c_ubyte*(s*s*4))();assert decoders[layout](native.payload,len(native.payload),fmt,side,1,level,buf,len(buf))==len(buf);expected=bytes(c for px in module.decode_level(native,s)for c in px);assert bytes(buf)==expected;aa=bytes(buf)[3::4];levels.append(dict(side=s,alpha_min=min(aa),alpha_max=max(aa),alpha_histogram=dict(collections.Counter(aa)),decoded_RGBA_sha256=sha(bytes(buf))))
  control=(fmt,layout,side,w//side)
  if control not in{tuple(x['class_'])for x in controls}:
   reference=compact.shorter_square(blob,before,enabled=True,engine='python');rm,_=module.add_mipmaps(reference,enabled=True,engine='python');assert reference==base and rm==candidate;controls.append(dict(class_=list(control),key=row['key'],base_and_all_mips_byteexact_reference=True))
  mx=1 if fmt==1 else 15;scale=255 if fmt==1 else 17;ah=collections.Counter(x//scale for x in before[3::4]);bh=collections.Counter(x//scale for x in after[3::4]);assert all(x%scale==0 for x in before[3::4]+after[3::4]);source_class=classifier.tex_class((dict(ah),mx));candidate_class=classifier.tex_class((dict(bh),mx));checks=[]
  for ref in refs:
   room=ref['world'].split('/')[2];p=ref['part'];expected=metadata[room][p]if metadata[room]is not None else None;source_code=classifier.CODE[classifier.part_class(ref['render_pass'],bool(ref['flags']&1),source_class)];candidate_code=classifier.CODE[classifier.part_class(ref['render_pass'],bool(ref['flags']&1),candidate_class)];checks.append(dict(room=room,part=p,pass_=ref['render_pass'],VA=bool(ref['flags']&1),shipped_class=expected,source_class=source_code,candidate_class=candidate_code,qualified=expected is not None and expected==source_code==candidate_code))
  ok=all(x['qualified']for x in checks);new=scoped.scoped_key(key,sha(candidate));assert new not in occupied;occupied.add(new);newkey='%08x-%08x'%new;relative='textures/'+newkey+'.re4tex';write(O/relative,candidate)
  sse=(ctypes.c_uint64*4)();maximum=(ctypes.c_uint*4)();cross=ctypes.c_uint();assert metric(before,after,w,side,sse,maximum,ctypes.byref(cross))==0;den=2*w//side;count=w*side;coords=[(-2.0001,-.0001),(-1.,1.),(0.,0.),(.5,.5),(.9999,1.0001),(3.125,-2.75)]+[(rng.uniform(-8,8),rng.uniform(-8,8))for _ in range(26)];pe=max(max(abs(x-y)for x,y in zip(rect.sample(after,side,side,u,v),rect.sample(after,side,side,u+3,v-2)))for u,v in coords);assert pe<1e-8
  res=dict(original_key=row['key'],scoped_key=newkey,relative_path=relative,logical=[w,side],physical=[side,side],uv_scale=[1.,1.],format=fmt,flags=4,payload_type=layout,source_flags=0,source_package_sha256=sha(blob),candidate_sha256=sha(candidate),candidate_crc32=native.header[8],source_payload=t[5],candidate_payload=len(native.payload),source_request_rounded=(t[5]+31)&~31,candidate_request_rounded=(len(native.payload)+31)&~31,package_bytes=len(candidate),original_VQ_codebook_exact=layout==2,base_exact=False,decoded_levels=levels,alpha_source_histogram=dict(ah),alpha_base_histogram=dict(bh),alpha_native_max=mx,source_texture_class=source_class,candidate_texture_class=candidate_class,source_center_RGBA_RMSE=[math.sqrt(x/(den*den*count))for x in sse],source_center_RGBA_max=[x/den for x in maximum],source_center_alpha128_coverage_disagreements=cross.value,periodic_probes=len(coords),periodic_max_error=pe,world_refs=refs,policy_qualified=ok)
  results.append(res);class_checks.append(dict(original_key=row['key'],scoped_key=newkey,source_texture_class=source_class,candidate_texture_class=candidate_class,qualified=ok,refs=checks))
  if ok:qualified.append(res)
  else:held.append(dict(key=row['key'],candidate_key=newkey,reasons=[x for x in checks if not x['qualified']]))
  if len(images)<8 and((fmt,layout)not in{x[0]for x in images}or len(images)<2):
   im=Image.new('RGBA',(384,100),'#303030');ImageDraw.Draw(im).text((2,2),row['key']+' '+str(fmt)+'/'+str(layout)+' '+source_class+'->'+candidate_class,fill='white');im.alpha_composite(Image.frombytes('RGBA',(w,side),before).resize((128,64)),(0,28));im.alpha_composite(Image.frombytes('RGBA',(side,side),after).resize((128,64)),(128,28));low=Image.new('RGBA',(max(1,side//2),max(1,side//2)));low.putdata(module.decode_level(native,max(1,side//2)));im.alpha_composite(low.resize((128,64)),(256,28));images.append(((fmt,layout),im))
  if len(results)%25==0 or len(results)==len(rows):print(json.dumps(dict(converted=len(results),policy_qualified=len(qualified),held=len(held),seconds=round(time.monotonic()-started,3))),flush=True)
 report=dict(schema='ALPHA142_NATIVE_PREMULTIPLIED_V1',status='CONVERTED_PRIVATE_POLICY_COUNTS_SEPARATE',source_pack_sha256=sha(raw),bindings_sha256=sha(I.read_bytes()),remaining_inventory_sha256=sha(A.read_bytes()),classifier_source_sha256=sha(Path(classifier.__file__).read_bytes()),prior_receipt_pins=priorpins,selected=results,converted_keys=len(results),material_refs=sum(len(x['world_refs'])for x in results),policy_qualified_keys=len(qualified),policy_held_keys=len(held),held=held,source_request_bytes=sum(x['source_request_rounded']for x in results),candidate_request_bytes=sum(x['candidate_request_rounded']for x in results),independent_C_mip_levels=sum(len(x['decoded_levels'])for x in results),dimension_format_layout_controls=controls,metric_controls=metric_controls,premultiplied_filter_controls=filter_controls,conversion_seconds=time.monotonic()-started,limits=['Base and loweralpha are filtered/quantized approximations; no visual acceptance.','All142 converted and preserved; policyqualified/held are separate and all508aliases checked against exact original shippedR4TCbytes. No restamp.','VQoriginalbook/nativefmt preserved; TWIDlayout/nativefmt preserved; flags0 retained plusonlymip4, UV1,1.','IndependentCBASEhist feeds actual unchangedtex_class/part_class functions, never mip-unaware Tex.alpha(candidate).','No Package/world admission claimed yet; one sharedhostgate follows. No runtime/fullpack/programme/image/guest changes.'])
 emit(O/'conversion-receipt.json',report);emit(O/'policy-classification.json',dict(status='EXACT_SHIPPED_CLASS_GATE',checks=class_checks,total_refs=sum(len(x['refs'])for x in class_checks),qualified_refs=sum(len(x['refs'])for x in class_checks if x['qualified']),held_keys=len(held),original_metadata_sha256=sha((O/'original-metadata.json').read_bytes())))
 q=dict(report);q.update(selected=qualified,converted_keys=len(qualified),material_refs=sum(len(x['world_refs'])for x in qualified),held=[],policy_gate_source_and_candidate_equal_shipped_R4TC=True);emit(O/'policy-qualified-receipt.json',q)
 if images:
  sheet=Image.new('RGBA',(384,100*len(images)),'#303030')
  for n,(_,im)in enumerate(images):sheet.alpha_composite(im,(0,100*n))
  sheet.save(O/'contact-sample.png');guard()
 print(json.dumps({k:report[k]for k in('converted_keys','material_refs','policy_qualified_keys','policy_held_keys','independent_C_mip_levels','source_request_bytes','candidate_request_bytes','conversion_seconds')}),flush=True)
if __name__=='__main__':main()