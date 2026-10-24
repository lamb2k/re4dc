#!/usr/bin/env python3
"""Independent frozen-source review; no SDK/target/guest/data operations."""
import argparse,hashlib,importlib.util,json,resource,subprocess,tempfile,time
from pathlib import Path
SOURCE='b6b4fa7a3cf3a5244d28a31eae9a8bf42f18ce45'
BASE='fb254e82ee6f9a3d9e34d53d1d442348a46b9cf2'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--tree',required=True,type=Path);ap.add_argument('--author-receipts',required=True,type=Path);ap.add_argument('--out',required=True,type=Path);a=ap.parse_args()
 if a.out.exists():raise ValueError('Preserve previous review')
 resource.setrlimit(resource.RLIMIT_AS,(268435456,268435456));a.out.mkdir(parents=True);start=time.monotonic()
 assert subprocess.check_output(['git','-C',str(a.tree),'rev-parse','HEAD'],text=True).strip()==SOURCE
 seal=json.loads((a.author_receipts/'SOURCE-SEAL.json').read_text());assert seal['source_revision']==SOURCE
 for item in seal['members']:
  p=a.tree/item['path'];assert p.stat().st_size==item['bytes'] and sha(p)==item['sha256']
 assert sha(a.author_receipts/'HOST-RESULTS.json')==seal['host_receipt_sha256']
 untouched=[]
 for rel in ('port/dreamcast/game/t2exact.mk','port/dreamcast/game/platform/include/pvs23_runtime.inc','port/dreamcast/game/platform/include/pvs23_proof.hpp'):
  data=(a.tree/rel).read_bytes();assert data==subprocess.check_output(['git','-C',str(a.tree),'show',BASE+':'+rel]);untouched.append(dict(path=rel,sha256=hashlib.sha256(data).hexdigest()))
 path=a.tree/'port/dreamcast/tools/d367/pvs_batch_compose24/test_compose.py'
 r=subprocess.run(['python3','-B',str(path),'-v'],cwd=a.tree,capture_output=True,text=True);assert not r.returncode,r.stdout+r.stderr
 (a.out/'host.log').write_text(r.stdout+r.stderr)
 spec=importlib.util.spec_from_file_location('reviewed_controls',path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);records=[]
 class Review(mod.Controls):
  def build(self,src,expected=True):
   with tempfile.TemporaryDirectory(prefix='iv23-batch-review-',dir='/dev/shm') as tmp:
    tmp=Path(tmp);(tmp/'unit.cpp').write_text(src)
    c=subprocess.run(['g++','-std=c++17','-O1','-fsanitize=undefined','-fno-sanitize-recover=all',str(tmp/'unit.cpp'),'-o',str(tmp/'run')],capture_output=True,text=True);assert not c.returncode,c.stderr
    run=subprocess.run([str(tmp/'run')],capture_output=True,text=True);assert (run.returncode==0)==expected,run.stderr
    if not expected:assert 'Assertion' in run.stderr and 'failed' in run.stderr,run.stderr
    records.append(dict(expected_success=expected,returncode=run.returncode,stderr=run.stderr))
 t=Review();t.test_actual_hot_cold_queue_snapshot0_and1();t.test_receipt_only_dispatch_and_mutant();t.test_semantic_mutants()
 # Additional single-event capacity test: a stale pending diagnostic must not
 # become a second ticket's acquisition or overwrite its captured old identity.
 prefix=t.fixture().split('int main(){')[0]
 extra=prefix+"""int main(){
 frame=22;sourceWorldPreparedFrame=22;sourceWorldPreparedKey={8,9};sourceWorldAcquired=0;
 sourceWorldAcquireDiagnostic={{1,2},17,true};sourceWorldTextureAcquired({8,9});
 assert(!sourceWorldAcquired && sourceWorldAcquireDiagnostic.pending && sourceWorldAcquireDiagnostic.frame==17 && sourceWorldAcquireDiagnostic.key.crc==1 && sourceWorldAcquireDiagnostic.key.fnv==2);
 direct_open=true;sourceWorldTexturePrepare();assert(!logs && sourceWorldAcquireDiagnostic.pending && sourceWorldPreparedFrame==22);
 direct_open=false;sourceWorldDiagnosticSqHeld=true;sourceWorldTexturePrepare();assert(!logs && sourceWorldAcquireDiagnostic.pending && sourceWorldPreparedFrame==22);
 sourceWorldDiagnosticSqHeld=false;sourceWorldTexturePrepare();assert(logs==2 && !sourceWorldAcquireDiagnostic.pending && !sourceWorldAcquired && sourceWorldPreparedFrame==0);
 assert(log_rows[0].frame==17 && log_rows[0].crc==1 && log_rows[0].fnv==2);return 0;}
"""
 t.build(extra)
 out=dict(kind='Independent bounded source/host review; no renderer acceptance',source=SOURCE,base=BASE,source_seal_sha256=sha(a.author_receipts/'SOURCE-SEAL.json'),host_receipt_sha256=sha(a.author_receipts/'HOST-RESULTS.json'),members_verified=len(seal['members']),author_methods=7,author_host_returncode=r.returncode,host_log_sha256=sha(a.out/'host.log'),independent_ubsan_controls=records,assertion_mutants=sum(not x['expected_success'] for x in records),untouched=untouched,review_tool_sha256=sha(__file__),elapsed_seconds=time.monotonic()-start,limits=dict(address_space_bytes=268435456,peak_child_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,jobs=1),actual_new_cuts=0,SDK_run=False,guest_run=False,renderer_source_receipts_admitted=False)
 (a.out/'RECEIPT.json').write_text(json.dumps(out,indent=1)+'\n');print(json.dumps(dict(source=SOURCE,methods=7,assertion_mutants=out['assertion_mutants'],additional_capacity_control=True,receipt_sha256=sha(a.out/'RECEIPT.json'))))
if __name__=='__main__':main()
