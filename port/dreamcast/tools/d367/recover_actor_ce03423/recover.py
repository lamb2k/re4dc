"""Exact ce034 recovery. Default describes source plan; execution requires admission/review."""
import argparse
import contextlib
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import struct
import time

PLAN_SHA = 'e580e6eaee617f8217a387803a877688fa0535ffdc44e89409bbc37ba0411252'
INPUT_SHA = '046d03de7f092e7582e0f4cba0b5303bf4f99c3009aaa4ff625a2099ea8a9536'
TARGET_SHA = 'ce034ff75d5c6eb125a5036b5c55afa1805de1beac75711cd41b73f366d854ad'
SIZE = 1028911104
ORIGINAL_SIZE = 1024653312
ROOT_CAP = 16*1024**3
PACKAGE_CAP = 3758096384
FLOOR = 20468203520
GUEST = 60*1024**2
META = 256*1024
CHUNK = 4*1024**2
CROOT = Path('/mnt/c/Flycast-Evidence/re4-dreamcast/pvs23-20261022')
INPUT = CROOT/'actor23-bea2d402-on-q01/base/track03.iso'
TARGET = CROOT/'actor23-10395a10-on-q01/base/track03.iso'
LOCKS = (Path('/root/probe/lanes/actor-visibility23-integration/tree.lock'), Path('/root/probe/pvs23-package-20261022-v1/.pvs23-package.lock'))

def require(ok, message):
 if not ok: raise ValueError(message)

def sha(path):
 with Path(path).open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()

def stamp(s):
 return s.st_dev,s.st_ino,s.st_size,s.st_mode,s.st_mtime_ns,s.st_ctime_ns

def content_stamp(s):
 # Hardlink publication changes ctime/link count, but must not change content.
 return s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns

def absent(path):
 require(not os.path.lexists(path), 'Owned output already exists; preserve/diagnose, never retry or replace: '+str(path))

def canonical(path):
 p=Path(path);require(p.is_absolute() and p.resolve()==p and not p.is_symlink(), 'Noncanonical path: '+str(p));return p

@contextlib.contextmanager
def pinned_reader(row):
 p=canonical(row['path']);fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW)
 with os.fdopen(fd,'rb') as f:
  before=os.fstat(f.fileno());require(stat.S_ISREG(before.st_mode) and before.st_size==row['size'],'Input size/type differs: '+str(p))
  yield f
  require(stamp(os.fstat(f.fileno()))==stamp(before) and stamp(p.stat())==stamp(before),'Input replaced/changed: '+str(p))

def pin_small(row):
 with pinned_reader(row) as f:
  require(hashlib.file_digest(f,'sha256').hexdigest()==row['sha256'],'Pinned small dependency differs: '+row['path'])

def read_json(path,pin):
 canonical(path);require(sha(path)==pin,'JSON pin differs: '+str(path));return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def validate_shape(plan, production=True):
 size=plan['target']['size'];require(size==plan['input']['size'],'This exact recipe requires equal source/target length')
 rows=plan['appends'];cursor=plan['original_size'];keys=set()
 for row in rows:
  require(row['package_path'] not in keys and row['offset']==cursor,'Append roster overlap/gap/duplicate')
  keys.add(row['package_path']);n=row['padded_size'];require(n==(row['size']+2047)//2048*2048 and n==(row['new_size']+2047)//2048*2048,'Append padded sizes differ');cursor+=n
 require(cursor==size,'Append extent does not end at target')
 spans=[]
 for row in plan['point_patches']:
  before=bytes.fromhex(row['before_hex']);after=bytes.fromhex(row['after_hex']);pos=row['offset']
  require(len(before)==len(after)==16 and 0<=pos and pos+16<=plan['original_size'],'Point patch bounds/length')
  spans.append((pos,pos+16))
 require(len(set(spans))==len(spans) and all(a[1]<=b[0] for a,b in zip(sorted(spans),sorted(spans)[1:])),'Point patches overlap')
 payloads=plan['payloads'];require(len({x['package_path'] for x in payloads})==len(payloads),'Duplicate payload')
 for p in payloads:
  matches=[r for r in rows if r['package_path']==p['package_path']]
  require(len(matches)==1,'Unknown replacement payload');r=matches[0]
  require(p['offset']==r['offset'] and p['padded_size']==r['padded_size'] and p['size']==r['size'] and p['sha256']==r['old_sha256'],'Payload/append tuple differs')
 if production:
  require(plan['input']==dict(path=str(INPUT),size=SIZE,sha256=INPUT_SHA) and plan['target']==dict(path=str(TARGET),size=SIZE,sha256=TARGET_SHA),'Fixed production media binding differs')
  require(plan['original_size']==ORIGINAL_SIZE and len(rows)==16 and len(payloads)==15 and len(spans)==32,'Fixed production roster differs')
  require({x['package_path'] for x in payloads}==keys-{'dc/native/r119/room.r4rc'},'Exact14 overlay/raw roster differs')

# The miniature controls exercise this exact copy/patch/hash engine. Production
# entry points always validate the sealed fixed plan before calling it.
def copy_patch(source, writer, plan, guard=lambda:None, event=lambda _:None):
 h=hashlib.sha256();count=0
 while True:
  raw=source.read(CHUNK)
  if not raw:break
  count+=len(raw);require(count<=plan['input']['size'],'Source longer than exact image');h.update(raw);require(writer.write(raw)==len(raw),'Short output write');guard()
 require(count==plan['input']['size'] and h.hexdigest()==plan['input']['sha256'],'Copied source full SHA256/length differs');event('SOURCE_FULL_HASH_VERIFIED')
 for p in plan['point_patches']:
  writer.seek(p['offset']);require(writer.read(16)==bytes.fromhex(p['before_hex']),'Directory tuple preimage differs')
 for p in plan.get('descriptor_checks',[]):
  writer.seek(p['offset']);raw=bytes.fromhex(p['hex']);require(writer.read(len(raw))==raw,'Volume descriptor length differs')
 room=next((r for r in plan['appends'] if r['package_path']=='dc/native/r119/room.r4rc'),None)
 if room:
  writer.seek(room['offset']);require(hashlib.sha256(writer.read(room['size'])).hexdigest()==room['old_sha256'],'Unchanged private room differs')
 for p in plan['payloads']:
  with pinned_reader(p) as reader:
   writer.seek(p['offset']);digest=hashlib.sha256();copied=0
   while raw:=reader.read(CHUNK):
    copied+=len(raw);digest.update(raw);require(writer.write(raw)==len(raw),'Short payload write');guard()
   require(copied==p['size'] and digest.hexdigest()==p['sha256'],'Old payload SHA256 differs: '+p['package_path'])
   pad=p['padded_size']-copied;require(0<=pad<2048,'Invalid payload padding');require(writer.write(bytes(pad))==pad,'Short padding write')
 for p in plan['point_patches']:
  writer.seek(p['offset']);raw=bytes.fromhex(p['after_hex']);require(writer.write(raw)==len(raw),'Short point write')
 writer.truncate(plan['target']['size']);writer.flush();os.fsync(writer.fileno());guard();event('PATCHES_APPLIED')
 writer.seek(0);verified=content_stamp(os.fstat(writer.fileno()));actual=hashlib.file_digest(writer,'sha256').hexdigest()
 require(content_stamp(os.fstat(writer.fileno()))==verified,'Candidate content changed during target hash')
 require(actual==plan['target']['sha256'],'Restored full target SHA256 differs; keep unpublished candidate');event('TARGET_FULL_HASH_VERIFIED');return actual,verified

def held_parent(parent,dfd):
 held=os.fstat(dfd);named=os.stat(parent,follow_symlinks=False)
 require(stat.S_ISDIR(held.st_mode) and stat.S_ISDIR(named.st_mode) and
         (held.st_dev,held.st_ino)==(named.st_dev,named.st_ino), 'Literal parent differs from held directory')
 canonical(parent)

def owned_temp(temp,writer,dfd,verified):
 held=os.stat(temp.name,dir_fd=dfd,follow_symlinks=False);current=os.fstat(writer.fileno())
 require(stat.S_ISREG(held.st_mode) and stat.S_ISREG(current.st_mode) and
         content_stamp(held)==content_stamp(current)==verified,'Owned temporary inode/content changed')

def literal_target(target,dfd,verified):
 held_parent(target.parent,dfd)
 literal=os.stat(target,follow_symlinks=False)
 held=os.stat(target.name,dir_fd=dfd,follow_symlinks=False)
 require(stat.S_ISREG(literal.st_mode) and stat.S_ISREG(held.st_mode) and
         content_stamp(literal)==content_stamp(held)==verified,'Literal target differs from verified writer')

def publish(temp,target,writer,dfd,verified,expected_size):
 # Exclusive link publication keeps one allocation. Namespace changes refuse
 # before unlink; never use a literal path to unlink a replacement directory.
 require(temp.parent==target.parent and verified[2]==expected_size,'Publication size/parent proof differs')
 held_parent(target.parent,dfd);owned_temp(temp,writer,dfd,verified);absent(target)
 os.link(temp.name,target.name,src_dir_fd=dfd,dst_dir_fd=dfd,follow_symlinks=False)
 literal_target(target,dfd,verified);owned_temp(temp,writer,dfd,verified)
 os.fsync(dfd)
 # Recheck both literal names immediately before removing our exclusive name.
 literal_target(target,dfd,verified);owned_temp(temp,writer,dfd,verified)
 os.unlink(temp.name,dir_fd=dfd);os.fsync(dfd)
 literal_target(target,dfd,verified)


def admission(row):
 age=(datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat(row['utc'].replace('Z','+00:00'))).total_seconds()
 require(0<=age<=60 and row.get('admitted') is True and not row.get('errors'),'Fresh successful root admission required')
 require(row['root_cap']==ROOT_CAP and row['package_cap']==PACKAGE_CAP and row['floor']==FLOOR and row['guest_peak']==GUEST,'Root capacity contract differs')
 require(row['projected_peak']+SIZE+META<=ROOT_CAP and row['package_current_bytes']+SIZE+META+GUEST<=PACKAGE_CAP,'One ISO+metadata root/package reservation refused')
 require(row['c_free']>=FLOOR+GUEST+SIZE+META,'C floor/guest/one-ISO reservation refused')
 require(any(CROOT.is_relative_to(Path(x['path'])) for x in row['roots']),'Root receipt does not cover evidence tree')

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execute',action='store_true');ap.add_argument('--plan',type=Path,default=Path(__file__).with_name('PLAN.json'))
 for name in ('root-admission','review'):ap.add_argument('--'+name,type=Path);ap.add_argument('--'+name+'-sha256')
 ap.add_argument('--source-seal-sha256');a=ap.parse_args()
 if not a.execute:
  print(json.dumps(dict(status='SOURCE_ONLY_NOT_EXECUTED',plan_sha256=PLAN_SHA,input_sha256=INPUT_SHA,expected_ce034_sha256=TARGET_SHA,one_image_bytes=SIZE,metadata_reserve=META)));return
 require(all((a.root_admission,a.root_admission_sha256,a.review,a.review_sha256,a.source_seal_sha256)),'Explicit source review and fresh admission arguments required')
 here=Path(__file__).resolve().parent;seal=read_json(here/'SOURCE-SEAL.json',a.source_seal_sha256)
 for row in seal['files']:
  p=here/row['path'];require(p.parent==here and p.is_file() and not p.is_symlink() and p.stat().st_size==row['bytes'] and sha(p)==row['sha256'],'Recovery source unit changed')
 review=read_json(a.review,a.review_sha256);require(review.get('status')=='CLEAR' and review.get('recovery_source_seal_sha256')==a.source_seal_sha256,'Exact recovery source review missing')
 plan=read_json(a.plan,PLAN_SHA);validate_shape(plan)
 temp=TARGET.with_name('.track03.recover-ce034.tmp');result_path=TARGET.with_name('recovery-ce034-result.json');parent=canonical(TARGET.parent)
 with contextlib.ExitStack() as stack:
  for p in LOCKS:
   f=stack.enter_context(canonical(p).open('r+'));fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
  absent(TARGET);absent(temp);absent(result_path)
  root=read_json(a.root_admission,a.root_admission_sha256);admission(root)
  for row in plan['metadata']:pin_small(row)
  pin_small(plan['private_room'])
  # Payload hashing happens while restoring their exact output bytes. No ELF,
  # remaster, extraction, second full image or source-media mutation occurs.
  fd=os.open(result_path,os.O_RDWR|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600);receipt=stack.enter_context(os.fdopen(fd,'w+'))
  dfd=os.open(parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW);stack.callback(os.close,dfd)
  record=dict(status='STARTED_UNPUBLISHED',plan_sha256=PLAN_SHA,source_seal_sha256=a.source_seal_sha256,review_sha256=a.review_sha256,root_admission_sha256=a.root_admission_sha256,input=str(INPUT),target=str(TARGET),temporary=str(temp),image_bytes=SIZE,events=[],published=False,source_media_modified=False)
  def save():
   raw=json.dumps(record,indent=2)+'\n';require(len(raw.encode())<32768,'Receipt cap');receipt.seek(0);receipt.write(raw);receipt.truncate();receipt.flush();os.fsync(receipt.fileno())
  def guard():
   used=temp.stat().st_size if temp.exists() else SIZE if TARGET.exists() else 0
   require(used<=SIZE,'One-image cap exceeded');remaining=max(0,SIZE-used)
   require(shutil.disk_usage(parent).free>=FLOOR+GUEST+META+remaining,'C floor/guest/remaining-copy reserve lost')
  def event(s):record['events'].append(s);save()
  start=time.monotonic();save()
  try:
   guard()
   with pinned_reader(plan['input']) as reader:
    source_before=stamp(os.fstat(reader.fileno()))
    fd=os.open(temp,os.O_RDWR|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'w+b') as writer:
     actual,verified=copy_patch(reader,writer,plan,guard,event)
     for row in plan['metadata']:pin_small(row)
     require(sha(a.root_admission)==a.root_admission_sha256,'Admission receipt changed');guard()
     # Revalidate source identity while its original read-only descriptor is held.
     require(stamp(INPUT.stat())==stamp(os.fstat(reader.fileno()))==source_before,'Retained bea identity changed')
     publish(temp,TARGET,writer,dfd,verified,plan['target']['size']);record['published']=True
   literal_target(TARGET,dfd,verified)
   record.update(status='EXACT_CE034_RECOVERED',restored_sha256=actual,source_input_sha256=INPUT_SHA,full_target_readback=True,elapsed_seconds=time.monotonic()-start);save();print(json.dumps(record))
  except BaseException as exc:
   record.update(status='FAILED_PRESERVED_NO_ACCEPTANCE',error=repr(exc),target_exists=os.path.lexists(TARGET),temporary_exists=os.path.lexists(temp),elapsed_seconds=time.monotonic()-start);save();raise

if __name__=='__main__':main()
