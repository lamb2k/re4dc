#!/usr/bin/env python3
"""Structural source-rule regression, not C++ execution or a CFG proof."""
import argparse
import json
import subprocess
import sys
import unittest
from pathlib import Path
import motion_consumer_audit as audit

class Rules(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.census=json.loads(ARGS.census.read_text())
  paths=set(audit.EVALUATORS)|{f'src/{m}/{m}.cpp' for m in audit.BLENDS}
  paths|={'src/game/pl_npc.cpp','src/pl11/pl11.cpp','src/game/pl_sub.cpp','src/game/em_sub.cpp','src/game/pl_class.cpp','src/game/read.cpp','src/game/game.cpp','include/types.h','src/game/sce_com.cpp'}
  paths|={f'src/em{x}/em{x}.cpp'for x in ['2f','31']}
  paths|={f'src/em{x}/em{x}_set.cpp'for x in ['10','11','12']}
  paths|={'src/game/model.cpp','src/game/obj12.cpp','src/game/obj16.cpp','src/game/em.cpp','src/game/emwep.cpp','src/game/emrock.cpp','src/game/main.cpp','src/game/main_mem.cpp','src/game/event.cpp','src/game/pl_leon.cpp','include/cManager.h','port/dreamcast/game/motion_bridge.cpp','port/dreamcast/game/platform/mem.cpp'}
  paths|={p for p in subprocess.check_output(['git','-C',str(ARGS.repo),'ls-tree','-r','--name-only',ARGS.source_ref,'src']).decode().splitlines()if p.endswith('_set.cpp')}
  paths|={'src/em30/em30.cpp','src/em3c/em3c.cpp','src/pl0e/pl0e.cpp','src/pl0f/pl0f.cpp'}
  cls.texts={p:subprocess.check_output(['git','-C',str(ARGS.repo),'show',ARGS.source_ref+':'+p]).decode() for p in paths}
 def test_seven_evaluators_and_seven_blend_helpers(self):
  self.assertEqual(len(audit.check_evaluators(self.texts)),7)
  self.assertEqual(len(audit.check_blends(self.texts)),7)
 def test_missing_lease_is_rejected(self):
  t=dict(self.texts);t['src/game/motion.cpp']=t['src/game/motion.cpp'].replace('Re4dcMotionLease keys(data, &native_keys, tbl);','',1)
  with self.assertRaises(AssertionError):audit.check_evaluators(t)
 def test_new_unreviewed_evaluator_is_rejected(self):
  t=dict(self.texts);t['src/game/new_test_consumer.cpp']='void newConsumer() { HermiteInterpolation(p, o, h); }\n'
  with self.assertRaises(AssertionError):audit.check_evaluators(t)
 def test_fourth_sequence_pointer_cannot_become_a_third_fcv_silently(self):
  t=dict(self.texts);t['src/em32/em32.cpp']=t['src/em32/em32.cpp'].replace('m0, m3i,','m3, m3i,')
  with self.assertRaises(AssertionError):audit.check_blends(t)
 def test_known_three_stream_ashley_baseline_and_selected_fixed(self):
  groups=audit.reviewed_groups(self.census,self.texts)
  old=groups['ashley-baseline-body-look-face'];new=groups['ashley-fixed-body-look-face']
  self.assertEqual([r['entry']for r in old['records']],[0,6,61])
  self.assertTrue(old['strict_v3_over_two']);self.assertEqual(old['cached_payload_bytes'],10656)
  self.assertFalse(new['strict_v3_over_two']);self.assertEqual(new['distinct_cached'],0)
 def test_selected_sequence_or_missing_variant_not_inferred_resident(self):
  with self.assertRaises(AssertionError):audit.group(self.census,'qa-fixed:em/em35.drs',[0x6b],'SEQ is not an FCV')
  with self.assertRaises(AssertionError):audit.group(self.census,'qa-fixed:em/em12.drs',[0x12e],'not this selected variant')
 def test_shared_tentacle_alias_is_one_cache_record(self):
  g=audit.group(self.census,'qa-fixed:em/em12.drs',[0x253]*4,'four independent instances, one binding entry')
  self.assertEqual(g['distinct_cached'],1);self.assertEqual(g['cached_payload_bytes'],2304)
 def test_preload_hint_is_still_cached_payload(self):
  g=audit.group(self.census,'prepared-krauser:em/em39.drs',[0x7f,0x81,0x2f],'reclaimable preload group')
  self.assertEqual(g['distinct_cached'],3);self.assertEqual(g['cold_bytes'],0)
  self.assertGreater(g['cached_payload_bytes'],0);self.assertFalse(g['mtc']['permanent_hot_lease'])
 def test_hokan_is_not_a_second_fcv(self):
  b,_=audit.fn(self.texts['src/game/motion.cpp'],'MotionHokan')
  self.assertIn('prevMat',b);self.assertNotIn('HermiteInterpolation(',b)
 def test_shared_normal_return_and_epilog_lifetime_narrowing(self):
  r=audit.lifecycle_rules(self.texts)
  self.assertEqual(len(r['empty_selected_epilogs']),11)
  self.assertFalse(r['interrupt_restores_subarc'])
 def test_event_mode_register_local_is_not_marked_target_proven(self):
  r=audit.lifecycle_rules(self.texts)
  self.assertTrue(r['player_event_mode_abi']['status'].startswith('OPEN'))
 def test_donor_free_before_unbind_is_rejected(self):
  t=dict(self.texts);t['src/game/read.cpp']=t['src/game/read.cpp'].replace('re4dc_motion_unbind(m->pArc);','Mem_free(m->pArc); re4dc_motion_unbind(m->pArc);',1)
  with self.assertRaises(AssertionError):audit.lifecycle_rules(t)
 def test_early_door_unbind_before_quiescence_is_rejected(self):
  t=dict(self.texts);t['src/game/game.cpp']=t['src/game/game.cpp'].replace('void gameDoordemo()\n{','void gameDoordemo()\n{ EmReadInit();',1)
  with self.assertRaises(AssertionError):audit.lifecycle_rules(t)
 def test_normal_return_without_archive_restore_is_rejected(self):
  t=dict(self.texts);text=t['src/game/pl_sub.cpp'];body,_=audit.fn(text,'EndPlDamage');t['src/game/pl_sub.cpp']=text.replace(body,body.replace('pl->subArc = pl->subArc2;',''),1)
  with self.assertRaises(AssertionError):audit.lifecycle_rules(t)
 def test_alias_scan_ignores_comments_but_keeps_literal_target(self):
  s='// argument x(cModel* m) asm("MotionMove");\nu16 MotionMoveF(cModel* m, int x) asm("MotionMove");\n'
  import re
  a=re.findall(r'\b(\w+)\s*\([^;{}]*\)\s*asm\("([^"\n]+)"\)',audit.mask_comments(s))
  self.assertEqual(a,[('MotionMoveF','MotionMove')])

 def test_function_boundary_keeps_cases_after_compound_vec_literal(self):
  b,_=audit.fn(self.texts['src/em2b/em2b.cpp'],'plem2b_Strangle')
  self.assertIn('&((Vec) {',b);self.assertIn('EndPlDamage()',b);self.assertIn('case 5:',b)
  s="""void victim() {
#if A
 for(int x=0;x<1;++x) {
#else
 for(int y=0;y<1;++y) {
#endif
  call();
 }
 after();
}
void next() { wrong(); }
"""
  b,_=audit.fn(s,'victim');self.assertIn('after()',b);self.assertNotIn('wrong()',b)
 def test_owner_contracts_expose_different_failure_kinds(self):
  r=audit.ownership_rules(self.texts,self.census)
  self.assertFalse(r['partial_admission']['module_slot_exhaustion_restores_display'])
  self.assertIn('terminal',r['partial_admission']['bind_refusal'])
  self.assertEqual(len(r['lifetime_edges']),8)
 def test_display_failure_classification_changes_if_source_restores_flags(self):
  t=dict(self.texts);old='if (m == NULL) {\n        return NULL;';new='if (m == NULL) {\n        pG->Disp_flg = flags; return NULL;'
  self.assertIn(old,t['src/game/read.cpp']);t['src/game/read.cpp']=t['src/game/read.cpp'].replace(old,new)
  self.assertTrue(audit.ownership_rules(t,self.census)['partial_admission']['module_slot_exhaustion_restores_display'])
 def test_leon_neck_cannot_be_counted_as_an_independent_third_body_stream(self):
  t=dict(self.texts);t['src/game/pl_class.cpp']=t['src/game/pl_class.cpp'].replace('p->blendMot = &p->neckMot','p->blendMot = &p->Motion',1)
  with self.assertRaises(AssertionError):audit.ownership_rules(t,self.census)
 def test_new_partner_neck_evaluator_requires_review(self):
  t=dict(self.texts);b,_=audit.fn(t['src/game/pl_npc.cpp'],'cSubChar::neckCtrl');t['src/game/pl_npc.cpp']=t['src/game/pl_npc.cpp'].replace(b,b.replace('{','{ MotionMove(this,0);',1),1)
  with self.assertRaises(AssertionError):audit.ownership_rules(t,self.census)
 def test_halt_cannot_be_silently_classified_as_recoverable_return(self):
  t=dict(self.texts);t['port/dreamcast/game/platform/mem.cpp']=t['port/dreamcast/game/platform/mem.cpp'].replace('thd_sleep(1000)','return',1)
  with self.assertRaises(AssertionError):audit.ownership_rules(t,self.census)
 def test_obj16_early_evaluation_before_owner_guard_is_rejected(self):
  t=dict(self.texts);b,_=audit.fn(t['src/game/obj16.cpp'],'cObj16::move');t['src/game/obj16.cpp']=t['src/game/obj16.cpp'].replace(b,b.replace('{','{ Obj16_R1_move_tbl[r_no_1](this);',1),1)
  with self.assertRaises(AssertionError):audit.ownership_rules(t,self.census)
 def test_cart_work_owner_variant_must_not_change_silently(self):
  t=dict(self.texts);t['src/em11/em11_set.cpp']=t['src/em11/em11_set.cpp'].replace('w->mot[51] = 0','w->mot[51] = ARC(0x25E)',1)
  with self.assertRaises(AssertionError):audit.ownership_rules(t,self.census)
 def test_recovery_sets_keep_death_continue_and_nondoor_reset_separate(self):
  r=audit.ownership_rules(self.texts,self.census);edges={x['id']:x for x in r['lifetime_edges']}
  self.assertIn('source normal Continue',edges['A07-FATAL']['status']);self.assertTrue(edges['A08-RESET']['status'].startswith('OPEN'))
  self.assertIn('post-destroy',edges['A08-RESET']['status'])
 def test_reset_owner_order_change_requires_reclassification(self):
  t=dict(self.texts);t['src/game/main.cpp']=t['src/game/main.cpp'].replace('    MemClearAllHeap();','    systemResetCommon();\n    MemClearAllHeap();',1)
  with self.assertRaises(AssertionError):audit.ownership_rules(t,self.census)
 def test_shape_writer_multiplicity_must_be_reviewed(self):
  t=dict(self.texts);t['src/game/shape.cpp']=t['src/game/shape.cpp'].replace('SetShape(p, p->pShape, (f32) p->shape_frame);','SetShape(p, p->pShape, (f32) p->shape_frame); SetShape(p, p->pShape, 0);',1)
  with self.assertRaises(AssertionError):audit.ownership_rules(t,self.census)

 def test_all_literal_work_initializer_macro_owners_are_pinned(self):
  r=audit.ownership_rules(self.texts,self.census)
  self.assertEqual(len(r['selector_contracts']['literal_work_archive_origins']),15)
  t=dict(self.texts);t['src/em12/em12_set.cpp']=t['src/em12/em12_set.cpp'].replace('#define ARC(no) PL_ARC_PTR(em->subArc, no)','#define ARC(no) ROOM_ARC_PTR(no)')
  with self.assertRaises(AssertionError):audit.ownership_rules(t,self.census)
 def test_event_end_precedes_registration_release(self):
  t=dict(self.texts);t['src/game/event.cpp']=t['src/game/event.cpp'].replace('evt->ExeEndEvt(evt, 0);','DelEvd(p); evt->ExeEndEvt(evt, 0);',1)
  with self.assertRaises(AssertionError):audit.ownership_rules(t,self.census)
 def test_event_shape_stop_is_not_inferred_from_body_motion_clear(self):
  r=audit.ownership_rules(self.texts,self.census);e=next(x for x in r['lifetime_edges']if x['id']=='A08-EVENT-SHAPE')
  self.assertTrue(e['status'].startswith('OPEN'));self.assertIn('not ShapeEnd',e['termination'])

 def test_indirect_bite_borrower_without_subarc_store_is_reviewed(self):
  r=audit.indirect_owner_rules(self.texts,self.census)
  self.assertIn('no subArc store',r['bite_contract']);self.assertEqual(len(r['head_setter_callers']['setPlDmgMot']),3)
 def test_head_setter_alternatives_not_eleven_simultaneous_streams(self):
  r=audit.indirect_owner_rules(self.texts,self.census)
  self.assertEqual(len(r['head_setter_callers']['setMotData']),6)
  t=dict(self.texts);t['src/game/obj16.cpp']=t['src/game/obj16.cpp'].replace('w->mot[10] = m10;','w->mot[10] = m9;',1)
  with self.assertRaises(AssertionError):audit.indirect_owner_rules(t,self.census)
 def test_boat_reviewed_six_stream_group_uses_actual_inline_records(self):
  r=audit.indirect_owner_rules(self.texts,self.census);g=r['reviewed_groups']['jet-ski-positive-lean-six-body-streams']
  self.assertEqual(len(g['records']),6);self.assertEqual(g['distinct_cached'],0);self.assertIsNone(g['mtc'])
 def test_boat_default_archive_restore_cannot_be_removed_silently(self):
  t=dict(self.texts);b,_=audit.fn(t['src/pl0e/pl0e.cpp'],'PlBoatMove');t['src/pl0e/pl0e.cpp']=t['src/pl0e/pl0e.cpp'].replace(b,b.replace('pl->subArc = pl->subArc2;',''),1)
  with self.assertRaises((AssertionError,ValueError)):audit.indirect_owner_rules(t,self.census)
 def test_bite_callback_normal_return_must_still_end_damage(self):
  t=dict(self.texts);b,_=audit.fn(t['src/game/obj16.cpp'],'plemDmMStar');t['src/game/obj16.cpp']=t['src/game/obj16.cpp'].replace(b,b.replace('EndPlDamage();',''),1)
  with self.assertRaises(AssertionError):audit.indirect_owner_rules(t,self.census)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--source-ref',default='c7e0358a');p.add_argument('--census',type=Path,required=True);ARGS,rest=p.parse_known_args();unittest.main(argv=[sys.argv[0]]+rest)
