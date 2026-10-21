"""Stored texture residency accounting includes every mip and palette tail."""
import pathlib
import struct
import sys
import tempfile
import unittest
import zlib

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from assetpipe import texture
import convert_tpl as tpl
import mipmap_pal4
import mipmap_twiddled
import mipmap_vq
import test_mipmap_pal4 as pal4_fixture
import test_mipmap_twiddled as twiddled_fixture
import test_mipmap_vq as vq_fixture


class StoredMipAccounting(unittest.TestCase):
    def read(self,data):
        with tempfile.TemporaryDirectory() as directory:
            path=pathlib.Path(directory)/'texture.re4tex';path.write_bytes(data)
            return texture.read_re4tex(path)

    def packages(self):
        yield twiddled_fixture.native(16),mipmap_twiddled
        yield vq_fixture.native(16),mipmap_vq
        yield pal4_fixture.package(16),mipmap_pal4

    def test_full_chains_count_stored_payload_in_all_three_native_families(self):
        for original,converter in self.packages():
            chain,_=converter.add_mipmaps(original,enabled=True,engine='python')
            row=self.read(chain)
            self.assertEqual(row['vram_bytes'],len(chain)-144)
            self.assertEqual(row['textures'][0]['vram_bytes'],row['textures'][0]['data_bytes'])
            self.assertGreater(row['vram_bytes'],self.read(original)['vram_bytes'])

    def test_original_nonmip_reports_keep_their_previous_byte_values(self):
        for original,_ in self.packages():
            d=tpl.TEXTURE.unpack_from(original,48)
            expected=(d[1]*d[2]//2+32 if d[3]==4 else texture.vram_bytes('vq' if d[7]==2 else 'twiddled',d[1],d[2]))
            self.assertEqual(self.read(original)['vram_bytes'],expected)

    def test_multiple_chain_descriptors_sum_payload_not_headers_or_allocator_rounding(self):
        a,_=mipmap_pal4.add_mipmaps(pal4_fixture.package(8),enabled=True,engine='python')
        b,_=mipmap_vq.add_mipmaps(vq_fixture.native(16),enabled=True,engine='python')
        payloads=[a[144:],b[144:]];descriptors=[];offset=48+2*96
        for blob,payload in zip((a,b),payloads):
            t=list(tpl.TEXTURE.unpack_from(blob,48));t[4]=offset
            descriptors.append(tpl.TEXTURE.pack(*t));offset+=len(payload)
        body=b''.join(descriptors+payloads)
        packed=tpl.HEADER.pack(tpl.MAGIC,2,48,96,2,48,240,sum(map(len,payloads)),zlib.crc32(body)&0xffffffff,1,0)+body
        result=self.read(packed)
        self.assertEqual(result['vram_bytes'],sum(map(len,payloads)))
        self.assertNotEqual(result['vram_bytes'],len(packed))
        self.assertNotEqual(result['vram_bytes'],sum((len(p)+31)&~31 for p in payloads))


if __name__=='__main__':unittest.main()
