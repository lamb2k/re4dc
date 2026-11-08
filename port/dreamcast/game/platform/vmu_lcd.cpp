// Shared LCD owner. All calls run on the game thread; KOS copies the queued packet.
#include <kos.h>
#include <dc/maple.h>
#include <dc/maple/controller.h>
#include <dc/maple/vmu.h>
#include <string.h>
#include "../vmu_context.h"
#include "../vmu_lcd_queue.h"

#ifndef RE4DC_VMU_MOTION
#define RE4DC_VMU_MOTION 1
#endif
extern "C" {
// Stable inspection symbols for host/emulator evidence; logical top-left MSB frame.
alignas(4) unsigned char re4dc_vmu_lcd_frame[192];
volatile unsigned re4dc_vmu_lcd_attempts, re4dc_vmu_lcd_sent, re4dc_vmu_lcd_errors;
}
namespace {
re4vmu::Snapshot snapshot;
re4vmu::Animation animation;
re4vmu::LcdQueue queue;
// The pages stay in their owners' persistent buffers (pace.cpp v_lcd, dbgslot_bridge.cpp lcd): no copies here.
const uint8_t *speed, *debug;
bool speed_enabled, debug_enabled;
unsigned debug_start, last_render;
bool rendered;
uintptr_t animation_device;
unsigned now_ms(){return (unsigned)timer_ms_gettime64();}
}
extern "C" void re4dc_vmu_publish(const re4vmu::Snapshot* s){snapshot=*s;}
extern "C" void re4dc_vmu_speed(const void* frame,int enabled){
    if(frame)speed=(const uint8_t*)frame;
    speed_enabled=enabled!=0&&speed;
}
extern "C" void re4dc_vmu_debug(const void* frame){
    if(!frame){debug_enabled=false;return;}
    debug=(const uint8_t*)frame;debug_start=now_ms();debug_enabled=true;
}
#if defined(RE4DC_VMU_SAFE_IO) && RE4DC_VMU_SAFE_IO
extern "C" int re4dc_card_busy(void);  // card.cpp: no LCD packets between the blocks of a card op
#endif
extern "C" void re4dc_vmu_poll(){
#if defined(RE4DC_VMU_SAFE_IO) && RE4DC_VMU_SAFE_IO
    if(re4dc_card_busy())return;
#endif
    unsigned now=now_ms();
    // Even composition is limited to 10 Hz, including busy/no-device cases.
    if(rendered&&now-last_render<100)return;
    rendered=true;last_render=now;
    // PADRead maps Joy[0] to controller enumeration 0, whose physical port may
    // be B/C/D. Never assume its ordinal is a physical Maple port.
    maple_device_t* controller=maple_enum_type(0,MAPLE_FUNC_CONTROLLER);
    maple_device_t* lcd=nullptr;
    if(controller)for(int unit=1;unit<=5;++unit){
        maple_device_t* d=maple_enum_dev(controller->port,unit);
        if(d&&(d->info.functions&MAPLE_FUNC_LCD)){lcd=d;break;}
    }
    // A newly attached LCD receives committed state, never a partial old animation.
    uintptr_t current_device=(uintptr_t)lcd;
    if(current_device!=animation_device){animation.initialized=false;animation_device=current_device;}
    re4vmu::View view=re4vmu::resolve(snapshot);
    re4vmu::Phase phase=animation.update(view,snapshot.generation,now,!RE4DC_VMU_MOTION);
    if(debug_enabled&&now-debug_start>=3000)debug_enabled=false;
    if(debug_enabled)memcpy(re4dc_vmu_lcd_frame,debug,192);
    else if(speed_enabled)memcpy(re4dc_vmu_lcd_frame,speed,192);
    else re4vmu::render(view,phase,re4dc_vmu_lcd_frame);
    // No retained device pointer survives a rescan/removal. Lower slot wins.
    if(!lcd){queue.disconnected();return;}
    uintptr_t identity=(uintptr_t)lcd;
    if(!queue.ready(now,identity,re4dc_vmu_lcd_frame))return;
    int rc=controller->info.connector_direction!=lcd->info.connector_direction?
        vmu_draw_lcd(lcd,re4dc_vmu_lcd_frame):vmu_draw_lcd_rotated(lcd,re4dc_vmu_lcd_frame);
    ++re4dc_vmu_lcd_attempts;
    if(rc==MAPLE_EOK)++re4dc_vmu_lcd_sent;else ++re4dc_vmu_lcd_errors;
    queue.result(now,rc,re4dc_vmu_lcd_frame);
}
