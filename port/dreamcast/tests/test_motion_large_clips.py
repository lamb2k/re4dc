#!/usr/bin/env python3
"""Private audited em32 clips through the actual native cache, without game bytes in Git.
Usage: --assets <prepared em32 dir> --output <new directory>.
"""
from pathlib import Path
import argparse,json,shutil,subprocess
import test_motion_residency as base
import test_motion_bounded_r11f as bounded

MAIN=r'''
void exact(const Archive& a,unsigned i,unsigned* keys){
 auto* row=a.a+a.mtc()+32+20*i;char path[128];
 snprintf(path,sizeof(path),"%s/mot/%08x-%08x.fcv",root.c_str(),word(row+8),word(row+12));auto raw=read_bytes_file(path);
 auto* proxy=(unsigned char*)a.proxy(i);unsigned n=proxy[2],head=((3+3*n+3)&~3u)+4+4*n;
 auto* cached=(unsigned char*)keys-head+4*n;
 assert(raw.size()==a.size(i));assert(!memcmp(cached+head,raw.data()+head,raw.size()-head));verify_keys(proxy,keys);
}
void visit_exact(const Archive& a,unsigned i){unsigned* t=nullptr;int token=acquire(a,i,&t);exact(a,i,t);re4dc_motion_release(token);}
int main(int argc,char**argv){assert(argc==2);root=argv[1];Archive em("em32.arc");
 const auto pristine=read_bytes_file(root+"/em32.arc");
#ifndef RE4DC_MOTION_LARGE_CLIPS
 assert(!re4dc_motion_bind(em.a,em.bytes)&&!heap_live);puts("{\"off_refuses_large\":true}");return 0;
#else
 assert(em.count()==98);
 for(unsigned test=0;test<12;++test){auto bad=std::vector<unsigned char>(em.a,em.a+em.bytes);unsigned m=em.mtc(),r=word(em.a+4);
  switch(test){case 0:put(bad.data(),m+8,3);break;case 1:put(bad.data(),m+28,131104);break;
   case 2:put(bad.data(),m+12,97);break;case 3:put(bad.data(),m+20,0);break;case 4:put(bad.data(),r,89);break;
   case 5:put(bad.data(),r+28,0);break;case 6:put(bad.data(),r+32,0);break;case 7:put(bad.data(),m+32+16,1);break;
   case 8:put(bad.data(),m+32+4,131104);break;case 9:put(bad.data(),m+52,word(bad.data()+m+32));break;
   case 10:put(bad.data(),m+24,em.bytes-32);break;case 11:bad[100]^=1;break;}
  assert(!re4dc_motion_bind(bad.data(),bad.size())&&!heap_live);
 }
 for(int failat=0;failat<3;++failat){allocation_calls=0;fail_allocation=failat;assert(!re4dc_motion_bind(em.a,em.bytes));
  Re4dcMotionStats s{};re4dc_motion_get_stats(&s);assert(!heap_live&&!s.metadata_bytes&&!s.resident_bytes);}
 fail_allocation=-1;assert(re4dc_motion_bind(em.a,em.bytes));const unsigned reserved=heap_live;assert(allocations.size()==3);
 for(unsigned round=0;round<3;++round)for(unsigned i=0;i<em.count();++i)visit_exact(em,i);
 assert(heap_live==reserved&&allocations.size()==3);
 unsigned largest=0,second=0;for(unsigned i=0;i<em.count();++i)if(em.size(i)>em.size(largest))largest=i;
 second=largest?0:1;for(unsigned i=0;i<em.count();++i)if(i!=largest&&em.size(i)>em.size(second))second=i;
 unsigned thirdid=0;while(thirdid==largest||thirdid==second)++thirdid;
 unsigned *one=nullptr,*two=nullptr,*third=nullptr;int x=acquire(em,largest,&one),y=acquire(em,second,&two);bool refused=false;
 try{int z=acquire(em,thirdid,&third);re4dc_motion_release(z);}catch(const std::runtime_error&){refused=true;}
 assert(refused&&heap_live==reserved);exact(em,largest,one);exact(em,second,two);re4dc_motion_release(y);re4dc_motion_release(x);
 assert(!re4dc_motion_thread_busy(thd_current));
 re4dc_motion_retire_all();assert(!heap_live);assert(re4dc_motion_bind(em.a,em.bytes));const unsigned bound=heap_live;
 io_fault=2;refused=false;try{visit_exact(em,largest);}catch(const std::runtime_error&){refused=true;}
 assert(refused&&heap_live==bound&&!re4dc_motion_thread_busy(thd_current));io_fault=0;visit_exact(em,largest);
 io_fault=1;visit_exact(em,(largest+1)%em.count());io_fault=0;assert(heap_live==bound&&fault_reads);
 unsigned k=(largest+2)%em.count();auto* row=em.a+em.mtc()+32+20*k;char file[128];
 snprintf(file,sizeof(file),"%s/mot/%08x-%08x.fcv",root.c_str(),word(row+8),word(row+12));auto data=read_bytes_file(file);
 {auto bad=data;bad.back()^=1;std::ofstream f(file,std::ios::binary);f.write((char*)bad.data(),bad.size());}
 refused=false;try{visit_exact(em,k);}catch(const std::runtime_error&){refused=true;}assert(refused&&heap_live==bound);
 {std::ofstream f(file,std::ios::binary);f.write((char*)data.data(),data.size());}visit_exact(em,k);
 re4dc_motion_unbind(em.a);assert(!heap_live&&allocations.empty());assert(!memcmp(em.a,pristine.data(),em.bytes));
 printf("{\"clips\":98,\"rounds\":3,\"largest\":102336,\"cells\":3,\"host_reserved\":%u,\"two_pins_survive_third_refusal\":true,\"fault_reads\":%u}\n",reserved,fault_reads);
#endif
}
'''

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--assets',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
 a.output.mkdir();data=a.output/'assets';shutil.copytree(a.assets,data)
 flags=bounded.FLAGS[:];bounded.FLAGS=[x for x in flags if not x.startswith('-DRE4DC_MOTION_RESERVE_SPILL=')]+['-DRE4DC_MOTION_RESERVE_SPILL=0']
 reports={}
 for use_bounded in [False,True]:
  for large in [False,True]:
   for fast in [False,True]:
    label=f'b{int(use_bounded)}-l{int(large)}-f{int(fast)}'
    if large:bounded.FLAGS+=['-DRE4DC_MOTION_LARGE_CLIPS=1']
    exe=bounded.compile_test(a.output/label,MAIN,fast=fast,bounded=use_bounded)
    if large:bounded.FLAGS.remove('-DRE4DC_MOTION_LARGE_CLIPS=1')
    r=subprocess.run([str(exe),str(data)],capture_output=True,text=True,timeout=60)
    if r.returncode:raise RuntimeError(label+' '+r.stdout+r.stderr)
    reports[label]=json.loads(r.stdout)
 (a.output/'results.json').write_text(json.dumps(reports,indent=2)+'\n');print(json.dumps(reports,indent=2))
if __name__=='__main__':main()
