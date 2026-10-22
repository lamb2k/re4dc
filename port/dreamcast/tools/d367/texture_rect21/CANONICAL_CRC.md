# Canonical mipmap package checksum repair

The native Package reader checks the CRC of all bytes after the 48-byte header,
including texture descriptors. Several offline emitters preserved an older
texel-only CRC convention. Resident streaming with CRC checking disabled masked
the strict reader's rejection. A prior `payload CRC mismatch|ok` result means
strict failure and streamed success; it never establishes both paths passed.

Enabled conversion now emits the runtime's descriptor-and-payload CRC. Legacy
inputs remain readable; disabled mip conversion remains byte-identical. Enabled
already-mipmapped inputs also normalize this header field. The field is Header
element 8, offset 36; data_size at offset 32 is preserved. Runtime validation and
production defaults/recipes are unchanged.

Selected canonical inputs consist of base948, actor20 and world36: 1,004 mip
packages. The base needs 150 header-only patches; actors need none; world36
needs 21 patches and consequently 21 new immutable scoped identities. Pixel,
palette, codebook, descriptor, mip and UV bytes remain unchanged. Three key-only
worlds receive genuine physical CRC/FNV certificates with original metadata
lineage. Old candidates, programme 4ef617a1/ELF f42dbb72 and their evidence remain
preserved on strict-package hold.

The emitter regression uses synthetic fixtures and the actual unchanged Package
implementation with ASan/UBSan and streamed CRC enabled: 100 source checks,
48 strict cases and 48 streamed cases pass, including descriptor/payload
corruption rejection. Separate selected-asset qualification covers all 1,004
canonical packages; the integrated world table passes 573 helper checks.

This is source/host evidence. A new programme, combined pack, images and fresh
target qualification are still required. No performance, release or physical
Dreamcast acceptance is implied.
