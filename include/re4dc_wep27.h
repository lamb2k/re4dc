#ifndef RE4DC_WEP27_H
#define RE4DC_WEP27_H

// Build 27: include only in the default-off WEP_MODULES_27 composition.
// Admission is a pure lookup; it neither replaces the selected item nor loads
// a module. The real load still has its own guarded failure/retirement path.
extern "C" {
int re4dc_weapon27_module_id_present(unsigned id);
int re4dc_weapon27_module_file_present(const char* rel);
int re4dc_weapon27_available(unsigned no, unsigned type);
}
extern int re4dc_wep27_failed;
extern int re4dc_wep_reverted;
void re4dc_weapon27_revert(int oldNo, int oldType, int no, int type);

#endif
