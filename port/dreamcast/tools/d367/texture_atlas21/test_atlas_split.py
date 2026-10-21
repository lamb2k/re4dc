import struct
import unittest
import atlas_split as atlas


class AtlasTests(unittest.TestCase):
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


if __name__=='__main__':unittest.main()
