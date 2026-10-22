#!/usr/bin/env python3
"""Capture/check a future tool closure. No compile/link command is executed."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess

PROGRAMS = ('collect2', 'ld', 'lto-wrapper', 'lto1', 'cc1', 'cc1plus', 'as')
FLAGS = ('-m4-single', '-ml')
INFLUENCING = ('GCC_EXEC_PREFIX', 'COMPILER_PATH', 'LIBRARY_PATH', 'LD_LIBRARY_PATH', 'LD_PRELOAD')


def pin(path, role):
    path = Path(path).absolute()
    target = path.resolve(strict=True)
    stat = target.stat()
    return dict(path=str(path), resolved=str(target), role=role, bytes=stat.st_size,
                sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
                mode=stat.st_mode & 0o7777,
                symlink_target=os.readlink(path) if path.is_symlink() else None)


def same_pins(expected, current):
    """Compare aliases/targets, role, mode, extent and bytes; never normalize paths."""
    def index(rows):
        result = {}
        for row in rows:
            if row['path'] in result:
                raise ValueError('duplicate pin path')
            result[row['path']] = row
        return result
    return index(expected) == index(current)


def query(driver, option):
    argv = [str(driver), *FLAGS, option]
    result = subprocess.run(argv, capture_output=True, text=True, timeout=15, check=True)
    if result.stderr or len(result.stdout.splitlines()) != 1:
        raise ValueError('unexpected driver query output')
    return dict(argv=argv, stdout=result.stdout.strip())


def bindings(log):
    lines = log.splitlines()
    drivers = [line.split('=', 1)[1] for line in lines if line.startswith('COLLECT_GCC=')]
    wrappers = [line.split('=', 1)[1] for line in lines if line.startswith('COLLECT_LTO_WRAPPER=')]
    commands = [shlex.split(line) for line in lines if line.lstrip().startswith('/') and
                '/collect2 ' in line]
    if len(drivers) != 1 or len(wrappers) != 1 or len(commands) != 1:
        raise ValueError('ambiguous driver/collect2 binding')
    command = commands[0]
    at = [i for i, arg in enumerate(command) if arg == '-plugin']
    if len(at) != 1 or at[0] + 1 >= len(command):
        raise ValueError('ambiguous plugin binding')
    plugin = command[at[0] + 1]
    lto = [arg.split('=', 1)[1] for arg in command if arg.startswith('-plugin-opt=') and
           arg.endswith('/lto-wrapper')]
    if lto != wrappers:
        raise ValueError('LTO wrapper command disagrees with driver record')
    result = dict(driver=drivers[0], collect2=command[0], lto_wrapper=wrappers[0], plugin=plugin)
    if any(not Path(path).is_absolute() for path in result.values()):
        raise ValueError('nonabsolute actual driver binding')
    return result


def dynamic_dependencies(tool, ldd):
    """Read trusted installed host tool dependencies; never execute target binaries."""
    if Path(tool).read_bytes()[:4] != b'\x7fELF':
        return [], dict(path=str(tool), kind='script-not-ELF')
    result = subprocess.run([str(ldd), str(tool)], capture_output=True, text=True, timeout=15)
    text = result.stdout + result.stderr
    if 'not a dynamic executable' in text or 'statically linked' in text:
        return [], dict(path=str(tool), kind='static-ELF', output=text)
    if result.returncode or 'not found' in text:
        raise ValueError('unresolved host dependency: ' + str(tool))
    paths = []
    for line in text.splitlines():
        value = line.strip()
        if not value or value.startswith('linux-vdso.so.'):
            continue
        value = value.split('=>', 1)[1].strip() if '=>' in value else value
        target = value.split()[0]
        if not target.startswith('/') or not Path(target).is_file():
            raise ValueError('unrecognized loader dependency: ' + line)
        paths.append(target)
    return paths, dict(path=str(tool), kind='dynamic-ELF', output=text)


def mapped_host_elfs():
    """Loaded controller/Python extensions are shared code too; freeze after imports."""
    result = set()
    for line in Path('/proc/self/maps').read_text().splitlines():
        fields = line.split(maxsplit=5)
        if len(fields) != 6 or not fields[5].startswith('/'):
            continue
        if fields[5].endswith(' (deleted)'):
            raise ValueError('deleted loaded host code')
        path = Path(fields[5]).resolve(strict=True)
        if path.read_bytes()[:4] == b'\x7fELF':
            result.add(str(path))
    return result


def host_elf_path_allowed(snapshot, path):
    """For future successful host ELF opens; target objects use their own policy."""
    target = Path(path).resolve(strict=True)
    return any(str(target) == row['resolved'] and
               pin(row['path'], row['role']) == row for row in snapshot['pins'])


def capture(driver, driver_log, additional_tools=(), host_dependencies=True, ldd='/usr/bin/ldd'):
    if any(os.environ.get(name) for name in INFLUENCING):
        raise ValueError('unexpected tool-search/loader override environment')
    driver = Path(driver).absolute()
    first_driver = pin(driver, 'driver')
    actual = bindings(Path(driver_log).read_text())
    if Path(actual['driver']).resolve() != driver.resolve():
        raise ValueError('actual driver differs from queried driver')
    queries = [query(driver, '-print-prog-name=' + name) for name in PROGRAMS]
    selected = {}
    for name, result in zip(PROGRAMS, queries):
        path = Path(result['stdout'])
        if not path.is_absolute() or not path.is_file():
            raise ValueError('unresolved driver program: ' + name)
        selected[name] = str(path.absolute())
    for key, name in [('collect2', 'collect2'), ('lto_wrapper', 'lto-wrapper')]:
        if Path(actual[key]).resolve() != Path(selected[name]).resolve():
            raise ValueError('driver log/query tool disagreement: ' + name)
    plugin_query = query(driver, '-print-file-name=liblto_plugin.so')
    plugin_result = plugin_query['stdout']
    if Path(plugin_result).is_absolute():
        if Path(plugin_result).resolve() != Path(actual['plugin']).resolve():
            raise ValueError('plugin file query/log disagreement')
        plugin_resolution = 'absolute-file-query-and-actual-log'
    elif plugin_result == 'liblto_plugin.so':
        # GCC can print the unresolved basename despite selecting an absolute
        # libexec plugin in -###. Do not invent a search result or silently omit it.
        plugin_resolution = 'unresolved-file-query; selected-absolute-actual-driver-log'
    else:
        raise ValueError('unexpected unresolved plugin file query')
    pins = [first_driver]
    for name, path in selected.items():
        pins.append(pin(path, 'driver-program:' + name))
    pins.append(pin(actual['plugin'], 'actual-driver-shared-plugin'))
    for path in additional_tools:
        if str(Path(path).absolute()) not in {row['path'] for row in pins}:
            pins.append(pin(path, 'explicit-additional-tool'))
    host_reports = []
    if host_dependencies:
        if str(Path(ldd).absolute()) not in {row['path'] for row in pins}:
            pins.append(pin(ldd, 'host-dependency-inspector'))
        dependencies = set()
        for row in list(pins):
            values, report = dynamic_dependencies(row['resolved'], ldd)
            dependencies.update(values)
            host_reports.append(report)
        known = {row['path'] for row in pins}
        for path in sorted(dependencies - known):
            pins.append(pin(path, 'host-loader-or-shared-library'))
    controller_maps = sorted(mapped_host_elfs()) if host_dependencies else []
    if host_dependencies:
        known_resolved = {row['resolved'] for row in pins}
        for path in controller_maps:
            if path not in known_resolved:
                pins.append(pin(path, 'controller-loaded-host-ELF'))
    loader_absent = []
    if host_dependencies:
        configs = [Path('/etc/ld.so.cache'), Path('/etc/ld.so.conf'), Path('/etc/ld.so.preload')]
        configs += sorted(Path('/etc/ld.so.conf.d').glob('*.conf'))
        known = {row['path'] for row in pins}
        for path in configs:
            if path.exists() and str(path) not in known:
                pins.append(pin(path, 'host-loader-config'))
            elif not path.exists():
                loader_absent.append(str(path))
    if pin(driver, 'driver') != first_driver:
        raise ValueError('driver changed during capture')
    for row in pins:
        if pin(row['path'], row['role']) != row:
            raise ValueError('tool/library changed during capture')
    return dict(kind='CURRENT_SOURCE_PLAN_SNAPSHOT_NOT_A_BUILD_PREPOST_RECEIPT',
                driver=str(driver), flags=list(FLAGS), actual_driver_log=str(driver_log),
                actual_driver_log_sha256=hashlib.sha256(Path(driver_log).read_bytes()).hexdigest(),
                actual_bindings=actual, program_queries=queries, plugin_query=plugin_query,
                plugin_resolution=plugin_resolution, pins=pins, host_dependency_reports=host_reports,
                influencing_environment={name: os.environ.get(name) for name in INFLUENCING},
                loader_absence_invariants=loader_absent,
                controller_host_elf_maps=controller_maps,
                host_dependency_paths=sorted(dependencies) if host_dependencies else [],
                future_requirement='Capture BEFORE first compiler/tool invocation and again AFTER. '
                'Check exact resolved tool/host-library pins and actual driver queries/exec/plugin paths. '
                'This source-plan snapshot cannot retroactively qualify an earlier build.')


def check(snapshot):
    if {name: os.environ.get(name) for name in INFLUENCING} != snapshot['influencing_environment']:
        raise ValueError('tool-search/loader environment changed')
    if any(Path(path).exists() for path in snapshot.get('loader_absence_invariants', [])):
        raise ValueError('loader absence invariant changed')
    now = [pin(row['path'], row['role']) for row in snapshot['pins']]
    if not same_pins(snapshot['pins'], now):
        raise ValueError('tool closure changed')
    if snapshot.get('controller_host_elf_maps'):
        if not mapped_host_elfs() <= {row['resolved'] for row in snapshot['pins']}:
            raise ValueError('unplanned controller/shared-code mapping')
    if snapshot.get('host_dependency_reports'):
        observed = set()
        for report in snapshot['host_dependency_reports']:
            paths, _ = dynamic_dependencies(report['path'], '/usr/bin/ldd')
            observed.update(paths)
        if observed != set(snapshot['host_dependency_paths']):
            raise ValueError('host loader selection changed')
    for prior in snapshot['program_queries'] + [snapshot['plugin_query']]:
        if query(snapshot['driver'], prior['argv'][-1]) != prior:
            raise ValueError('tool selection changed')
    return True


def exec_path_allowed(snapshot, actual_path):
    """Future execution-trace gate: unknown executed tools never enter implicitly."""
    path = Path(actual_path)
    if not path.is_absolute() or not path.exists():
        return False
    selected = str(path.resolve())
    return any(selected == row['resolved'] and row['role'] not in
               ('host-loader-or-shared-library', 'host-loader-config', 'controller-loaded-host-ELF') and row['mode'] & 0o111
               for row in snapshot['pins'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    ap = sub.add_parser('capture')
    ap.add_argument('--driver', required=True)
    ap.add_argument('--driver-log', required=True)
    ap.add_argument('--tool', action='append', default=[])
    ap.add_argument('--output', required=True)
    ap = sub.add_parser('check')
    ap.add_argument('snapshot')
    args = parser.parse_args()
    if args.command == 'capture':
        result = capture(args.driver, args.driver_log, args.tool)
        with Path(args.output).open('x') as out:
            json.dump(result, out, indent=2)
            out.write('\n')
        print(json.dumps(dict(status='SOURCE_SNAPSHOT_ONLY', pins=len(result['pins']),
                              plugin_resolution=result['plugin_resolution'])))
    else:
        check(json.loads(Path(args.snapshot).read_text()))
        print('PASS_TOOL_CLOSURE_STILL_EXACT; not a retroactive build qualification')


if __name__ == '__main__':
    main()