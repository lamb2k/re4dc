"""Targeted Mendez window observer; host-only. Execute under census-bound-run.py; no standalone guest launch."""
import hashlib,json,pathlib,queue,re,runpy,struct,subprocess,sys,threading,time
import stat_owned_ram as ram
START=re.compile(r'warp: goto 2 at room frame\s+(\d+)')
END=re.compile(r'warp: goto 3(?:\s|$)')
EVENT_BIT=0x10000000
class IncrementalLines:
    def __init__(self,path):self.path=pathlib.Path(path);self.offset=0;self.pending=b''
    def poll(self):
        try:
            with self.path.open('rb') as f:
                if f.seek(0,2)<self.offset:raise RuntimeError('run-output truncated during owned observation')
                f.seek(self.offset);new=f.read();self.offset=f.tell()
        except FileNotFoundError:return []
        chunks=(self.pending+new).split(b'\n');self.pending=chunks.pop()
        return [x.decode('ascii','replace') for x in chunks]

def summarize(rows):
    baseline=False;started=None;cleared=None;progress=[];previous=None
    for row in rows:
        if not row['event_active']:
            if started is None:baseline=True
            elif cleared is None:cleared=row
        elif started is None and baseline:started=row
        if started and cleared is None and row['event_active']:
            if previous and row['pMotion']!='0x0' and row['pMotion']==previous['pMotion'] and row.get('motion_header_sha256') and row.get('motion_header_sha256')==previous.get('motion_header_sha256') and row['frame']>previous['frame']:
                progress.append({'from_frame':previous['frame'],'to_frame':row['frame'],'pMotion':row['pMotion'],'header_sha256':row.get('motion_header_sha256'),'global_frame':row['Frame_cnt']})
            previous=row
    return {'baseline_event_clear_observed':baseline,'event_set_after_clear_observed':started is not None,'motion_progress_pairs':progress,'event_clear_after_set_observed':cleared is not None,'event_set_sample':started,'event_clear_sample':cleared,'normal_event_state_sequence_observed':bool(started and progress and cleared),'window_jump_certified':False,'qualification':'Event-bit edges and progressing motion are diagnostic evidence only; room10f or a repeated motion pointer/header alone does not authenticate the named window FCV or a complete jump.'}

def main():
    harness=pathlib.Path(sys.argv[1]);ppl_symbol=int(sys.argv[2],0);pg_symbol=int(sys.argv[3],0);args=sys.argv[4:]
    cap=pathlib.Path(args[args.index('--cap')+1]);original=subprocess.Popen;stop=threading.Event();closed=threading.Event();observer=None;guest=None
    rows=[];markers=[];errors=[];shots=[];shotq=queue.Queue(maxsize=3);shot_count=0;started_host=time.monotonic();readers=[]
    receipt={'pPL_symbol':hex(ppl_symbol),'pG_symbol':hex(pg_symbol),'source':'2a14662d4b025031cd93f64eed6a5d8159d473b7','source_fields':{'pos':'cModel+94 Vec3f','stat':'cModel+fc bytes4','pMotion':'cModel+1d8 u32','motState':'cModel+21a u16','frame':'cModel+290 f32','frameMax':'cModel+294 u16','Status_flg1':'GlobalWork+5010 u32','Frame_cnt':'GlobalWork+51e4 u32'},'read_only':True,'interval':'only log goto2 window approach through before goto3 first door','maximum_stills':3,'sample_period_seconds':0.1,'motion_header_bytes':64,'harness_sha256':hashlib.sha256(harness.read_bytes()).hexdigest(),'backend_sha256':hashlib.sha256(pathlib.Path(ram.__file__).read_bytes()).hexdigest()}
    def sample(reader):
        row=reader.player(ppl_symbol);pg=reader.u32(pg_symbol)
        row.update(host_s=round(time.monotonic()-started_host,3),pG=hex(pg),SF1=f'{reader.u32(pg+0x5010):08x}',Frame_cnt=reader.u32(pg+0x51e4),room=f'{struct.unpack("<H",reader.read_pointer(pg+0x4f9e,2))[0]:03x}')
        row['event_active']=bool(int(row['SF1'],16)&EVENT_BIT)
        motion=int(row['pMotion'],16)
        if motion:
            try:
                head=reader.read_pointer(motion,64);row['motion_header_sha256']=hashlib.sha256(head).hexdigest();row['motion_header_hex']=head.hex()
            except (OSError,ValueError) as exc:row['motion_header_read_error']=str(exc)
        return row
    def request_shot(reason,row):
        nonlocal shot_count
        if shot_count>=3 or closed.is_set() or stop.is_set():return
        shotq.put_nowait((shot_count,reason,row.copy()));shot_count+=1
    def capture_worker(proc):
        reader=None
        try:
            while not stop.is_set() or not shotq.empty():
                try:index,reason,requested=shotq.get(timeout=.1)
                except queue.Empty:continue
                record={'index':index,'reason':reason,'requested_state':requested}
                if closed.is_set() or proc.poll() is not None:
                    record['skipped']='door marker or owned guest exit before capture';shots.append(record);continue
                try:
                    if reader is None:reader=ram.OwnedRam(cap,proc.pid)
                    actual=sample(reader);record['capture_start_state']=actual
                    out=cap/'window-stills'/f's{index:02d}-{reason}'
                    ram.capture_frames(cap,out,actual)
                    record.update(path=str(out.relative_to(cap)),capture_end_monotonic=time.monotonic(),door_marker_observed_during_capture=closed.is_set())
                    (out/'capture-binding.json').write_text(json.dumps(record,indent=2)+'\n')
                except Exception as exc:record['error']=repr(exc)
                shots.append(record)
        finally:
            if reader:reader.close()
    def observe(proc):
        reader=None;capture=None;active=False;initial=False;event_seen=False;last_event=False;progress_requested=False;event_clear_requested=False;first_motion=None;last_motion=None;tail=IncrementalLines(cap/'run-output.txt')
        try:
            capture=threading.Thread(target=capture_worker,args=(proc,),daemon=True);capture.start()
            while not stop.is_set() and proc.poll() is None:
                for line in tail.poll():
                    begin=START.search(line)
                    if END.search(line):
                        markers.append({'kind':'door-goto3','host_s':round(time.monotonic()-started_host,3),'line':line});closed.set();active=False
                    elif begin and not closed.is_set():
                        markers.append({'kind':'window-goto2','host_s':round(time.monotonic()-started_host,3),'room_frame':int(begin.group(1)),'line':line});active=True
                if not active:stop.wait(.1);continue
                try:
                    if reader is None:reader=ram.OwnedRam(cap,proc.pid)
                    row=sample(reader);rows.append(row)
                    if not initial:
                        request_shot('approach',row);initial=True
                    if row['event_active']:
                        event_seen=True
                        if first_motion is None:first_motion=row
                        if last_motion and not progress_requested and row['pMotion']==last_motion['pMotion'] and row.get('motion_header_sha256') and row.get('motion_header_sha256')==last_motion.get('motion_header_sha256') and row['frame']>last_motion['frame']:
                            request_shot('event-motion-progress',row);progress_requested=True
                        last_motion=row
                    elif event_seen and last_event and not event_clear_requested:
                        request_shot('event-clear',row);event_clear_requested=True
                    last_event=row['event_active']
                except (OSError,ValueError) as exc:
                    if len(errors)<20:errors.append({'host_s':round(time.monotonic()-started_host,3),'error':str(exc)})
                stop.wait(.1)
        except Exception as exc:errors.append({'fatal':repr(exc)})
        finally:
            if reader:reader.close()
            if capture:capture.join(timeout=3)
            receipt.update(pid=proc.pid,markers=markers,samples=len(rows),summary=summarize(rows),shots=shots,errors=errors,window_interval_reached=any(x['kind']=='window-goto2' for x in markers),first_door_marker_reached=closed.is_set(),capture_worker_still_running=bool(capture and capture.is_alive()))
            (cap/'window-ram-samples.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
            (cap/'window-observation.json').write_text(json.dumps(receipt,indent=2)+'\n')
    class ObservedPopen(original):
        def __init__(self,*a,**kw):
            nonlocal observer,guest
            cmd=a[0] if a else kw.get('args',[])
            is_guest=isinstance(cmd,(list,tuple)) and pathlib.Path(str(cmd[0])).name.lower()=='flycast.exe'
            if is_guest and guest is not None:raise RuntimeError('second guest refused')
            super().__init__(*a,**kw)
            if is_guest:
                guest=self;observer=threading.Thread(target=observe,args=(self,),daemon=True);observer.start()
    subprocess.Popen=ObservedPopen
    try:
        sys.argv=[str(harness),*args];runpy.run_path(str(harness),run_name='__main__')
    finally:
        stop.set()
        if observer:observer.join(timeout=5)

if __name__=='__main__':main()
