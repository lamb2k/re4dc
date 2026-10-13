# Offline Dreamcast world assets. See port/dreamcast/docs/PS2_ASSET_BUILD.md.
PYTHON ?= python3
ASSETS_OUT ?= .assets/worlds
ASSET_TOOLS ?= .assets/tools
ROOMS ?= r102 r106
export PS2_ISO GC_ISO ASSETS_OUT ASSET_TOOLS ROOMS
.PHONY: assets assets-check
assets:
	$(PYTHON) port/dreamcast/tools/build_ps2_assets.py

assets-check:
	$(PYTHON) -m unittest discover -s port/dreamcast/tools/ps2_assets -p 'test_*.py'
