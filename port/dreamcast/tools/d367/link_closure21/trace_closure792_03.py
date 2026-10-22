#!/usr/bin/env python3
"""Fail-closed strace execve/openat parser for a separately approved tool contract."""
import ast
from pathlib import Path
import re
import tool_closure as tools

NONCES = {'gcc_resolution': r'cc[A-Za-z0-9]{6}\.res',
          'gcc_cdtor_c': r'cc[A-Za-z0-9]{6}\.cdtor\.c',
          'gcc_cdtor_o': r'cc[A-Za-z0-9]{6}\.cdtor\.o',
          'python_named_temp': r'tmp[a-z0-9_]{8}',
          'python_temp_probe': r'[a-z0-9_]{8}'}
ENV_KEYS = tools.INFLUENCING


def split_top(text):
    parts, first, depth, quote, escape = [], 0, 0, False, False
    for i, char in enumerate(text):
        if quote:
            if escape:
                escape = False
            elif char == '\\':
                escape = True
            elif char == '"':
                quote = False
        elif char == '"':
            quote = True
        elif char in '[({<':
            depth += 1
        elif char in '])}>':
            depth -= 1
            if depth < 0:
                raise ValueError('unbalanced trace arguments')
        elif char == ',' and depth == 0:
            parts.append(text[first:i].strip())
            first = i + 1
    if quote or depth:
        raise ValueError('incomplete trace arguments')
    return parts + [text[first:].strip()]


def cstring(value):
    if not value.startswith('"') or not value.endswith('"'):
        raise ValueError('truncated/nonliteral C string')
    result = ast.literal_eval('b' + value).decode('utf-8', 'surrogateescape')
    if '\0' in result:
        raise ValueError('NUL in trace string')
    return result


def strings(value):
    if not value.startswith('[') or not value.endswith(']'):
        raise ValueError('abbreviated argv/environment; require strace -v -s262144')
    middle = value[1:-1].strip()
    return [] if not middle else [cstring(part) for part in split_top(middle)]


def parse(text):
    pending, events = {}, []
    for line in text.splitlines():
        match = re.fullmatch(r'(?:\[pid\s+(\d+)\]\s+|(\d+)\s+)(.*)', line)
        if not match:
            raise ValueError('missing PID or unknown trace line: ' + line[:100])
        pid, rest = int(match.group(1) or match.group(2)), match.group(3)
        if rest.startswith('--- SIG') and rest.endswith(' ---'):
            continue
        if rest.startswith('+++ exited with '):
            if rest != '+++ exited with 0 +++':
                raise ValueError('nonzero traced child exit')
            continue
        if rest.startswith('<... '):
            resumed = re.fullmatch(r'<\.\.\. (execve|openat|unlink) resumed>(.*)', rest)
            if not resumed or pid not in pending or pending[pid][0] != resumed.group(1):
                raise ValueError('unmatched resumed syscall')
            rest = pending.pop(pid)[1] + resumed.group(2)
        elif rest.endswith(' <unfinished ...>'):
            kind = rest.split('(', 1)[0]
            if kind not in ('execve', 'openat', 'unlink') or pid in pending:
                raise ValueError('ambiguous unfinished syscall')
            pending[pid] = (kind, rest[:-len(' <unfinished ...>')])
            continue
        call = re.fullmatch(r'(execve|openat|unlink)\((.*)\)\s+=\s+(-?\d+)(.*)', rest)
        if not call:
            raise ValueError('unknown/error/truncated syscall: ' + rest[:100])
        kind, arguments, result = call.group(1), split_top(call.group(2)), int(call.group(3))
        event = dict(PID=pid, kind=kind, result=result, success=result >= 0)
        if kind == 'execve':
            if len(arguments) != 3:
                raise ValueError('bad execve arity')
            event.update(path=cstring(arguments[0]), argv=strings(arguments[1]),
                         environment=strings(arguments[2]))
        elif kind == 'unlink':
            if len(arguments) != 1:
                raise ValueError('bad unlink arity')
            path = cstring(arguments[0])
            event.update(path=path, resolved=str(Path(path).resolve()))
        else:
            if len(arguments) not in (3, 4):
                raise ValueError('bad openat arity')
            event.update(path=cstring(arguments[1]), flags=arguments[2], dirfd=arguments[0])
            if event['success']:
                target = re.fullmatch(r'<(/.*)>', call.group(4).strip())
                if not target or target.group(1).endswith(' (deleted)'):
                    raise ValueError('successful open lacks stable -yy absolute target')
                event['resolved'] = str(Path(target.group(1)).resolve())
        events.append(event)
    if pending or not events:
        raise ValueError('incomplete/empty trace')
    return events


def argv_matches(rule, actual, owned_temp, nonce_state=None):
    expected = rule['argv']
    if len(expected) != len(actual):
        return False
    slots = {row['index']: row for row in rule.get('nonce_slots', [])}
    if len(slots) != len(rule.get('nonce_slots', [])):
        raise ValueError('duplicate nonce index')
    if any(type(index) is not int or index < 0 or index >= len(expected) for index in slots):
        raise ValueError('nonce index outside argv')
    forward, reverse = ({}, {}) if nonce_state is None else (dict(nonce_state[0]), dict(nonce_state[1]))
    for index, (old, new) in enumerate(zip(expected, actual)):
        if index not in slots:
            if old != new:
                return False
            continue
        row = slots[index]
        profile = row['profile']
        if profile not in NONCES:
            raise ValueError('unapproved nonce profile')
        prefix = str(Path(owned_temp)) + '/'
        if profile == 'gcc_resolution':
            prefix = '-plugin-opt=-fresolution=' + prefix
        if not old.startswith(prefix) or not new.startswith(prefix):
            return False
        if not re.fullmatch(NONCES[profile], old[len(prefix):]) or not re.fullmatch(NONCES[profile], new[len(prefix):]):
            return False
        if old in forward and forward[old] != new or new in reverse and reverse[new] != old:
            return False
        forward[old], reverse[new] = new, old
    if nonce_state is not None:
        nonce_state[0].clear(); nonce_state[0].update(forward)
        nonce_state[1].clear(); nonce_state[1].update(reverse)
    return True


def validate(text, contract):
    if contract.get('root_returncode') != 0:
        raise ValueError('root child did not exit successfully')
    events = parse(text)
    inputs = {}
    for row in contract['inputs']:
        current = tools.pin(row['pin']['path'], row['pin']['role'])
        if current != row['pin']:
            raise ValueError('changed prepinned input/tool/plugin')
        resolved = row['pin']['resolved']
        if resolved in inputs:
            raise ValueError('duplicate resolved input policy')
        inputs[resolved] = row
    mutable = {}
    for row in contract.get('mutable_data', []):
        resolved = row['post_pin']['resolved']
        if resolved in inputs or resolved in mutable or row['pre_pin']['path'] != row['post_pin']['path'] or row['pre_pin']['bytes'] != row['post_pin']['bytes'] or not row.get('prechecked_and_reviewed_span_verified'):
            raise ValueError('invalid mutable generated-data contract')
        if tools.pin(row['post_pin']['path'], row['post_pin']['role']) != row['post_pin']:
            raise ValueError('mutable generated-data posthash changed')
        if not set(row['readers'] + row['writers']) <= set(inputs):
            raise ValueError('unknown mutable data reader/writer')
        mutable[resolved] = dict(policy=row, reads=0, writes=0)
    rules = contract['executions']
    if not rules or any(type(row.get('count', 1)) is not int or row.get('count', 1) <= 0 for row in rules):
        raise ValueError('invalid execution count contract')
    seen_exec, seen_read, writes = set(), set(), set()
    successful_exec = 0
    execution_counts = {}
    nonce_state = ({}, {})
    pid_executables, transient = {}, {}
    transient_rules = contract.get('transient_data', [])
    if any(row['root'] != contract['owned_temp'] or row['profile'] not in NONCES or any(type(row[key]) is not int or row[key] < (1 if key == 'count' else 0) for key in ('count', 'writes', 'reads')) or not set(row['creators'] + row['writers'] + row['readers'] + row['unlinkers']) <= set(inputs) for row in transient_rules):
        raise ValueError('invalid transient data contract')
    for event in events:
        if not event['success']:
            continue  # Failed probes admit no executed code or bytes; root success/coverage still required.
        if event['kind'] == 'execve':
            path = event['path']
            if not Path(path).is_absolute():
                raise ValueError('relative executable')
            resolved = str(Path(path).resolve(strict=True))
            matches = []
            for index, rule in enumerate(rules):
                candidate_nonce = (dict(nonce_state[0]), dict(nonce_state[1]))
                if path == rule['path'] and resolved == rule['resolved'] and argv_matches(rule, event['argv'], contract['owned_temp'], candidate_nonce):
                    env = {}
                    for item in event['environment']:
                        if '=' not in item:
                            raise ValueError('malformed execution environment')
                        key, value = item.split('=', 1)
                        if key in env:
                            raise ValueError('duplicate environment key')
                        env[key] = value
                    required = rule['environment']
                    if not set(ENV_KEYS) <= set(required):
                        raise ValueError('missing critical environment policy')
                    if set(env) == {key for key, value in required.items() if value is not None} and all(env.get(key) == value for key, value in required.items()):
                        matches.append((index, candidate_nonce))
            if len(matches) != 1 or resolved not in inputs:
                raise ValueError('unknown executable/argv/order/alias/environment')
            matched, nonce_state = matches[0]
            seen_exec.add(matched)
            execution_counts[matched] = execution_counts.get(matched, 0) + 1
            successful_exec += 1
            pid_executables[event['PID']] = resolved
            continue
        resolved, requested = event['resolved'], event['path']
        executable = pid_executables.get(event['PID'])
        if event['kind'] == 'unlink':
            state = transient.get(resolved)
            if not state or state['unlinked'] or requested != resolved or executable not in transient_rules[state['rule']]['unlinkers'] or (transient_rules[state['rule']].get('same_creator_pid',False) and event['PID'] != state['creator_PID']):
                raise ValueError('unknown/repeated/unapproved transient unlink')
            state['unlinked'] = True
            continue
        flags = event['flags']
        if resolved in mutable:
            state = mutable[resolved]; row = state['policy']
            if requested not in row['aliases']:
                raise ValueError('mutable data alias changed')
            if flags in row['write_flags'] and executable in row['writers'] and state['reads'] == row['reads']:
                state['writes'] += 1
            elif flags in row['read_flags'] and executable in row['readers'] and not state['writes']:
                state['reads'] += 1
            else:
                raise ValueError('mutable data order/reader/writer/flags')
            continue
        temporary_match = [index for index, row in enumerate(transient_rules)
            if str(Path(resolved).parent) == row['root'] and re.fullmatch(NONCES[row['profile']], Path(resolved).name)]
        if temporary_match:
            if len(temporary_match) != 1 or requested != resolved or resolved in inputs:
                raise ValueError('ambiguous/aliased/pinned transient data')
            index = temporary_match[0]; row = transient_rules[index]
            state = transient.get(resolved)
            if state is None:
                if flags not in row['create_flags'] or 'O_EXCL' not in flags.split('|') or executable not in row['creators']:
                    raise ValueError('transient read/write before exclusive creation')
                transient[resolved] = dict(rule=index, writes=0, reads=0, unlinked=False, creator_PID=event['PID'])
            elif state['unlinked']:
                raise ValueError('transient accessed after unlink')
            elif flags in row['write_flags'] and executable in row['writers']:
                state['writes'] += 1
            elif flags in row['read_flags'] and executable in row['readers'] and state['writes'] in row.get('allowed_writes', [row['writes']]):
                state['reads'] += 1
            else:
                raise ValueError('unapproved transient data flags/reader/writer/order')
            continue

        writing = any(flag in flags.split('|') for flag in ('O_WRONLY', 'O_RDWR', 'O_CREAT', 'O_TRUNC', 'O_APPEND'))
        if writing:
            permitted = any(resolved == row['path'] and requested == row.get('alias', row['path']) and flags in row['flags'] for row in contract.get('writes', []))
            for row in contract.get('temporary_writes', []):
                parent, base = str(Path(resolved).parent), Path(resolved).name
                if requested == resolved and parent == row['root'] == contract['owned_temp'] and row['profile'] in NONCES and re.fullmatch(NONCES[row['profile']], base) and flags in row['flags']:
                    permitted = True
            if not permitted:
                raise ValueError('write outside exact approved outputs/private temp policy')
            writes.add(resolved)
            continue
        if resolved in inputs:
            row = inputs[resolved]
            if requested not in row['aliases'] or flags not in row['read_flags']:
                raise ValueError('input/plugin alias or read flags changed')
            # Recheck file while interpreting the successful read, not only path membership.
            if tools.pin(row['pin']['path'], row['pin']['role']) != row['pin']:
                raise ValueError('input/tool changed during validation')
            seen_read.add(resolved)
        elif resolved in contract.get('read_directories', []) and Path(resolved).is_dir() and 'O_DIRECTORY' in flags.split('|'):
            continue
        elif resolved in contract.get('special_reads', {}) and flags in contract['special_reads'][resolved]:
            continue
        else:
            raise ValueError('unknown successful input/plugin/code open')
    if any(state['reads'] != state['policy']['reads'] or state['writes'] != state['policy']['writes'] for state in mutable.values()):
        raise ValueError('mutable generated-data read/write count differs')
    for index, row in enumerate(transient_rules):
        states = [(path, state) for path, state in transient.items() if state['rule'] == index]
        if len(states) != row['count'] or any(not state['unlinked'] or state['writes'] not in row.get('allowed_writes', [row['writes']]) or state['reads'] != row['reads'] or Path(path).exists() or Path(path).is_symlink() for path, state in states):
            raise ValueError('incomplete transient data lifecycle/count/postabsence')
    if any(execution_counts.get(index, 0) != rule.get('count', 1) for index, rule in enumerate(rules)):
        raise ValueError('subprocess execution count differs')
    if not successful_exec or not set(contract['required_executions']) <= seen_exec or not set(contract['required_reads']) <= seen_read:
        raise ValueError('required executable/plugin coverage missing')
    return dict(status='PASS_EXACT_PREPINNED_TRACE', events=len(events),
                successful_executions=successful_exec, seen_execution_rules=sorted(seen_exec),
                distinct_prepinned_reads=len(seen_read), approved_writes=sorted(writes), transient_data_files=len(transient), mutable_data_files=len(mutable))