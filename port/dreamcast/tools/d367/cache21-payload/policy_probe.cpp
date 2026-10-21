#include <cstring>
#include <cassert>
#include <cstdio>
#include <climits>
#include "texpack_payload_retry.inc"
int main(){using namespace texpack_payload_retry;unsigned checks=0;
 for(unsigned phase=0;phase<30;++phase){reset();assert(!blocked(0,100));failed(0,100+phase);
  for(unsigned n=100+phase;n<160;++n){assert(blocked(0,n));++checks;}assert(!blocked(0,160));++checks;
 }
 reset();failed(8191,0);assert(blocked(8191,0)&&blocked(8191,29)&&blocked(8191,30)&&blocked(8191,59)&&!blocked(8191,60));checks+=5;
 failed(8192,60);assert(!blocked(8192,60));++checks;
 reset();failed(7,0);assert(!blocked(7,1000000));++checks;
 reset();failed(7,UINT_MAX-15);assert(blocked(7,UINT_MAX)&&blocked(7,14)&&blocked(7,43)&&!blocked(7,44));checks+=4;
 reset();failed(7,55);succeeded(7);assert(!blocked(7,55));++checks;
 failed(7,55);reset();assert(!blocked(7,55));++checks;
 reset();for(unsigned i=0;i<8192;++i){failed(i,0);assert(blocked(i,0));++checks;}
 for(unsigned i=0;i<8192;++i){succeeded(i);assert(!blocked(i,1));++checks;}
 reset();for(unsigned i=0;i<4096;++i)failed(i,10);
 for(unsigned i=4096;i<8192;++i){assert(!blocked(i,11));++checks;}
 assert(source_error("streamed texture upload read failed")&&source_error("streamed header read failed"));checks+=2;
 const char* excluded[]={nullptr,"streamed metadata allocation failed","PVR texture allocation failed","texture pointer allocation failed","texture ownership allocation failed","PVR palette banks exhausted","PVR palette manager uninitialized or banks exhausted","injected mid-upload failure"};
 for(const auto* e:excluded){assert(!source_error(e));++checks;}
 printf("POLICY_PROBE PASS checks=%u maps=%zu epochs=%zu latency=31..60 UI frames\n",checks,sizeof(current)+sizeof(next),sizeof(base)+sizeof(initialized));
}
