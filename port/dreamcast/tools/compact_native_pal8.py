"""Opt-in exact square ARGB4444 -> PAL8 base/chain compatibility candidate.

No resampling or re-quantization: each existing native16 word becomes a palette
index. Grayscale+alpha uses a canonical256-color palette shared across frames.
Runtime format5 admission is a separate default-off implementation/gate.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import struct
import zlib
import convert_tpl as tpl
import mipmap_twiddled as tw
import mipmap_vq as vq

FORMAT_PAL8_ARGB4444=tpl.FORMAT_PAL8_ARGB4444


def chain_bytes(side):return side*side*4//3+3


def level_offset(side):return 3 if side==1 else chain_bytes(side//2)


@dataclass(frozen=True)
class NativePal8:
    header:tuple
    texture:tuple
    payload:bytes
    crc_rule:str
    @property
    def size(self):return self.texture[1]
    @property
    def mipmapped(self):return bool(self.texture[6]&tpl.FLAG_MIPMAP)
    @property
    def palette(self):return self.payload[-512:]
    @property
    def base_indices(self):
        at=level_offset(self.size) if self.mipmapped else 0
        return self.payload[at:at+self.size*self.size]


def read_native_pal8(blob):
    if len(blob)<144:raise ValueError('short native PAL8 package')
    h=tpl.HEADER.unpack_from(blob);t=tpl.TEXTURE.unpack_from(blob,48)
    if (h[:6]!=(tpl.MAGIC,tpl.VERSION,48,96,1,48) or h[6]!=144 or h[6]+h[7]!=len(blob)
            or t[4]!=144 or t[3]!=FORMAT_PAL8_ARGB4444 or t[7]!=tpl.PAYLOAD_TWIDDLED or t[8]
            or t[6]&(1<<30) or not 8<=t[1]<=1024 or t[1]!=t[2] or t[1]&(t[1]-1)):
        raise ValueError('expected canonical square twiddled PAL8 ARGB4444')
    expected=(chain_bytes(t[1]) if t[6]&tpl.FLAG_MIPMAP else t[1]*t[2])+512
    if t[5]!=expected or h[7]!=expected:raise ValueError('PAL8 index/palette-tail length differs')
    if h[8]==zlib.crc32(blob[48:])&0xffffffff:rule='header'
    elif h[8]==zlib.crc32(blob[144:])&0xffffffff:rule='data'
    else:raise ValueError('native PAL8 CRC differs')
    return NativePal8(h,t,blob[144:],rule)


def decode_words(native,side):
    if side<1 or side>native.size or side&(side-1) or side!=native.size and not native.mipmapped:
        raise ValueError('invalid PAL8 mip level')
    palette=struct.unpack('<256H',native.palette)
    at=level_offset(side) if native.mipmapped else 0
    indices=native.payload[at:at+side*side]
    order=tpl.twiddle_16bpp(list(range(side*side)),side,side)
    result=[0]*(side*side)
    for i,linear in enumerate(order):result[linear]=palette[indices[i]]
    return result


def decode_level(native,side):return [vq.rgba(w,tpl.FORMAT_ARGB4444) for w in decode_words(native,side)]


def compact(blob,*,enabled=False):
    source=tw.read_native_twiddled(blob)
    if source.texture[3]!=tpl.FORMAT_ARGB4444:raise ValueError('PAL8 exact packing currently accepts ARGB4444 only')
    words=struct.unpack('<%dH'%(len(source.payload)//2),source.payload)
    unique=sorted(set(words));gray=all(((w>>8)&15)==((w>>4)&15)==(w&15) for w in unique)
    before=len(source.payload);after=len(words)+512
    report=dict(enabled=bool(enabled),changed=False,source_package_sha256=hashlib.sha256(blob).hexdigest(),
        width=source.size,height=source.size,mipmapped=source.mipmapped,distinct_native_words=len(unique),
        before_payload_bytes=before,after_payload_bytes=before,
        canonical_grayscale_alpha_palette=gray,source_full_chain_words_exact=True,
        runtime_scope='Experimental native format5 PAL8 path requires its own default-off admission and aligned palette-bank gates.')
    reason='disabled' if not enabled else 'too-many-colors' if len(unique)>256 else 'prefer-existing-PAL4' if len(unique)<=16 else 'no-payload-request-win' if (after+31)//32>=(before+31)//32 else None
    if reason:
        report.update(reason=reason)
        return blob,report
    palette=[(a<<12)|(g<<8)|(g<<4)|g for a in range(16) for g in range(16)] if gray else unique+[0]*(256-len(unique))
    lookup={w:i for i,w in reversed(list(enumerate(palette)))}
    payload=bytes(lookup[w] for w in words)+struct.pack('<256H',*palette)
    h,t=list(source.header),list(source.texture);t[3],t[5],h[7]=FORMAT_PAL8_ARGB4444,len(payload),len(payload)
    body=tpl.TEXTURE.pack(*t)+payload
    h[8]=zlib.crc32(body)&0xffffffff
    result=tpl.HEADER.pack(*h)+body;checked=read_native_pal8(result)
    levels=range(source.size.bit_length()) if source.mipmapped else [source.size.bit_length()-1]
    for i in levels:
        side=1<<i
        if decode_level(checked,side)!=tw.decode_level(source,side):raise ValueError('PAL8 changed a native mip RGBA/alpha level')
    report.update(changed=True,reason='exact-native-word-palette-indices',after_payload_bytes=len(payload),
        payload_saved_bytes=before-len(payload),palette_sha256=hashlib.sha256(checked.palette).hexdigest(),
        package_sha256=hashlib.sha256(result).hexdigest(),format=FORMAT_PAL8_ARGB4444,
        base_RGBA_alpha_exact=True,all_existing_mip_levels_RGBA_alpha_exact=True,
        dimensions_material_header_flags_exact=True,palette_entries=256,
        palette_allocation_contract='One aligned block of 16 PAL4 banks; only exact identical 256-color palettes may share the block.')
    return result,report
