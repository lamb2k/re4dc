#pragma once
// One bounded window per fixture invocation/programme. A continuous late
// condition, room reentry or changed request never rearms a spent window.
namespace actor_visibility23 {
struct Window {
 enum Event {Idle,Start,Continue,Complete,Cancel,Invalid};
 bool spent=false,active=false,seen=false;unsigned mode=0,left=0,frames=0,last=0,bits=0;
 Event begin(unsigned render,bool open,unsigned request) {
  if(seen&&render==last)return Idle;
  seen=true;last=render;
  if(active&&(!open||request!=bits)){active=false;mode=0;return Cancel;}
  if(active&&!left){active=false;mode=0;return Complete;}
  Event event=Continue;
  if(!active){
   if(spent||!open)return Idle;
   spent=true;bits=request;
   if(request&~0x60U || (request&0x60U)==0x60U)return Invalid;
   mode=(request&0x40U)?2U:(request&0x20U)?1U:0U;
   active=true;left=600;frames=0;event=Start;
  }
  --left;++frames;return event;
 }
};
}
