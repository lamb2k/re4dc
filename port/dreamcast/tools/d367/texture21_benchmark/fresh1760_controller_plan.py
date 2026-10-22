"""Build a metadata-only candidate controller plan from actual qualified inputs.
Never allocates, creates output parents, stages, spawns or executes the writer.
"""
import argparse,json,os,sys
from pathlib import Path
import owned_windows_fresh1760_image_job as c
INSTALL=Path(r'C:\Game Dev\Emulators\codex-lanes\castle-controls21\owned-windows-fresh1760-image-job.py')
def build(image_plan,image_sha,child,child_sha,python,out):
 if os.name!='nt'or not sys.dont_write_bytecode:raise ValueError('Native source-only metadata builder; bytecode disabled')
 if out.exists()or out.is_symlink()or not out.parent.is_dir()or not c.within(out,c.ALLOCATIONS)or c.within(out,c.PRODUCTION):raise ValueError('Exclusive external lane metadata plan output required')
 for p,h in((image_plan,image_sha),(child,child_sha),(INSTALL,c.sha(c.__file__))):
  if c.sha(c.canonical(p))!=h:raise ValueError('Actual bound plan/child/controller bytes')
 if not c.within(child,c.ALLOCATIONS)or c.within(child,c.PRODUCTION):raise ValueError('ChildA separate lane scope')
 ip=json.loads(image_plan.read_text());adref=ip['programme_admission'];ap=c.canonical(adref['path']);ad=json.loads(ap.read_text());m=ip['programme'];root=c.PRODUCTION
 inputs={str(p):c.sha(p)for p in(c.canonical(python),INSTALL,Path(__file__).absolute(),image_plan,child,c.PARENT_SEAL,c.SOURCE_SEAL,ap)}
 for name,digest in ip['source_sha256'].items():inputs[str(c.WRITER.parent/name)]=digest
 for name in('qualification','independent','consumer','tool_closure','manifest'):
  ref=ad[name];inputs[str(c.canonical(ref['path']))]=ref['sha256']
 p=dict(schema='fresh1760-candidate-controller-plan-v1',source=c.SOURCE,arm='M1',approved_output_root=str(root),approved_payload_roots=[],receipt=str(root/'controller.json'),log=str(root/'controller.log'),new_outputs=[str(root/'gdemu')]+[str(root/'gdemu'/n)for n in('track01.bin','track02.raw','disc.gdi','track03.iso')]+[str(root/'full-readback.json'),str(root/'child-result.json')],argv=[str(c.canonical(python)),str(c.WRITER),'write','--plan',str(image_plan),'--plan-sha256',image_sha,'--allocation',str(child),'--allocation-sha256',child_sha,'--arm','M1'],cwd=str(c.WRITER.parent),input_sha256=inputs,image_plan_path=str(image_plan),image_plan_sha256=image_sha,programme_admission_path=str(ap),programme_admission_sha256=adref['sha256'],ELF_sha256=m['ELF']['sha256'],programme_sha256=m['programme_sha256'],consumer_sha256=ad['consumer']['sha256'],child_allocation_path=str(child),child_allocation_sha256=child_sha,absolute_seconds=130,inner_seconds=120,peer_reserved_bytes=67108864,max_output_bytes=c.PACK_CAP,metadata_cap_bytes=c.METADATA_CAP,log_limit_bytes=c.MAX_LOG,expected_image_bytes=ip['image_bytes'],expected_image_sha256=ip['arms']['M1']['predicted']['sha256'],uncompressed_forecast_bytes=ip['proposal']['exact_uncompressed_forecast_bytes'],allocation_status='PLAN_ONLY_NOT_ALLOCATION')
 c.require_image_bindings(p,inputs)
 ca=json.loads(child.read_text());expected=dict(stage_authorized=True,candidate_contract_valid=True,source=c.SOURCE,arm='M1',plan_sha256=image_sha,writer_source_sha256=c.WRITER_SHA,controller_path=str(INSTALL),controller_source_sha256=c.sha(INSTALL),approved_output_root=str(root),allocation_cap_bytes=c.PACK_CAP,metadata_cap_bytes=c.METADATA_CAP,peer_reserved_bytes=67108864,runtime_floor_bytes=c.BASE_FLOOR,inner_seconds=120)
 if not ca.get('allocation_id')or any(ca.get(k)!=v for k,v in expected.items())or ca.get('compression_credits'):raise ValueError('Exact actual root childA, not proposal placeholders')
 raw=(json.dumps(p,indent=2)+'\n').encode()
 if len(raw)>262144:raise ValueError('Bounded controller metadata')
 with out.open('xb')as f:f.write(raw);f.flush();os.fsync(f.fileno())
 return dict(status='METADATA_PLAN_ONLY_NO_OUTPUTS_OR_JOB',path=str(out),sha256=c.sha(out),argv=p['argv'],predicted_image_bytes=p['expected_image_bytes'],predicted_image_sha256=p['expected_image_sha256'])
def main():
 a=argparse.ArgumentParser(description=__doc__)
 for name in('image-plan','child-allocation','python','out'):a.add_argument('--'+name,type=Path,required=True)
 for name in('image-plan-sha256','child-allocation-sha256'):a.add_argument('--'+name,required=True)
 x=a.parse_args();print(json.dumps(build(x.image_plan,x.image_plan_sha256,x.child_allocation,x.child_allocation_sha256,x.python,x.out)))
if __name__=='__main__':main()
