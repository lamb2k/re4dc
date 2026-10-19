/* actor_rt_grid.S: the r101 EDGR grid for the engine preview (ENGINE_PREVIEW=1; ENGINE_PREVIEW_GRID = private file). */
    .section .rodata
    .balign 32
    .global _re4dc_rt_grid101
_re4dc_rt_grid101:
    .incbin RE4DC_RT_GRID_FILE
_re4dc_rt_grid101_end:
    .balign 4
    .global _re4dc_rt_grid101_size
_re4dc_rt_grid101_size:
    .long _re4dc_rt_grid101_end - _re4dc_rt_grid101
