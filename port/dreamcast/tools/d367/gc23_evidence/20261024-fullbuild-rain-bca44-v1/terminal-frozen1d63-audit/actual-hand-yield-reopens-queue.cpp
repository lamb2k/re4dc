
#include <cassert>
using mutex_t=int;int lh_mutex;struct kthread_t{}thread;kthread_t*job_thd=&thread;unsigned char memory[64],*job_mem=memory;int job_blob=0,job_state=2;unsigned job_n=2,nblobs=2,aica=0,yields=0,refill[4],cell_blob[4],joins=0,frees=0;int job_queue[8],want[2];
void mutex_lock(int*){}void mutex_unlock(int*){}void thd_join(kthread_t*t,void*){assert(t==&thread);++joins;}void re4dc_motion_free(void*p){assert(p==memory);++frees;}void snd_mem_free(unsigned){}
namespace leon_hand_pack{}
void job_enqueue(int b) {
    if(b<0 || unsigned(b)>=nblobs || b==job_blob)return;
    for(unsigned i=0;i<job_n;++i)if(job_queue[i]==b)return;
    if(job_n<8)job_queue[job_n++]=b;
}
extern "C" void re4dc_leon_hands_yield() {
    using namespace leon_hand_pack;
    mutex_lock(&lh_mutex);
#if RE4DC_GC_ASSET_GATE
    gcasset_hand_job={};gcasset_hand_scratch={};
    for(auto& cell:gcasset_hand_cell)cell={};gcasset_hand_aica=0;
#endif
    if(job_thd){thd_join(job_thd,nullptr);job_thd=nullptr;re4dc_motion_free(job_mem);job_mem=nullptr;job_blob=-1;job_state=0;}
    job_n=0;want[0]=want[1]=-1;
    if(!aica){mutex_unlock(&lh_mutex);return;}
    snd_mem_free(aica);aica=0;++yields;
    for(unsigned c=0;c<4;++c){refill[c]=cell_blob[c];cell_blob[c]=-1;}
    mutex_unlock(&lh_mutex);
}
int main(){re4dc_leon_hands_yield();assert(joins==1&&frees==1&&!job_thd&&!job_mem&&!job_n&&job_blob==-1);job_enqueue(1);assert(job_n==1&&job_queue[0]==1);}
