"""Pure PNG allocation broker; caller must re-gate inputs AFTER any capture."""
class Budget:
 def __init__(self,max_png=8,reserve_final=2):self.max=max_png;self.reserve=reserve_final;self.used=0;self.events=set()
 def request(self,label,existing_png,charged,final=False):
  if existing_png!=self.used:raise RuntimeError('unexpected/unmetered screenshot count')
  if label in self.events:return False
  limit=self.max if final else self.max-self.reserve
  if self.used+2>limit:return False
  if charged+2*3*1024**2>=60000000:return False
  self.used+=2;self.events.add(label);return True
 def validate(self,actual_png):
  if actual_png!=self.used or actual_png>self.max:raise RuntimeError('PNG budget mismatch')
