import importlib.util,pathlib,unittest
p=pathlib.Path(__file__).with_name('force_limited.py');s=importlib.util.spec_from_file_location('fps',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Controls(unittest.TestCase):
 def test_absent_key_becomes_explicit_yes(self):
  text='[config]\nrend.EmulateFramebuffer = yes\n';out=m.enforce_text(text);self.assertIn('aica.LimitFPS = yes',out);self.assertEqual(m.enforce_text(out),out)
 def test_enabled_aliases_canonicalized(self):
  for v in ['yes','true','1']:
   out=m.enforce_text('[config]\naica.LimitFPS = '+v+'\nrend.EmulateFramebuffer = yes\n');self.assertIn('aica.LimitFPS = yes',out)
 def test_explicit_off_refused(self):
  for v in ['no','false','0','nonsense']:
   with self.assertRaises(m.ConfigRefused):m.enforce_text('[config]\naica.LimitFPS = '+v+'\nrend.EmulateFramebuffer = yes\n')
 def test_duplicate_refused(self):
  with self.assertRaises(m.ConfigRefused):m.enforce_text('[config]\naica.LimitFPS = yes\naica.LimitFPS = yes\nrend.EmulateFramebuffer = yes\n')
 def test_bad_config_section_refused(self):
  for text in ['rend.EmulateFramebuffer = yes\n','[config]\n[config]\nrend.EmulateFramebuffer = yes\n']:
   with self.assertRaises(m.ConfigRefused):m.enforce_text(text)
 def test_missing_or_off_framebuffer_refused(self):
  for text in ['[config]\n','[config]\nrend.EmulateFramebuffer = no\n']:
   with self.assertRaises(m.ConfigRefused):m.enforce_text(text)
if __name__=='__main__':unittest.main(verbosity=2)
