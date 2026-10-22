"""Fixture-only exact startup semantics, retaining original owned process on failure."""
import ctypes,subprocess

def spawn_retained(backend,cmd,job,popen=None):
    if job!=backend.job:raise RuntimeError('foreign job')
    if popen is None:popen=subprocess.Popen
    proc=popen(cmd,stdin=subprocess.PIPE,creationflags=subprocess.DETACHED_PROCESS)
    # Ownership exists immediately after Popen. Never clear/close it on failure.
    # Outer universal cleanup and captured-job guardian own every later outcome.
    backend.inner=proc;backend.inner_identity=None
    backend.inner_identity=backend.info(proc.pid,int(proc._handle))
    backend.checked(backend.k.AssignProcessToJobObject(job,int(proc._handle)))
    member=ctypes.c_int();backend.checked(backend.k.IsProcessInJob(int(proc._handle),job,ctypes.byref(member)))
    if not member.value:raise RuntimeError('job assignment not verified')
    return proc
