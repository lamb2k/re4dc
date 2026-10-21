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
  paths|={'src/game/pl_npc.cpp','src/pl11/pl11.cpp'}
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
 def test_alias_scan_ignores_comments_but_keeps_literal_target(self):
  s='// argument x(cModel* m) asm("MotionMove");\nu16 MotionMoveF(cModel* m, int x) asm("MotionMove");\n'
  import re
  a=re.findall(r'\b(\w+)\s*\([^;{}]*\)\s*asm\("([^"\n]+)"\)',audit.mask_comments(s))
  self.assertEqual(a,[('MotionMoveF','MotionMove')])

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--source-ref',default='c7e0358a');p.add_argument('--census',type=Path,required=True);ARGS,rest=p.parse_known_args();unittest.main(argv=[sys.argv[0]]+rest)
