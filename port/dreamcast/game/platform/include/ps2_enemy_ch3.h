#ifndef RE4DC_PS2_ENEMY_CH3_H
#define RE4DC_PS2_ENEMY_CH3_H

/* Freshly read, little-endian enemy lists only. Never call on restored state.
 * 1: selected rows adopted; 0: list not owned; -1: invalid input;
 * -2: source differs from the qualified baseline. Failure leaves data intact.
 * The caller must reject a negative result rather than continue with GC rules.
 */
#ifdef __cplusplus
extern "C" {
#endif
int re4dc_ps2EnemyListCh3(int list_no, void *data, unsigned size);
#ifdef __cplusplus
}
#endif
#endif
