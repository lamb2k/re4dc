from pathlib import Path
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18');p=L/'test-guard-v4-mocked-adversarial.py';assert not p.exists();s=(L/'test-guard-v3-mocked-faults-timed.py').read_text().replace('resources-v3.py','resources-v4.py').replace('guard-v3-mocked-fault-tests-timed.json','guard-v4-mocked-adversarial-tests.json').replace('route-walk-resource-guard-v3-timed-faulttest-','route-walk-resource-guard-v4-adversarial-')
s=s.replace("('slow_sampler',44.9)","('slow_sampler',44.9),('normal_exit_queries_fail',46),('exit_between_identity_calls',46),('reused_PID_new_identity_rejected',5)")
s=s.replace("state=dict(alive=True,terminates=0,closes=0,handlecloses=0)","state=dict(alive=True,terminates=0,closes=0,handlecloses=0,times_calls=0,dead_path_queries=0)")
a=s.index(' def times(');b=s.index(' def terminate(',a)
s=s[:a]+''' def times(h,a,b,c,d):
  state['times_calls']+=1
  if case=='exit_between_identity_calls'and state['times_calls']==2:state['alive']=False;return 0
  if not state['alive']and case in ['normal_exit_queries_fail','exit_between_identity_calls']:return 0
  start=owner['start_filetime']+(1 if case=='reused_PID_new_identity_rejected'else 0)
  a._obj.dwLowDateTime=start&0xffffffff;a._obj.dwHighDateTime=start>>32;return 1
 def query(h,z,b,n):
  if not state['alive']:state['dead_path_queries']+=1;return 0
  b.value=owner['path'];return 1
 def exitcode(h,c):c._obj.value=259 if state['alive']else 0;return 1
'''+s[b:]
s=s.replace('k.CloseHandle=Fn(close)','k.CloseHandle=Fn(close);k.GetExitCodeProcess=Fn(exitcode)',1)
s=s.replace("assert not state['alive'] and state['handlecloses']==1,(case,state)","assert state['handlecloses']==1,(case,state)\n if case=='reused_PID_new_identity_rejected':assert state['alive'] and not state['terminates']and not state['closes']\n else:assert not state['alive'],(case,state)\n assert not state['dead_path_queries'],(case,state)")
s=s.replace("assert receipt['process_exited']", "assert receipt['process_exited']==(case!='reused_PID_new_identity_rejected')")
s=s.replace("else:assert error is None,(case,error)","elif case=='reused_PID_new_identity_rejected':assert error\n else:assert error is None,(case,error)")
s=s.replace('PASS6 synthetic','PASS9 synthetic').replace('plus filesystem3s stall starting44.9s; isolated sampler must fail closed before47.5.','plusfilesystem3sstall starting44.9; normalpostexitqueriesfail; exitbetweenidentitycalls; reusedPIDnewstartidentitymustberejectedwithouttouchingotherprocess. All real APIs mocked.')
compile(s,str(p),'exec');p.write_text(s)
