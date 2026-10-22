import types,unittest
from phase_latch import PhaseLatch
from observer import Invalid
class PhaseLatchTests(unittest.TestCase):
 def base(self):return {'completed_sequence':20,'Rno0':3,'system_flags':0,'stop_flags':0,'last_proc':'SndWatcher','cpu_proc':'PROCESS CPU','cpu_ticks':40500,'source_draws_finished':1,'frame_ready':1,'ui_order':0,'stream_aborted':0,'pace_skip_frame':0,'re4dc_pace_skipping':0,'direct_open':0,'completed_present':1,'completed_aborted':0,'completed_frame':10,'frame':10,'source_frame':10,'pace_skipped_frames':0,'zero_tick':100}
 def test_finished_draw_flag_alone_is_not_update_latch(self):
  s=self.base();s['completed_frame']=9
  with self.assertRaises(Invalid):PhaseLatch.require(s)
  s=self.base();s['completed_sequence']=21
  with self.assertRaises(Invalid):PhaseLatch.require(s)
 def test_skip_menu_hold_and_cursor_rejected(self):
  for key,value in [('pace_skip_frame',1),('Rno0',2),('system_flags',0x400),('last_proc','CameraMove')]:
   s=self.base();s[key]=value
   with self.assertRaises(Invalid):PhaseLatch.require(s)
 def test_epoch_change_rejected_with_equal_source_frame(self):
  first=self.base();second={**first,'zero_tick':200};it=iter([first,second]);obj=object.__new__(PhaseLatch);obj.state=lambda:next(it);obj.t=types.SimpleNamespace(scene=lambda:{'source_tick':10})
  with self.assertRaises(Invalid):obj.capture()
 def test_same_phase_complete_current_state(self):
  s=self.base();PhaseLatch.require(s);it=iter([s,s]);obj=object.__new__(PhaseLatch);obj.state=lambda:next(it);obj.t=types.SimpleNamespace(scene=lambda:{'source_tick':10});self.assertEqual(obj.capture()['cpu_us'],1000)
if __name__=='__main__':unittest.main()
