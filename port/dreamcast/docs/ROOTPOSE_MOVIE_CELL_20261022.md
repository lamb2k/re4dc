# Root-pose movie-cell compatibility

The r100 s30 cliff movie cannot borrow its world arena with PS2_WORLD_ROOT_POSE enabled. Dynamic single-part bindings allocate the PartPose plus 24 floats (bind-root and inverse), while the movie preflight requests only the PartPose bytes. Room4 checks exact payload size, so a live valid cell is rejected before playback.

The allocation and validation now share part_cell_bytes(count). ROOT_POSE=1 adds the existing 96-byte tail only for count 1, including a refused/singular root witness. Multi-part and ROOT_POSE=0 sizes remain unchanged. No arena layout, package, world-cell capacity, retirement, recipe or gameplay behavior is changed.

The existing movie-arena host suite used simplified PartPose/Slot types and never ROOT_POSE=1. It now extracts production types and runs both modes under UBSan/guard pages. A realistic enabled fixture failed against the original validator before this fix. The fixed source passes 1,224 assertions with ROOT_POSE=0, 1,226 with it enabled, and 27 source integration contracts. Added cases cover 1/2/255 parts, exact short/long and stale-generation rejection, refused root witness allocation size, and complete Slot/part/matrix-tail preservation through borrow/return.

Host receipts are private at C:/Flycast-Evidence/re4-dreamcast/rootpose23-20261022. This is not linked-target or physical Dreamcast acceptance. Required next gates: matched console-mode r100 s30 340/340 and original r11c gear activation/animation/end state. Physical console validation is separate.

The coordinator owns integration as one unit; this patch does not alter its production recipe or protected allocator/texture/inventory/back-face work.
