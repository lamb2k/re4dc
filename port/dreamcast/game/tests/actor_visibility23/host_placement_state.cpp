// Build host-only with the exact extracted current placements_intact definition.
#include <cstdint>
#include <cstring>
#define RE4DC_PS2_WORLD_DYNAMIC 1
#define RE4DC_PS2_WORLD_PARTS 1
#define RE4DC_PS2_WORLD_ROOT_POSE 0
#define RE4DC_PS2_PLACE_GATE 1
#define RE4DC_PS2_AREA_HIDE 1
namespace dyn {
constexpr unsigned kIds=250,kNone=255;
struct PartPose {const unsigned char* part;float pose[9];};
struct Slot {const unsigned char* obj;std::uint32_t serial;float rest[12];PartPose* parts;unsigned nparts,pose_offset;bool source;};
unsigned char idbuf[95],*ids=idbuf;Slot slotsbuf[2],*slots=slotsbuf;unsigned nids=95;
unsigned char slot_of[kIds];unsigned off_flag=0,off_serial=4,off_mat=8;
}
namespace gate {unsigned room=0x119;constexpr unsigned kMax=95;unsigned owned[3],cur[3],want[3];}
namespace area {bool cur=false;unsigned hidden=0;bool hide(unsigned p){return p==hidden;}}
#include "placements_actual.inc"
static unsigned char object[2][64],part[2][36];static dyn::PartPose pose[2];
extern "C" void host_real_state(unsigned state){
 std::memset(dyn::slot_of,255,sizeof(dyn::slot_of));std::memset(dyn::idbuf,255,sizeof(dyn::idbuf));
 std::memset(gate::owned,0,sizeof(gate::owned));std::memset(gate::cur,0,sizeof(gate::cur));std::memset(gate::want,0,sizeof(gate::want));area::cur=false;
 for(unsigned i=0;i<2;i++){
  const unsigned field=i?7:5;dyn::idbuf[field]=field;dyn::slot_of[field]=i;
  std::memset(object[i],0,sizeof(object[i]));std::memset(part[i],0,sizeof(part[i]));
  unsigned flag=7,serial=1;std::memcpy(object[i],&flag,4);std::memcpy(object[i]+4,&serial,4);
  auto& s=dyn::slotsbuf[i];s={};s.obj=object[i];s.serial=1;pose[i]={};pose[i].part=part[i];s.parts=pose+i;s.nparts=1;
  if(state==1){flag=5;std::memcpy(object[i],&flag,4);} // broken/hidden current object
  if(state==2){float moved=1;std::memcpy(object[i]+8,&moved,4);} // moved placement
  if(state==3){float moved=1;std::memcpy(part[i],&moved,4);} // current skeletal pose changed
  if(state==4)s.source=true;
  if(state==5){gate::owned[field>>5]|=1U<<(field&31);gate::want[field>>5]|=1U<<(field&31);}
  if(state==6){area::cur=true;area::hidden=5;}
 }
}
