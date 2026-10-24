Done: Isolated source-only tree created from qualified WIP140a699f; no runtime acceptance claimed.
Doing now: Complete immutable SourceGeometry and Weapon ancestry at accepted and replayed draws.
Next: Source-extracted positive, negative, mutation and lifetime controls; origin WIP checkpoint.
Blocked / Needs the user: none.

Branch: wip/gc-source-weapon24-20261024
Tree: /root/work/lanes/gc-source-weapon24
Base: 140a699f8ead7b406e76581de7075191acf77a96
Shared-file claims: port/dreamcast/game/model_bridge.cpp; platform/native_model.cpp; platform/native_actor_fast.cpp; platform/gc_asset_members.cpp; platform/gc_asset_payloads.cpp; platform/include/gc_asset_members.h; platform/include/gc_asset_payloads.h; platform/include/gc_asset_actor*.inc/.h; hand/static_source helpers only as needed.
Excluded: native_static.cpp, native_ui.cpp, audio_aica.cpp, gc_asset_gate.cpp/h, Motion-owned loaders/new Motion helper. No SDK, staging, guests, recipe/assets, shared tree or wired-mask edits.

First source checkpoint: gc_asset_actor_original.h parses the actual pre-relocation ModelData format with bounded member ownership. It validates all source GX indices, exact UV/color extents (nTex is not an array bound), original positions/normals, weight table width/count and shape delta table/vertex bounds. Selection compares captured source fields and exact complete source part, never a foreign array or interior stream alias. Color/weight/shape capability is separately refused when missing. This helper is not yet connected to positive draw acceptance; the existing raw serial0 guard remains intact until owner/FE/prepared derivation integration completes.

The actual production header passed standalone C++17 -Wall -Wextra -Werror with ASan+UBSan in RAM, including source mutation, foreign constituent, malformed stream, bounds, weight, color, shape and zero-serial negatives. No target compiler, build, programme, guest or provenance claim. Root granted model.cpp and tiny successful-output derivation hooks in trans.cpp; shape.cpp remains Motion-owned and interface-coordinated.
