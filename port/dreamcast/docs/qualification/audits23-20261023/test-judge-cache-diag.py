#!/usr/bin/env python3
import importlib.util
from pathlib import Path
import unittest
p=Path(__file__).with_name('judge-cache-diag.py')
s=importlib.util.spec_from_file_location('judge',p);j=importlib.util.module_from_spec(s);s.loader.exec_module(j)
def pair(seq,phase='live',room='0117',frame=150,c=3,t=2,rejected=1,u=0,ticks=200,maximum=100,full=2,ram=1,capacity=None,overflow='0',hook=0):
 if capacity is None:capacity=full*16384+ram*8192
 return f'cachep2diag room={room} phase={phase} seq={seq} frame={frame} calls={c} timed={t} rejected={rejected} unavailable={u} overflow={overflow} hook_reject={hook}\ncachep2diag time room={room} seq={seq} ticks={ticks>>32:08x}:{ticks&0xffffffff:08x} max={maximum} full512={full} ram256={ram} capacity={capacity>>32:08x}:{capacity&0xffffffff:08x}\n'
BOOT=pair(1,'boot','ffff',0)
class Controls(unittest.TestCase):
 def bad(self,text):
  with self.assertRaises(j.Invalid):j.judge(text)
 def test_valid_and_unknown_attribution(self):
  text='other log\n'+BOOT+pair(2)+pair(3,frame=300)+pair(4,frame=0)+pair(5,'transition','ffff',0)+pair(6,room='0200')
  r=j.judge(text,[0x117,0x200]);self.assertEqual(r['totals']['calls'],18);self.assertEqual(r['rooms']['0117']['calls'],9);self.assertEqual(r['unattributed']['boot']['calls'],3);self.assertEqual(r['unattributed']['transition']['calls'],3);self.assertTrue(r['capture_ends_with_unreported_interval']);self.assertIsNone(r['interrupted_final_interval']['ticks'])
 def test_timed_zero_is_nodata(self):
  r=j.judge(BOOT+pair(2,c=1,t=0,rejected=0,u=1,ticks=0,maximum=0,full=1,ram=0));self.assertEqual(r['rooms']['0117']['timing_status'],'NODATA');self.assertIsNone(r['rooms']['0117']['modelled_nominal_valid_window_us']);self.assertEqual(r['rooms']['0117']['unavailable'],1)
 def test_all_zero_still_observed_counts_no_duration(self):
  r=j.judge(pair(1,'boot','ffff',0,c=0,t=0,rejected=0,ticks=0,maximum=0,full=0,ram=0));self.assertEqual(r['totals']['calls'],0);self.assertEqual(r['totals']['timing_status'],'NODATA');self.assertIsNone(r['totals']['clock_coverage'])
 def test_bad_total(self):self.bad(BOOT+pair(2,c=4))
 def test_bad_modes(self):self.bad(BOOT+pair(2,full=1))
 def test_bad_capacity(self):self.bad(BOOT+pair(2,capacity=1))
 def test_overflow_hook(self):
  self.bad(BOOT+pair(2,overflow='1'));self.bad(BOOT+pair(2,hook=1))
 def test_duplicate_and_missing_sequence(self):
  self.bad(BOOT+pair(2)+pair(2));self.bad(BOOT+pair(3));self.bad(pair(2))
 def test_missing_or_duplicate_lines(self):
  lines=pair(2).splitlines(True);self.bad(BOOT+lines[0]);self.bad(BOOT+lines[1]);self.bad(BOOT+pair(2)+lines[1]);self.bad(BOOT+lines[0]+pair(3))
 def test_pair_mismatch(self):
  text=BOOT+pair(2);self.bad(text.replace('time room=0117','time room=0200'));self.bad(text.replace('time room=0117 seq=2','time room=0117 seq=3'))
 def test_phase_and_frame_labels(self):
  self.bad(BOOT+pair(2,phase='transition'));self.bad(BOOT+pair(2,room='ffff'));self.bad(BOOT+pair(2,phase='boot',room='ffff',frame=0));self.bad(BOOT+pair(2,frame=149));self.bad(BOOT+pair(2,frame=300));self.bad(BOOT+pair(2)+pair(3,room='0200',frame=300));self.bad(BOOT+pair(2)+pair(3,frame=450));self.bad(BOOT+pair(2)+pair(3,'transition','ffff',0));self.bad(BOOT+pair(2)+pair(3,room='0200',frame=0))
 def test_timing_bounds(self):
  self.bad(BOOT+pair(2,t=0,c=1,rejected=1,full=1,ram=0));self.bad(BOOT+pair(2,ticks=99));self.bad(BOOT+pair(2,ticks=201));self.bad(BOOT+pair(2,ticks=24937442,maximum=12468721))
 def test_malformed_fields_and_missing_room(self):
  self.bad(BOOT.replace('timed=2','timed=-2'));self.bad(BOOT.replace('seq=1','seq=4294967296'));self.bad(BOOT+'cachep2diag nonsense\n');self.bad('no rows')
  with self.assertRaises(j.Invalid):j.judge(BOOT,[0x117])
 def test_prefixed_serial_lines(self):
  r=j.judge(''.join('[serial] '+l+'\n' for l in (BOOT+pair(2)).splitlines()));self.assertEqual(r['last_seq'],2)
if __name__=='__main__':unittest.main(verbosity=2)
