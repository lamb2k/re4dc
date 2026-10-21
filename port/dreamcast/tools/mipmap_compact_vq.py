"""Mip-aware use of unused vectors in a newly losslessly compacted VQ base.

Referenced base vectors and the complete base index plane remain exact.
Only unused codebook slots may be replaced. Lower-level targets are native
16-bit or compact PAL4 mip planes, retaining their filter/alpha quantization.
This opt-in composition helper does not alter original accepted VQ assets.
"""
from __future__ import annotations

import collections
import hashlib
import math
import struct
import zlib

import convert_tpl as tpl
import mipmap_pal4 as pal4
import mipmap_twiddled as twiddled
import mipmap_vq as vq


def _features(vector, fmt):
    return tuple(c for w in vector for c in vq._feature(vq.rgba(w, fmt)))


def _distance(a, b):
    return sum((x-y)**2 for x,y in zip(a,b))


def reference_native(blob):
    if len(blob)<144:
        raise ValueError('short native mip reference')
    if tpl.TEXTURE.unpack_from(blob,48)[3]==tpl.FORMAT_PAL4_ARGB4444:
        return pal4.read_native_pal4(blob),tpl.FORMAT_ARGB4444
    native=twiddled.read_native_twiddled(blob)
    return native,native.texture[3]


def reference_decode(native,side):
    reader=pal4 if isinstance(native,pal4.NativePal4) else twiddled
    return reader.decode_level(native,side)


def reference_words(native,side):
    if isinstance(native,pal4.NativePal4):
        palette=struct.unpack('<16H',native.palette)
        if side==1:
            return (palette[native.payload[1]>>4],)
        off=pal4.level_offset(side)
        return tuple(palette[(b>>shift)&15] for b in native.payload[off:off+side*side//2]
                     for shift in (0,4))
    off=twiddled.level_offset(side)
    return struct.unpack('<%dH'%(side*side),native.payload[off:off+side*side*2])


def quality(reference, result):
    rows=[]
    for level in range(result.size.bit_length()):
        side=1 << level
        a=reference_decode(reference,side)
        b=vq.decode_level(result,side)
        count=side*side
        rgba=sum((p[c]-q[c])**2 for p,q in zip(a,b) for c in range(4))
        premul=sum(((p[c]*p[3]-q[c]*q[3])/255)**2 for p,q in zip(a,b) for c in range(3))
        alpha=sum((p[3]-q[3])**2 for p,q in zip(a,b))
        rows.append(dict(side=side,pixels=count,exact_rgba=a==b,
            rgba_rmse=math.sqrt(rgba/(count*4)),premultiplied_rgb_rmse=math.sqrt(premul/(count*3)),
            alpha_rmse=math.sqrt(alpha/count),
            max_alpha_error=max(abs(p[3]-q[3]) for p,q in zip(a,b)),
            reference_rgba_sha256=hashlib.sha256(bytes(c for p in a for c in p)).hexdigest(),
            candidate_rgba_sha256=hashlib.sha256(bytes(c for p in b for c in p)).hexdigest()))
    return rows


def add_mipmaps(base_blob, reference_blob, *, enabled=False, engine="auto"):
    base=vq.read_native_vq(base_blob)
    reference,reference_format=reference_native(reference_blob)
    if base.mipmapped or not reference.mipmapped:
        raise ValueError("expected a new VQ base and a native mip reference")
    if (base.texture[:3] != reference.texture[:3] or base.texture[3]!=reference_format or
            base.texture[6] != reference.texture[6] & ~tpl.FLAG_MIPMAP or
            base.header[9:] != reference.header[9:]):
        raise ValueError("base/reference material, dimensions, format, alpha or header flags differ")
    if vq.decode_level(base,base.size) != reference_decode(reference,reference.size):
        raise ValueError("reference has a different full-resolution RGBA base")
    used=sorted(set(base.base_indices))
    report=dict(enabled=bool(enabled),changed=False,width=base.size,height=base.size,
        format=base.texture[3],source_package_sha256=hashlib.sha256(base_blob).hexdigest(),
        reference_package_sha256=hashlib.sha256(reference_blob).hexdigest(),
        source_codebook_sha256=hashlib.sha256(base.codebook).hexdigest(),
        used_base_vectors=len(used),unused_codebook_slots=256-len(used),
        base_indices_sha256=hashlib.sha256(base.base_indices).hexdigest(),
        before_payload_bytes=len(base.payload),exact_base_rgba=True,exact_base_alpha=True,
        referenced_base_codebook_exact=True,sampler_policy="existing package mip bit; original dimensions, UVs, wrap and sampler configuration retained")
    if not enabled:
        report.update(reason="disabled",after_payload_bytes=len(base.payload),extra_payload_bytes=0)
        return base_blob,report
    fmt=base.texture[3]
    words=struct.unpack("<1024H",base.codebook)
    book=[tuple(words[i:i+4]) for i in range(0,1024,4)]
    free=[i for i in range(256) if i not in used]
    old_vectors={book[i] for i in used}
    active=[_features(book[i],fmt) for i in used]
    targets=collections.Counter()
    for level in range(1,base.size.bit_length()-1):
        side=1 << level
        row=reference_words(reference,side)
        targets.update(tuple(row[i:i+4]) for i in range(0,len(row),4))
    # The single-pixel mip only samples BR. Reserve an exact BR when possible;
    # no other word of that vector is required by this mip's hardware contract.
    one=reference_words(reference,1)[0]
    if not any(book[i][3]==one for i in used) and free:
        index=free.pop(0)
        book[index]=(one,)*4
        active.append(_features(book[index],fmt))
    candidates=sorted(vector for vector in targets if vector not in old_vectors)
    features=[_features(q,fmt) for q in candidates]
    errors=[min(_distance(f,b) for b in active) for f in features]
    # Deterministic weighted farthest residual. Each target represents a 2x2
    # native mip block; repeated blocks receive their actual occurrence weight.
    # This uses spare entries without quantizing or moving any base vector.
    added=0
    while free and candidates:
        choice=max(range(len(candidates)),key=lambda i:errors[i]*targets[candidates[i]])
        if errors[choice]==0:
            break
        index=free.pop(0)
        book[index]=candidates[choice]
        added+=1
        chosen=features[choice]
        errors=[min(error,_distance(f,chosen)) for f,error in zip(features,errors)]
    feature_book=[_features(q,fmt) for q in book]
    levels={base.size:base.base_indices}
    for level in range(base.size.bit_length()-1):
        side=1 << level
        pixels=[vq._feature(p) for p in reference_decode(reference,side)]
        levels[side],_=vq._encode_level(pixels,side,feature_book,engine)
    payload=b"".join(struct.pack("<4H",*q) for q in book)+b"".join(
        levels[1 << i] for i in range(base.size.bit_length()))
    h,t=list(base.header),list(base.texture)
    t[5],t[6],h[7]=len(payload),t[6]|tpl.FLAG_MIPMAP,len(payload)
    body=tpl.TEXTURE.pack(*t)+payload
    h[8]=zlib.crc32(body if base.crc_rule=="header" else payload)&0xffffffff
    result=tpl.HEADER.pack(*h)+body
    checked=vq.read_native_vq(result)
    if checked.base_indices != base.base_indices or any(
            checked.codebook[i*8:i*8+8] != base.codebook[i*8:i*8+8] for i in used):
        raise ValueError("referenced full-resolution codebook vector or index changed")
    if vq.decode_level(checked,checked.size) != vq.decode_level(base,base.size):
        raise ValueError("mip composition changed the original full-resolution RGBA")
    metrics=quality(reference,checked)
    report.update(changed=True,reason="unused-slots-for-native-mip-targets",spare_vectors_added=added,
        after_payload_bytes=len(payload),extra_payload_bytes=len(payload)-len(base.payload),
        package_sha256=hashlib.sha256(result).hexdigest(),
        full_codebook_exact=checked.codebook==base.codebook,
        unused_slots_changed=sum(book[i]!=tuple(words[4*i:4*i+4]) for i in range(256) if i not in used),
        exact_all_reference_levels=all(r["exact_rgba"] for r in metrics),
        lower_level_quality=metrics,
        lower_level_quality_scope="Against the supplied filtered/quantized native mip reference, not a console screenshot or perceptual acceptance.")
    return result,report
