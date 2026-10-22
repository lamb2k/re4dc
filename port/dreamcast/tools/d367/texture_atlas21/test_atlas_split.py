import struct
import unittest
import zlib
import atlas_split as atlas


class AtlasTests(unittest.TestCase):
    def test_crop_from_legacy_crc_emits_canonical_body_crc(self):
        payload=bytes(i&255 for i in range(2048))+bytes((i*37)&255 for i in range(65536))
        descriptor=atlas.tpl.TEXTURE.pack(b'synthetic-tile',512,512,
            atlas.tpl.FORMAT_RGB565,144,len(payload),0,atlas.tpl.PAYLOAD_VQ,0)
        body=descriptor+payload
        def package(crc):
            return atlas.tpl.HEADER.pack(atlas.tpl.MAGIC,atlas.tpl.VERSION,
                48,96,1,48,144,len(payload),crc,1,0)+body
        canonical=package(zlib.crc32(body))
        legacy=package(zlib.crc32(payload))
        self.assertEqual(atlas.mip.read_native_vq(legacy).crc_rule,'data')
        from_canonical=atlas.crop_vq(canonical,(384,256,128))
        from_legacy=atlas.crop_vq(legacy,(384,256,128))
        self.assertEqual(from_legacy,from_canonical)
        self.assertEqual(struct.unpack_from('<I',from_legacy,36)[0],
            zlib.crc32(from_legacy[48:]))
        self.assertEqual(atlas.mip.read_native_vq(from_legacy).crc_rule,'header')
        self.assertEqual(from_legacy[144:2192],payload[:2048])

    def test_source_uv_texel_coordinates_are_exact_under_power_of_two_map(self):
        rect=(384,256,128)
        for u in range(384*64,512*64,53):
            for v in range(256*64,384*64,101):
                a,b=atlas.remap((u,v),rect)
                self.assertEqual(a/32768*128+384,u/32768*512)
                self.assertEqual(b/32768*128+256,v/32768*512)
        for point in ((0,0),(32769,32769),(384*64-1,256*64)):
            with self.assertRaises(ValueError):atlas.remap(point,rect)

    def test_ordered_stream_preserves_rotation_winding_and_duplicates(self):
        header=bytearray(32)
        struct.pack_into('<BBBBHHHHHH4f',header,0,254,3,0,0,1,2,10,20,0,0,1.,2.,3.,4.)
        triangles=[((0,1,0),(2,3,1),(4,5,2)),((2,3,1),(0,1,0),(4,5,2))]*80
        uv=struct.pack('<6H',128,256,512,768,1024,2048)
        blob=atlas.make_fe(triangles,uv,header)
        self.assertEqual(atlas.read_fe(blob),triangles)
        self.assertEqual(blob[6:8],header[6:8])
        self.assertEqual(blob[16:32],header[16:32])
        with self.assertRaises(ValueError):atlas.read_fe(blob[:40])

    def test_existing_run_capacity_holds_unselected_segments_without_reordering(self):
        uv=[(384*64+2*64,256*64+3*64)]
        tri=((0,0,0),(1,1,0),(2,2,0))
        groups=[(bool(i&1),[tri]*i) for i in range(1,16)]
        chosen,held=atlas.budget_groups(groups,uv,(384,256,128),5)
        self.assertLessEqual(len(chosen),5)
        self.assertTrue(held)
        self.assertEqual([t for _,ts in groups for t in ts],[t for _,ts in chosen for t in ts])
        self.assertEqual(sum(pick for pick,_ in chosen),2)


if __name__=='__main__':unittest.main()
