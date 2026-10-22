"""Narrow actual cleanup/retained proof controls; no native calls at import."""

def note(errors,item):
    if len(errors)<32:errors.append(item)
    else:errors[-1]['additional_failures']=errors[-1].get('additional_failures',0)+1

def failure(exc):return {'type':type(exc).__name__,'text':str(exc),'winerror':getattr(exc,'winerror',None)}

def job_cleanup(backend,job,inner,pinned,errors):
    state={'private_job_empty':False,'inner_finalized':inner is None}
    # Every independent action is attempted even when an earlier action fails.
    for name,action in [('pipe_close',lambda:backend.close_release_pipe(inner) if inner is not None else None),
                        ('job_stop',lambda:backend.stop_private_job(job)),
                        ('inner_wait',lambda:backend.wait(inner) if inner is not None else None)]:
        try:action()
        except BaseException as exc:note(errors,{'operation':name,**failure(exc)})
    if inner is not None:
        try:
            identity=backend.retained_identity(inner.pid,int(inner._handle),pinned)
            times=backend.times(int(inner._handle));status=backend.k.WaitForSingleObject(int(inner._handle),0)
            state['inner_exit']={'identity':identity,'times':times,'exit_code':inner.returncode,'wait_status':status}
            state['inner_finalized']=identity==pinned and times[0]==pinned['start_filetime'] and times[1]>=times[0]>0 and status==0
        except BaseException as exc:note(errors,{'operation':'inner_finalization',**failure(exc)})
    try:backend.wait_private_job_empty(job);state['private_job_empty']=True
    except BaseException as exc:note(errors,{'operation':'job_empty',**failure(exc)})
    state['safe_to_disarm']=state['private_job_empty'] and state['inner_finalized']
    return state

def retained_cleanup(proc,terminate,times,wait_status,pinned,errors):
    state={'signaled_finalized':proc is None}
    if proc is None:return state
    try:
        if proc.poll() is None:terminate(int(proc._handle))
    except BaseException as exc:note(errors,{'operation':'coordinator_terminate',**failure(exc)})
    try:proc.wait(timeout=.15)
    except BaseException as exc:note(errors,{'operation':'coordinator_wait',**failure(exc)})
    try:
        stamp=times(int(proc._handle));status=wait_status(int(proc._handle))
        state.update(retained_times=stamp,wait_status=status)
        state['signaled_finalized']=(pinned is None or stamp[0]==pinned) and stamp[1]>=stamp[0]>0 and status==0
        if state['signaled_finalized']:state['actual_seconds']=(stamp[1]-stamp[0])/1e7
    except BaseException as exc:note(errors,{'operation':'coordinator_finalization',**failure(exc)})
    return state

def disarm_if_proven(safe,done,thread,close):
    if not safe:raise RuntimeError('HOLD: cleanup proof missing; guardian and handles retained')
    done.set();thread.join(timeout=.2)
    if thread.is_alive():raise RuntimeError('HOLD: guardian not joined; handles retained')
    close()
