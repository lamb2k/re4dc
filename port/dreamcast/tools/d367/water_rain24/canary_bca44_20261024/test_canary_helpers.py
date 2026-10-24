import importlib.util,json,pathlib,struct,tempfile,unittest,math
HERE=pathlib.Path(__file__).parent
spec=importlib.util.spec_from_file_location('observe',HERE/'observe_canary.py');observer=importlib.util.module_from_spec(spec);spec.loader.exec_module(observer)
spec=importlib.util.spec_from_file_location('launch',HERE/'launch_canary.py');launcher=importlib.util.module_from_spec(spec);spec.loader.exec_module(launcher)
E=pathlib.Path('/mnt/c/Flycast-Evidence/re4-dreamcast/water-rain24/rain-bca44-console55-20261024')
class FakeReader:
 def __init__(self,layout):
  self.layout=layout;self.pg=0x8c100000;self.room=0x10c;self.frame=777;self.blob=bytearray(layout['types']['Filter06Work']['bytes']);f=layout['types']['Filter06Work']['members'];off=lambda k:f[k]['offset'];struct.pack_into('<I',self.blob,off('p'),0x8c200000);struct.pack_into('<I',self.blob,off('num'),1100);struct.pack_into('<fff',self.blob,off('spd'),21,-250,0);self.blob[off('col'):off('col')+4]=bytes([170,170,170,80]);self.blob[off('cur'):off('cur')+4]=bytes([170,170,170,80]);struct.pack_into('<f',self.blob,off('rate'),1);struct.pack_into('<f',self.blob,off('scale'),1)
 def u32(self,address):
  symbols=self.layout['symbols'];g=self.layout['types']['GlobalWork']['members']
  if address==symbols['pG']['address']:return self.pg
  if address==self.pg+g['Frame_cnt']['offset']:return self.frame
  for key,row in symbols.items():
   if address==row['address']:return {'s_raindc_frames':5,'s_raindc_sent':1600}.get(key,0)
  raise ValueError('unmapped synthetic address')
 def read_pointer(self,address,count):
  if address==self.pg+self.layout['types']['GlobalWork']['members']['room_id']['offset']:return struct.pack('<H',self.room)
  if address==self.layout['symbols']['flt06']['address']:return bytes(self.blob)
  raise ValueError('unmapped synthetic extent')
class Controls(unittest.TestCase):
 def layout(self,arm='on'):return json.loads((E/'identities'/(arm+'-g-source-layout.json')).read_text())
 def test_actual_off_on_layouts(self):
  for arm in ['off','on']:
   d=self.layout(arm);s=observer.source_sample(FakeReader(d),d);self.assertTrue(s['retained_source_signature_matches']);self.assertEqual(s['room'],0x10c);self.assertEqual(s['source_frame_before'],777);self.assertNotEqual(s['source_frame_before'],330)
 def test_wrong_count_and_signature_fields(self):
  d=self.layout();f=d['types']['Filter06Work']['members']
  for field,value in [('num',1099),('col',1),('cur',0),('rate',.5),('scale',2),('alphaMin',1)]:
   r=FakeReader(d);off=f[field]['offset']
   if field=='num':struct.pack_into('<I',r.blob,off,value)
   elif field in ['rate','scale']:struct.pack_into('<f',r.blob,off,value)
   elif field=='cur':r.blob[off+3]=value
   else:r.blob[off]=value
   self.assertFalse(observer.source_sample(r,d)['retained_source_signature_matches'],field)
 def test_wrong_room_is_unexercised(self):
  d=self.layout();r=FakeReader(d);r.room=0x11b;self.assertFalse(observer.source_sample(r,d)['retained_source_signature_matches'])
 def test_zero_particle_storage_is_unexercised(self):
  d=self.layout();r=FakeReader(d);struct.pack_into('<I',r.blob,d['types']['Filter06Work']['members']['p']['offset'],0);self.assertFalse(observer.source_sample(r,d)['retained_source_signature_matches'])
 def test_invalid_pointer_and_nan_refused(self):
  d=self.layout();r=FakeReader(d);r.pg=1
  with self.assertRaises(ValueError):observer.source_sample(r,d)
  r=FakeReader(d);struct.pack_into('<f',r.blob,d['types']['Filter06Work']['members']['spd']['offset'],math.nan)
  with self.assertRaises(ValueError):observer.source_sample(r,d)
 def test_marker_room_and_tick(self):
  self.assertEqual(observer.marker('warp: frozen at tick 330','10c','10c')['tick'],330)
  for line,room in [('warp: frozen at tick 329','10c'),('warp: frozen at tick 330','11b')]:
   with self.assertRaises(ValueError):observer.marker(line,room,'10c')
 def test_explicit_grant_required(self):
  good={'source':launcher.SOURCE,'preflight_sha256':'a'*64,'root_approved':True,'cases':['off','on'],'maximum_guests':2,'seconds':45};launcher.require_grant(good,'a'*64,'off')
  for key,value in [('source','old'),('preflight_sha256','b'*64),('root_approved',False),('maximum_guests',3),('seconds',55),('cases',['off'])]:
   bad=dict(good);bad[key]=value
   with self.assertRaises(ValueError):launcher.require_grant(bad,'a'*64,'on')
 def test_file_drift_refused(self):
  with tempfile.TemporaryDirectory(dir='/dev/shm') as td:
   p=pathlib.Path(td)/'x';p.write_bytes(b'1234');row={'bytes':4,'sha256':launcher.sha(p)};launcher.verify_file(p,row);p.write_bytes(b'4321')
   with self.assertRaises(ValueError):launcher.verify_file(p,row)
 def test_known_fps_guard(self):
  text='[config]\nrend.EmulateFramebuffer = yes\n';x=observer.prepare_owned_config.__globals__['enforce_text'](text);self.assertEqual(x.count('aica.LimitFPS = yes'),1)
  with self.assertRaises(ValueError):observer.prepare_owned_config.__globals__['enforce_text'](text+'aica.LimitFPS = no\n')
 def test_vram_extent(self):
  class Mod:VRAM_SIZE=8*1024*1024
  Mod.map_32bit_vram=staticmethod(lambda p:p)
  with self.assertRaises(ValueError):observer.frame_bytes(b'',0,Mod)
  with self.assertRaises(ValueError):observer.frame_bytes(bytes(Mod.VRAM_SIZE),3,Mod)
 def test_no_old_completion_claim(self):
  text=(HERE/'observe_canary.py').read_text();self.assertNotIn('last completed world328',text);self.assertIn("'callback_ticket_direct_proof':False",text)
 def test_on_requires_actual_source_and_fresh_native_evidence(self):
  d=self.layout();state=observer.source_sample(FakeReader(d),d)
  self.assertIn('UNEXERCISED',observer.classify_view('on',[state],'')['feature_observation'])
  good=observer.classify_view('on',[state],'rain dc: frame=770 room=10c streaks=320 sent=640 alpha=80');self.assertTrue(good['native_room10c_emission_observed']);self.assertFalse(good['automatic_visual_or_lifecycle_pass'])
  state['retained_source_signature_matches']=False;self.assertIn('UNEXERCISED',observer.classify_view('on',[state],'rain dc: frame=770 room=10c streaks=320 sent=640')['feature_observation'])
 def test_off_unexpected_native_is_not_accepted(self):
  d=self.layout('off');state=observer.source_sample(FakeReader(d),d);self.assertIn('UNEXPECTED',observer.classify_view('off',[state],'rain dc: frame=770 room=10c streaks=320 sent=640')['feature_observation'])
 def test_compile_helpers_only(self):
  for name in ['observe_canary.py','launch_canary.py','force_limited.py','stat_owned_ram.py']:compile((HERE/name).read_text(),name,'exec')
if __name__=='__main__':unittest.main()