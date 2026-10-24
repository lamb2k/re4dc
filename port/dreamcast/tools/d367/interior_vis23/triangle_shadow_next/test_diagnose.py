"""Synthetic refusal-category controls; categories remain heuristic."""
import unittest
from diagnose import classify

class DiagnosticTests(unittest.TestCase):
    tri=((-20,-20,0),(20,-20,0),(0,20,0))
    eye=((-1,-1,10),(1,1,12))
    def test_categories(self):
        self.assertEqual(classify(self.tri,self.eye,((-1,-1,-12),(1,1,-10)))[0],'float_candidate')
        self.assertEqual(classify(self.tri,self.eye,((-1,-1,12),(1,1,13)))[0],'target_not_strictly_opposite_plane')
        self.assertEqual(classify(self.tri,((-1,-1,-1),(1,1,1)),((-1,-1,-12),(1,1,-10)))[0],'eye_plane_crossing_or_contact')
        self.assertEqual(classify(self.tri,self.eye,((40,40,-12),(50,50,-10)))[0],'triangle_edge_coverage')
        self.assertEqual(classify(self.tri[::-1],self.eye,((-1,-1,-12),(1,1,-10)))[0],'float_candidate')
        self.assertEqual(classify(self.tri,((-1,-1,0),(1,1,1)),((-1,-1,-12),(1,1,-10)))[0],'eye_plane_crossing_or_contact')

if __name__=='__main__':unittest.main()
