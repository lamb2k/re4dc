"""Run existing avk simulator on an explicitly labelled instruction schedule; no caches."""
import argparse,hashlib,importlib.util,json,pathlib
P=pathlib.Path(__file__).resolve();SIM=P.parents[2]/'game30/avk/sim.py'
def model(schedule,triangles,vertices,source_kind):
 if triangles<=0 or vertices<=0:raise ValueError('positive denominators required')
 if source_kind not in ('illustrative','disassembly','candidate-source'):raise ValueError('explicit source kind required')
 spec=importlib.util.spec_from_file_location('existing_avk_sim',SIM);sim=importlib.util.module_from_spec(spec);spec.loader.exec_module(sim);text=pathlib.Path(schedule).read_text();cycles=sim.simulate(text.splitlines(),iters=100)
 return dict(scope='MODELLED no-cache in-order issue only; not hardware/Flycast/frame timing',source_kind=source_kind,schedule_sha256=hashlib.sha256(text.encode()).hexdigest(),sim_sha256=hashlib.sha256(SIM.read_bytes()).hexdigest(),cycles_per_iteration=cycles,cycles_per_triangle=cycles/triangles,cycles_per_vertex=cycles/vertices,limitations=['no cache misses','no complete strip/run/clip/emit cost unless schedule includes them','straight sequence assumes inner branches not taken','no GPU/TA/transfer timing'])
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('schedule');p.add_argument('--triangles',type=int,required=True);p.add_argument('--vertices',type=int,required=True);p.add_argument('--source-kind',required=True);a=p.parse_args();print(json.dumps(model(a.schedule,a.triangles,a.vertices,a.source_kind),indent=2))
