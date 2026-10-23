#include "actor_visibility23_world.h"
#include <cassert>
#include <cstring>
#define RE4DC_ACTOR_VISIBILITY23 1
#define RE4DC_SCENERY_SCREEN_MEMO 1
#define RE4DC_SCREEN_WF 640.0f
#define RE4DC_SCREEN_HF 480.0f
#define RE4DC_SCREEN_HALF_WF 320.0f
#define RE4DC_SCREEN_HALF_HF 240.0f
using matrix_t=float[4][4];
static unsigned mode=0,actor_world23_loaded_mode=~0U;
static bool change_on_load=false;
static matrix_t loaded;
static unsigned actor_world23_mode(){return mode;}
static void mat_load(matrix_t* m){std::memcpy(loaded,*m,sizeof(loaded));if(change_on_load)mode^=1;}
#include "screen_actual.inc"
int main(){
 float mv[12]={1,0,0,123,0,1,0,456,0,0,1,-10000};
 float P[7]={0,1,0,1,0,-.001,-1},V[6]={0,0,640,480,0,1};
 load_screen(mv,P,V);assert(actor_world23_loaded_mode==0);
 matrix_t first;std::memcpy(first,loaded,sizeof(first));
 mode=1;load_screen(mv,P,V);assert(actor_world23_loaded_mode==0);
 assert(!std::memcmp(first,loaded,sizeof(first))); // arithmetic/memo unchanged
 mv[3]+=1;load_screen(mv,P,V);assert(actor_world23_loaded_mode==1);
 mode=1U<<18;mv[3]+=1;load_screen(mv,P,V);assert(actor_world23_loaded_mode==mode);
 mode=1U<<19;mv[3]+=1;load_screen(mv,P,V);
 assert(!actor_visibility23::world_mode_supported23(actor_world23_loaded_mode));
 mode=0;change_on_load=true;mv[3]+=1;load_screen(mv,P,V);
 assert(actor_world23_loaded_mode==0&&mode==1); // next transform mismatch refuses
}
