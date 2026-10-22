from pathlib import Path
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18');p=L/'test-guard-v3-mocked-faults-timed.py';assert not p.exists();s=(L/'test-guard-v3-mocked-faults.py').read_text().replace('guard-v3-mocked-fault-tests.json','guard-v3-mocked-fault-tests-timed.json').replace('route-walk-resource-guard-v3-faulttest-','route-walk-resource-guard-v3-timed-faulttest-')
s=s.replace("state['terminates']+=1;state['alive']=False;return 1","state['terminates']+=1;state['termination_process_age']=time.time()-(owner['start_filetime']/1e7-11644473600);state['alive']=False;return 1")
s=s.replace("assert not state['alive'] and state['handlecloses']==1,(case,state)","assert not state['alive'] and state['handlecloses']==1,(case,state)\n if state['terminates']:assert state['termination_process_age']<47.5,(case,state)")
compile(s,str(p),'exec');p.write_text(s)
