import unittest,copy
import disposition as d

def fixture():
 p=[];r=[];domains=[]
 for size in [2000,500,250]:
  for rank in range(25):
   n=865 if rank==0 else 1;covered=[0,1] if rank==0 else [];draw=list(range(2,n)) if rank==0 else [0];case=[rank,rank,rank,1,1,0,1,'hut',647,size]
   p.append({'case':case});r.append({'case':case,'complete_originals':n,'covered_originals':covered,'unproved_draw_originals':draw,'runtime_admitted':False,'actual_removed_transform_corners':None,'modelled_ms':None,'dependencies':[1] if covered else [],'exclusively_covered_local_indices':[0,1] if covered else [],'draw_reasons':[[i,'UNKNOWN'] for i in draw]})
  domains.append({'size_mm':size,'nominal_per_let_covered_originals_before_global_union':2,'covered_originals_after_global_union':2,'sum_per_let_exclusive_local_index_slots':2})
 return {'halt':None,'plan':p,'results':r,'domains':domains}
class Disposition(unittest.TestCase):
 def test_complete_alternatives_stay_separate(self):
  out=d.domain_rows(fixture());self.assertEqual([x['nominal_whole_meshlets'] for x in out],[0,0,0]);self.assertEqual([x['partial_nominal_triangles'] for x in out],[2,2,2]);self.assertTrue(all(x['gross_saving_of_admitted_empty_cut_set_ms']==0 for x in out))
 def test_missing_overlap_foreign_camera_refuse(self):
  for mutate in [lambda j:j['results'][0]['unproved_draw_originals'].pop(),lambda j:j['results'][0]['covered_originals'].append(2),lambda j:j['results'][0]['case'].__setitem__(7,'cross')]:
   j=fixture();mutate(j)
   with self.assertRaises(ValueError):d.domain_rows(j)
 def test_global_k16_failure_is_not_partial_acceptance(self):
  j=fixture()
  for r in j['results'][50:]:r['dependencies']=list(range(19))
  j['domains'][2]['covered_originals_after_global_union']=0;j['domains'][2]['sum_per_let_exclusive_local_index_slots']=0
  out=d.domain_rows(j)[2];self.assertFalse(out['global_union_within_limit']);self.assertEqual(out['partial_nominal_triangles'],2);self.assertEqual(out['after_global_union_nominal_triangles'],0)
 def test_portal_rows_do_not_trust_zero_label(self):
  j={'rows':[{'frame':x,'all_openings_out':False,'visible_unresolved_openings':[0]} for x in range(500,795,7)],'all_openings_out_views':0,'camera':{},'component':0};self.assertEqual(d.portal_rows(j)['views'],43);j['rows'][0]['all_openings_out']=True
  with self.assertRaises(ValueError):d.portal_rows(j)
if __name__=='__main__':unittest.main(verbosity=2)
