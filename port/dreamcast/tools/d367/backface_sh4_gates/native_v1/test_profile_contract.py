import copy,unittest
from contain import fixed_stock_contract
class Tests(unittest.TestCase):
 def profile(self,name='f1'):
  tick={'f1':330,'close-ganado':420}[name]
  return dict(fixture_name=name,freeze_tick=tick,capture='fresh-cap',stock_argv=['--disc','disc','--cap','fresh-cap','--syms','a b c','--seconds','40','--period','2','--stop','^warp: frozen at tick '+str(tick)+'$','--grace','8','--name','unique'])
 def test_f1_exact330(self):self.assertEqual(fixed_stock_contract(self.profile())['--stop'],'^warp: frozen at tick 330$')
 def test_close_exact420(self):self.assertEqual(fixed_stock_contract(self.profile('close-ganado'))['--stop'],'^warp: frozen at tick 420$')
 def test_close330_refuses(self):
  p=self.profile('close-ganado');p['freeze_tick']=330
  with self.assertRaises(ValueError):fixed_stock_contract(p)
 def test_stop_mismatch_refuses(self):
  p=self.profile('close-ganado');p['stock_argv'][11]='^warp: frozen at tick 330$'
  with self.assertRaises(ValueError):fixed_stock_contract(p)
 def test_added_warp_refuses(self):
  p=self.profile();p['stock_argv']+=['--warp','another']
  with self.assertRaises(ValueError):fixed_stock_contract(p)
 def test_unbounded_seconds_refuses(self):
  p=self.profile();p['stock_argv'][7]='3000'
  with self.assertRaises(ValueError):fixed_stock_contract(p)
 def test_changed_grace_refuses(self):
  p=self.profile();p['stock_argv'][13]='30'
  with self.assertRaises(ValueError):fixed_stock_contract(p)
if __name__=='__main__':unittest.main()
