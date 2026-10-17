#pragma once
// Default-off, r200 event-image presentation only. All ownership is a bounded
// read of the existing accepted OTs, scroll work table and loaded native owner.
class cModel;
// Scalar snapshot only: diagnostics never read a rejected allocation.
struct Re4dcSourceWorldOtMemory { unsigned long begin,end;unsigned epoch,live; };
struct Re4dcSourceWorldTexture { unsigned generation,crc,fnv,width,height,bytes; };
// Exact ExecOt invocation. Borrowed values only: these hooks never read a node
// or a payload. A nested ModelRender cannot inherit its caller's one-shot role.
struct Re4dcSourceWorldCallback {
    unsigned table,kind,callback_depth,model_depth;
    const void* node;
    void (*func)(void*);
    void* data;
};
extern "C" {
void re4dc_source_world_callback_begin(unsigned table,const void* node,
    void (*func)(void*),void* data,unsigned kind);
void re4dc_source_world_callback_end();
int re4dc_source_world_callback_current(Re4dcSourceWorldCallback*);
void re4dc_source_world_model_enter();
void re4dc_source_world_model_leave();
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
int re4dc_source_world_native_cell(const void*,unsigned bytes,unsigned generation);
int re4dc_ps2_source_group_package(unsigned* generation,int deep);
int re4dc_r200_scroll_group();
int re4dc_r200_scroll_storage_current();
int re4dc_r200_scroll_probe(cModel*,unsigned* serial,unsigned* work);
int re4dc_r200_scroll_member(cModel*,unsigned serial,unsigned work,float* uv);
int re4dc_r200_scroll_member_light(cModel*,unsigned serial,unsigned work,float* uv);
int re4dc_r200_scroll_storage_current_light();
void re4dc_r200_set_light(int on);
int re4dc_r200_scroll_pointers(cModel**,unsigned count);
int re4dc_source_world_preflight_current(unsigned native,unsigned generation);
int re4dc_source_world_binding_valid();
void re4dc_source_world_binding_failed();
int re4dc_source_world_group_claimed();
int re4dc_source_world_sealed();
int re4dc_r200_part_delta(unsigned work,float* out); // source_world_scroll.inc (TRANSITION_OWNER)
int re4dc_source_world_op_window();
int re4dc_source_world_uv(unsigned placement,unsigned mesh,unsigned part,unsigned pass,float* uv);
int re4dc_scroll_source_transition_member(cModel*,unsigned serial,unsigned* work,unsigned* reason);
unsigned re4dc_scroll_source_member_field();
int re4dc_source_world_transition_owner(unsigned native,unsigned generation);
int re4dc_source_world_legacy_allowed(unsigned native);
int re4dc_source_world_callback_continue();
int re4dc_source_world_present(unsigned native,int source_finished,int stream_aborted);
void re4dc_ps2_source_pass_begin(unsigned pass);
void re4dc_ps2_source_pass_result(unsigned pass,int result);
int re4dc_ps2_source_receipt_complete(unsigned native,unsigned generation);
int re4dc_ps2_source_legacy_clean(unsigned native);
void re4dc_ps2_source_legacy_started(unsigned native);
#endif
int re4dc_r11f_scroll_pointers(cModel**,unsigned count);
int re4dc_r11f_package(unsigned* generation,int deep);
int re4dc_r11f_native_plan(unsigned native,unsigned generation);
int re4dc_r11f_native_draw(unsigned generation,unsigned source,const float* uv);
int re4dc_r11f_native_complete(unsigned native,unsigned generation,unsigned source);
void re4dc_r11f_native_cancel(int failed);
void re4dc_r11f_native_frame(unsigned native);
int re4dc_r11f_op_window();
unsigned re4dc_r11f_packet_bytes();
void re4dc_r11f_prepare(unsigned native);
int re4dc_r11f_current(unsigned native,unsigned generation,int deep);
int re4dc_r11f_check_current(unsigned native,unsigned generation,int deep);
int re4dc_r11f_binding_valid();
void re4dc_r11f_binding_failed();
int re4dc_r11f_barrier(unsigned native);
void re4dc_r11f_source_finished(unsigned native,int finished,int aborted);
int re4dc_r11f_present(unsigned native,int finished,int aborted);
int re4dc_r11f_legacy_blocked(unsigned native);
int re4dc_r11f_callback_continue();
void re4dc_r11f_pass_failed(unsigned native);
int re4dc_r11f_scroll_group();
int re4dc_r11f_scroll_member(cModel*,unsigned serial,unsigned work,float* uv);
int re4dc_r11f_scroll_probe(cModel*,unsigned* serial,unsigned* work);
int re4dc_r11f_scroll_pointer(const cModel*);
unsigned re4dc_source_world_ot_epoch();
void re4dc_source_world_ot_memory(Re4dcSourceWorldOtMemory*);
int re4dc_source_world_ot_retained(const void*,unsigned bytes);
int re4dc_ps2_source_package(unsigned* generation);
int re4dc_ps2_source_texture(unsigned generation,Re4dcSourceWorldTexture* out);
int re4dc_ps2_source_draw(unsigned generation);
int re4dc_ps2_source_passes_complete();
void re4dc_source_world_flush_result(unsigned native_frame,int complete);
int re4dc_scroll_source_member(cModel*,unsigned serial,unsigned* work);
// Exact currently published source pool slots, before any candidate field read.
int re4dc_source_world_pool(const void*,unsigned type);
int re4dc_scroll_source_probe(cModel*,unsigned* serial,unsigned* work);
int re4dc_source_world_prepare(unsigned native_frame,unsigned* generation);
int re4dc_source_world_current(unsigned native_frame,unsigned generation);
#if RE4DC_PS2_WORLD_TRANSITION_PIN
// Texture cache retention only; never authorizes source geometry consumption.
int re4dc_source_world_transition(unsigned native_frame,unsigned generation);
#endif
void re4dc_source_world_prepared(unsigned native_frame,unsigned generation,int ready);
}
