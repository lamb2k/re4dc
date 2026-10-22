from pathlib import Path
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18');p=L/'test-guard-v3-mocked-faults.py';assert not p.exists();s=(L/'test-guard-v2-mocked-faults.py').read_text().replace('resources-v2.py','resources-v3.py').replace('guard-v2-mocked-fault-tests.json','guard-v3-mocked-fault-tests.json').replace("('absolute_stop',47.2)","('absolute_stop',47.2),('slow_sampler',44.9)").replace("'route-walk-resource-guard-faulttest-'","'route-walk-resource-guard-v3-faulttest-'")
s=s.replace("if case=='disk_query_failure':shutil.disk_usage=", "if case=='slow_sampler':\n  def slowdisk(p):time.sleep(3);return origdisk(p)\n  shutil.disk_usage=slowdisk\n elif case=='disk_query_failure':shutil.disk_usage=")
s=s.replace("['disk_query_failure','missing_SDL_window','WM_CLOSE_failure']", "['disk_query_failure','missing_SDL_window','WM_CLOSE_failure','slow_sampler']")
s=s.replace("rows.append(dict(case=case", "if case=='slow_sampler':time.sleep(2.2)\n rows.append(dict(case=case")
s=s.replace('PASS5 synthetic','PASS6 synthetic').replace('hard47.1stop.','hard47.1stop plus filesystem3s stall starting44.9s; isolated sampler must fail closed before47.5.')
compile(s,str(p),'exec');p.write_text(s)
