import importlib.util,json,os,pathlib,subprocess,sys,time
case,out=sys.argv[1],pathlib.Path(sys.argv[2]);(out/'child-entered.txt').write_text(case)
if case in ('normal','descendant'):
 from contain import API,API_SHA,sha
 if sha(API)!=API_SHA:raise ValueError('API pin changed')
 s=importlib.util.spec_from_file_location('control_api',API);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);api=m.WindowsApi()
 if case=='descendant':
  p=subprocess.Popen([sys.executable,'-B','-c','import time;time.sleep(20)']);(out/'descendant.pid').write_text(str(p.pid))
 (out/'current-job-pids.json').write_text(json.dumps({'self':os.getpid(),'pids':api.job_pids(None)}))
 if case=='descendant':time.sleep(20)
elif case in ('deadline','late','assignfail'):time.sleep(20)
elif case=='cap':(out/'bounded-overcap.bin').write_bytes(bytes(1024*1024));time.sleep(20)
