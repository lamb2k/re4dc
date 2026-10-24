import importlib.util,pathlib
p=pathlib.Path('/mnt/c/Game Dev/Emulators/codex-lanes/world-emit23/runtime-support/analyse-meter-v1.py')
s=importlib.util.spec_from_file_location('meter',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
r=pathlib.Path('/mnt/c/Flycast-Evidence/re4-dreamcast/world-emit23-takeover/7a3af776')
for arm,scene in [('E','b1'),('B','b1'),('R','s2'),('L','s2'),('E','s2')]:
 c=m.inspect(r,arm,scene);print('PASS',arm,scene,len(c['windows']),'whole candidate windows, no fallback/abort/refusal, runtimeLOD5')