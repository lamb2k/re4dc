#!/usr/bin/env python3
"""Make-derived public Test22 profiles for the Build 3 selection controls."""
import importlib.util
from pathlib import Path
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
ROOT = DC.parents[1]
_spec = importlib.util.spec_from_file_location(
    "select2_public_profile", HERE.parent / "world_submit_spike/build_profile.py")
helpers = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(helpers)
Build, sections, sha, stack_usage = helpers.Build, helpers.sections, helpers.sha, helpers.stack_usage


def expand_existing(output, compiler, sdk, receipt, overrides=(), *, actor=False,
                    cost_dependencies=False, prefix="select2"):
    """Expand actual recipes using one generated-header directory.

    The original helper asserts that every reconstructed generated header is
    unchanged. Only recipe-local flags may differ between the tested knobs.
    """
    source = dict(receipt["native_static"])
    source["command"] = [*source["command"], *overrides]
    specifications = [("native_static", "platform/native_static.o", "platform/native_static.cpp"),
                      ("native_ui", "platform/native_ui.o", "platform/native_ui.cpp")]
    if actor:
        specifications.append(("native_actor_fast", "platform/native_actor_fast.o", "platform/native_actor_fast.cpp"))
    if cost_dependencies:
        specifications += [("texture_package", "native-reuse/texture_package.o", "../room/texture_package.cpp"),
                           ("pvr_geometry", "native-reuse/pvr_geometry.o", "../room/pvr_geometry.cpp")]
    flags, profiles = {}, {}
    for name, target, path in specifications:
        flags[name], profiles[name] = helpers.expand(output, compiler, sdk, output / "kos-overlay",
            source, prefix + "-" + name, target, path)
    return flags, profiles


def derive(output, compiler, kos, sdk, *, overrides=(), actor=False, cost_dependencies=False):
    flags, receipt = helpers.derive(output, compiler, kos, sdk, cost_dependencies=cost_dependencies)
    if overrides or actor:
        flags, profiles = expand_existing(output, compiler, sdk, receipt, overrides,
            actor=actor, cost_dependencies=cost_dependencies)
        receipt = dict(receipt, **profiles)
    return flags, receipt
