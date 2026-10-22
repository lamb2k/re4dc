"""SOURCE-ONLY fake metadata cases. No live filesystem/native identity query."""
import copy,importlib.util,json,pathlib,unittest
P=pathlib.Path(__file__).parent
s=importlib.util.spec_from_file_location('reference_model',P/'reference-model.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);c=json.loads((P/'REFERENCE_EXTENSION_CONTRACT.json').read_text())
def fake(phase='prelaunch'):
 rule=c['proposed_phase_rules'][phase];im=c['image'];identity={k:im[k] for k in ('bytes','mtime_ns','inode','native_file_id')};identity['links']=rule['expected_links'];rows=[dict(path=p,resolved_path=p,samefile=True,ancestor_alias_or_reparse=False,**identity) for p in rule['paths']]
 return {'scope':'FAKE metadata using sealed receipt identity constants; alias/ownership/hash freshness NOT queried','source_sha256':im['sha256'],'before':identity.copy(),'after':identity.copy(),'all_native_hardlink_names':rule['paths'].copy(),'references':rows}
class Contract(unittest.TestCase):
 def test_retained_three_model_matches_but_never_adopts_or_authorizes(self):
  r=m.assess_proposal(c,fake(),'prelaunch');self.assertTrue(r['proposal_matches']);self.assertFalse(r['adopted']);self.assertFalse(r['preflight_performed']);self.assertFalse(r['launch_authorized'])
 def test_existing_default_off_two_link_guard_refuses_three(self):
  with self.assertRaisesRegex(ValueError,'baseline two-link'):m.baseline_default_off(c,fake())
 def test_extra_missing_duplicate_native_names_refused(self):
  for kind in ['extra','missing','duplicate']:
   x=fake()
   if kind=='extra':x['all_native_hardlink_names'].append('C:/unexpected/fourth.iso')
   elif kind=='missing':x['all_native_hardlink_names'].pop()
   else:x['all_native_hardlink_names'].append(x['all_native_hardlink_names'][0])
   with self.assertRaises(ValueError):m.assess_proposal(c,x,'prelaunch')
 def test_reference_count_two_or_four_cannot_pass_retained_three(self):
  for count in [2,4]:
   x=fake();x['before']['links']=x['after']['links']=count
   for r in x['references']:r['links']=count
   with self.assertRaises(ValueError):m.assess_proposal(c,x,'prelaunch')
 def test_native_identity_size_mtime_inode_and_source_hash_changes_refused(self):
  for field,value in [('native_file_id','0x99'),('bytes',1),('mtime_ns',1),('inode',1)]:
   x=fake();x['references'][1][field]=value
   with self.assertRaises(ValueError):m.assess_proposal(c,x,'prelaunch')
  x=fake();x['source_sha256']='0'*64
  with self.assertRaises(ValueError):m.assess_proposal(c,x,'prelaunch')
 def test_alias_reparse_or_non_samefile_refused(self):
  for field,value in [('resolved_path','C:/alias/track03.iso'),('ancestor_alias_or_reparse',True),('samefile',False)]:
   x=fake();x['references'][0][field]=value
   with self.assertRaises(ValueError):m.assess_proposal(c,x,'prelaunch')
 def test_source_identity_change_during_hash_refused(self):
  x=fake();x['after']['mtime_ns']+=1
  with self.assertRaisesRegex(ValueError,'across read'):m.assess_proposal(c,x,'prelaunch')
 def test_live_fourth_only_exact_fixed_cap_with_all_ownership_proofs(self):
  x=fake('live_owned')
  with self.assertRaisesRegex(ValueError,'ownership unavailable'):m.assess_proposal(c,x,'live_owned')
  proof={'separate_root_allocation':True,'exact_output_owner':True,'retained_current_pid_path_start':True,'reviewed_runner_created_reference':True};r=m.assess_proposal(c,x,'live_owned',proof);self.assertFalse(r['launch_authorized']);x['references'][-1]['path']='C:/unexpected/fourth.iso'
  with self.assertRaises(ValueError):m.assess_proposal(c,x,'live_owned',proof)
 def test_staged_fourth_requires_owned_inner_job_before_guest_PID_exists(self):
  x=fake('staged_owned')
  with self.assertRaisesRegex(ValueError,'ownership unavailable'):m.assess_proposal(c,x,'staged_owned')
  proof={'separate_root_allocation':True,'exact_output_owner':True,'retained_inner_pid_path_start':True,'private_job_containment':True,'reviewed_runner_created_reference':True};r=m.assess_proposal(c,x,'staged_owned',proof);self.assertFalse(r['launch_authorized'])
 def test_post_clean_fourth_leftover_fails_preserves_no_cleanup_api(self):
  x=fake('live_owned')
  with self.assertRaises(ValueError):m.assess_proposal(c,x,'post_clean')
  r=m.assess_proposal(c,fake('post_clean'),'post_clean');self.assertFalse(r['launch_authorized']);text=(P/'reference-model.py').read_text();self.assertNotIn('.unlink(',text);self.assertNotIn('subprocess',text);self.assertNotIn('os.',text)
 def test_unreviewed_phase_and_enabled_proposal_refused(self):
  with self.assertRaises(ValueError):m.assess_proposal(c,fake(),'other')
  x=copy.deepcopy(c);x['adoption_authorized']=True
  with self.assertRaises(ValueError):m.assess_proposal(x,fake(),'prelaunch')
if __name__=='__main__':unittest.main(verbosity=2)
