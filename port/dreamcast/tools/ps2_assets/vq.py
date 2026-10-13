"""Existing deterministic CPU VQ nearest-centre helper."""
import numpy as np

def nearest(x,c):
 out=[];cc=(c*c).sum(1)
 for j in range(0,len(x),4096):
  a=x[j:j+4096];out.append(((a*a).sum(1)[:,None]+cc[None,:]-2*a@c.T).argmin(1))
 return np.concatenate(out)
