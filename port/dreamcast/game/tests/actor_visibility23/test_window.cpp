#include "actor_visibility23_window.h"
#include <cassert>
#include <initializer_list>
using actor_visibility23::Window;
int main(){
 for(unsigned bits: {0U,0x20U,0x40U}) {
  Window w;assert(w.begin(0,false,bits)==Window::Idle);
  assert(w.begin(1,true,bits)==Window::Start);assert(w.mode==(bits>>5));
  assert(w.begin(1,true,bits)==Window::Idle);assert(w.frames==1&&w.left==599);
  for(unsigned f=2;f<=600;f++)assert(w.begin(f,true,bits)==Window::Continue);
  assert(w.frames==600&&w.left==0&&w.active);
  assert(w.begin(601,true,bits)==Window::Complete);assert(!w.active&&w.mode==0);
  assert(w.begin(602,false,bits)==Window::Idle);assert(w.begin(603,true,bits)==Window::Idle);
 }
 for(unsigned bits: {0x60U,1U,0x80U,0x100U,0x200U,0xffffffffU}){
  Window w;assert(w.begin(1,true,bits)==Window::Invalid);assert(!w.active);
  assert(w.begin(2,true,0x20)==Window::Idle);
 }
 for(bool change: {false,true}){
  Window w;assert(w.begin(1,true,0x40)==Window::Start);
  assert(w.begin(2,change,change?0x20:0x40)==Window::Cancel);
  assert(w.mode==0&&!w.active);assert(w.begin(3,true,0x40)==Window::Idle);
 }
 // Gaps/skipped Render entries do not consume budget; unsigned serial wrap is safe.
 Window w;assert(w.begin(0xffffffffU,true,0)==Window::Start);
 assert(w.begin(0,true,0)==Window::Continue);assert(w.frames==2);
}
