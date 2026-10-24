"""Small fail-closed persistent ray reservation; failed runs never refund."""
import fcntl,json,os,time
from pathlib import Path
LIMIT=110000
class Token:
    def __init__(self,n):self.reserved=n;self.used=0
    def take(self):
        if self.used>=self.reserved:raise ValueError('Reserved ray budget exhausted before traversal')
        self.used+=1
class Ledger:
    def __init__(self,path):self.path=Path(path)
    def create(self):
        with self.path.open('x') as f:json.dump(dict(schema='ELIGIBLE24_RAYS_V1',limit=LIMIT,reserved=0,runs=[]),f);f.flush();os.fsync(f.fileno())
    def reserve(self,n,label):
        if type(n)is not int or n<=0:raise ValueError('Positive reservation required')
        with self.path.open('r+') as f:
            fcntl.flock(f.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB);r=json.load(f)
            if r['schema']!='ELIGIBLE24_RAYS_V1' or r['limit']!=LIMIT or type(r['reserved'])is not int or not 0<=r['reserved']<=LIMIT or any(type(x['reserved'])is not int or x['reserved']<=0 for x in r['runs']) or r['reserved']!=sum(x['reserved'] for x in r['runs']):raise ValueError('Ledger identity/accounting')
            if n>LIMIT-r['reserved']:raise ValueError('Entire110k tranche cap incl controls/repeated runs')
            r['reserved']+=n;r['runs'].append(dict(label=label,reserved=n,time=time.time(),refundable=False));f.seek(0);json.dump(r,f);f.truncate();f.flush();os.fsync(f.fileno())
        return Token(n)
