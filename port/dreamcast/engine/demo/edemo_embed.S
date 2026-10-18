/* edemo18 console disc: the data pack and the arm list linked into the program (no /cd access needed on a GD-ROM
 * image). Built only with EMBED_PAK / EMBED_ARMS set (private files, never in git). */
    .section .rodata
    .balign 32
    .global _edemo_pak_start
_edemo_pak_start:
    .incbin EMBED_PAK
    .global _edemo_pak_end
_edemo_pak_end:
    .balign 4
    .global _edemo_arms_start
_edemo_arms_start:
    .incbin EMBED_ARMS
    .global _edemo_arms_end
_edemo_arms_end:
    .byte 0
