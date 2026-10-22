#!/usr/bin/env python3
"""Host-only parser controls; never invoke a compiler/linker or game programme."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
import trace_closure as trace
import tool_closure as tools

class TraceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = self.root / 'plugin.so'
        self.data.write_bytes(b'pinned-fixture-only')
        self.exe = '/usr/bin/python3'
        self.argv = [self.exe, '-I', '-S', '-B']
        self.lines = [f'101 execve({json.dumps(self.exe)}, {json.dumps(self.argv)}, []) = 0',
                      f'101 openat(AT_FDCWD, {json.dumps(str(self.data))}, O_RDONLY|O_CLOEXEC) = 3<{self.data}>']
        self.contract = dict(root_returncode=0, owned_temp=str(self.root),
            inputs=[dict(pin=tools.pin(self.exe,'fixture-exe'),aliases=[self.exe],read_flags=[]),
                    dict(pin=tools.pin(self.data,'fixture-plugin'),aliases=[str(self.data)],read_flags=['O_RDONLY|O_CLOEXEC'])],
            executions=[dict(path=self.exe,resolved=str(Path(self.exe).resolve()),argv=self.argv,
                environment={key:None for key in tools.INFLUENCING})], required_executions=[0],
            required_reads=[str(self.data)],writes=[],temporary_writes=[],read_directories=[],special_reads={})
    def run_trace(self, lines=None, contract=None):
        return trace.validate('\n'.join(self.lines if lines is None else lines), self.contract if contract is None else contract)
    def reject(self, lines=None, contract=None):
        with self.assertRaises((ValueError,OSError)):
            self.run_trace(lines,contract)
    def test_exact(self): self.assertEqual(self.run_trace()['successful_executions'],1)
    def test_unknown_exec(self): self.reject([self.lines[0].replace('/usr/bin/python3','/usr/bin/true'),self.lines[1]])
    def test_exec_alias(self): self.reject([self.lines[0].replace('/usr/bin/python3','/usr/bin/./python3'),self.lines[1]])
    def test_changed_flag(self): self.reject([self.lines[0].replace('"-I"','"-E"'),self.lines[1]])
    def test_changed_order(self): self.reject([self.lines[0].replace('"-I", "-S"','"-S", "-I"'),self.lines[1]])
    def test_unknown_plugin(self): self.reject([self.lines[0],self.lines[1].replace(str(self.data),'/etc/hosts')])
    def test_plugin_path_alias(self): self.reject([self.lines[0],self.lines[1].replace(json.dumps(str(self.data)),json.dumps(str(self.root)+'/./plugin.so'))])
    def test_plugin_flags(self): self.reject([self.lines[0],self.lines[1].replace('O_RDONLY|O_CLOEXEC','O_RDONLY')])
    def test_changed_pinned_bytes(self): self.data.write_bytes(b'changed');self.reject()
    def test_changed_pinned_mode(self): self.data.chmod(0o700);self.reject()
    def test_missing_plugin(self): self.reject(self.lines[:1])
    def test_duplicate_exec(self): self.reject([self.lines[0],*self.lines])
    def test_failed_root(self): c=copy.deepcopy(self.contract);c['root_returncode']=1;self.reject(contract=c)
    def test_child_nonzero(self): self.reject([*self.lines,'101 +++ exited with 1 +++'])
    def test_abbreviated_environment(self): self.reject([self.lines[0].replace('[])','0x123 /* 3 vars */)'),self.lines[1]])
    def test_critical_env(self): self.reject([self.lines[0].replace('[])','["LD_PRELOAD=/tmp/evil.so"])'),self.lines[1]])
    def test_extra_loader_environment(self): self.reject([self.lines[0].replace('[])','["LD_AUDIT=/tmp/evil.so"])'),self.lines[1]])
    def test_duplicate_env(self): self.reject([self.lines[0].replace('[])','["PATH=/a", "PATH=/b"])'),self.lines[1]])
    def test_missing_env_policy(self): c=copy.deepcopy(self.contract);c['executions'][0]['environment'].pop(tools.INFLUENCING[0]);self.reject(contract=c)
    def test_unknown_write(self): self.reject([self.lines[0],self.lines[1].replace('O_RDONLY|O_CLOEXEC','O_WRONLY|O_CREAT|O_TRUNC')])
    def test_exact_write(self):
        c=copy.deepcopy(self.contract);c['required_reads']=[];c['writes']=[dict(path=str(self.data),flags=['O_WRONLY|O_TRUNC'])]
        self.assertEqual(self.run_trace([self.lines[0],self.lines[1].replace('O_RDONLY|O_CLOEXEC','O_WRONLY|O_TRUNC')],c)['approved_writes'],[str(self.data)])
    def test_no_fd_target(self): self.reject([self.lines[0],self.lines[1].split(' = ')[0]+' = 3'])
    def test_deleted_target(self): self.reject([self.lines[0],self.lines[1][:-1]+' (deleted)>'])
    def test_unfinished(self): self.reject([self.lines[0],self.lines[1].split(' = ')[0]+' <unfinished ...>'])
    def test_resumed(self):
        before,after=self.lines[1].split(', O_RDONLY');before += ', O_RDONLY'
        lines=[self.lines[0],before+' <unfinished ...>','101 <... openat resumed>'+after]
        self.assertEqual(self.run_trace(lines)['distinct_prepinned_reads'],1)
    def test_unknown_syscalls(self):
        for kind in ('execveat','open','openat2','creat'):
            with self.subTest(kind=kind): self.reject([*self.lines,f'101 {kind}("/tmp/unknown", 0) = -1 ENOENT (No such file or directory)'])
    def test_empty_trace(self): self.reject([])
    def test_nonce_exact(self):
        r=dict(argv=['ld','-plugin-opt=-fresolution='+str(self.root)+'/ccABC123.res'],nonce_slots=[dict(index=1,profile='gcc_resolution')])
        self.assertTrue(trace.argv_matches(r,['ld','-plugin-opt=-fresolution='+str(self.root)+'/ccXYZ456.res'],str(self.root)))
        self.assertFalse(trace.argv_matches(r,['ld','-plugin-opt=-fresolution=/tmp/ccXYZ456.res'],str(self.root)))
    def test_nonce_shared_across_subprocess_rules(self):
        prefix='-plugin-opt=-fresolution='+str(self.root)+'/'
        rule=dict(argv=['ld',prefix+'ccABC123.res'],nonce_slots=[dict(index=1,profile='gcc_resolution')])
        state=({}, {})
        self.assertTrue(trace.argv_matches(rule,['ld',prefix+'ccXYZ456.res'],str(self.root),state))
        self.assertTrue(trace.argv_matches(rule,['ld',prefix+'ccXYZ456.res'],str(self.root),state))
        self.assertFalse(trace.argv_matches(rule,['ld',prefix+'ccZZZ456.res'],str(self.root),state))
        reverse_rule=dict(argv=['ld',prefix+'ccDEF123.res'],nonce_slots=[dict(index=1,profile='gcc_resolution')])
        self.assertFalse(trace.argv_matches(reverse_rule,['ld',prefix+'ccXYZ456.res'],str(self.root),state))
    def test_nonce_bounds(self):
        for index in (-1,2,'0'):
            with self.subTest(index=index),self.assertRaises(ValueError): trace.argv_matches(dict(argv=['ld'],nonce_slots=[dict(index=index,profile='gcc_resolution')]),['ld'],str(self.root))
    def test_nonce_duplicate(self):
        with self.assertRaises(ValueError): trace.argv_matches(dict(argv=['ld'],nonce_slots=[dict(index=0,profile='gcc_resolution')]*2),['ld'],str(self.root))
    def test_invalid_count(self):
        for count in (0,-1,True,'1'):
            c=copy.deepcopy(self.contract);c['executions'][0]['count']=count
            with self.subTest(count=count): self.reject(contract=c)
    def test_real_prepinned_trace(self):
        fixture=os.environ.get('TRACE_CLOSURE_FIXTURE')
        if not fixture:self.skipTest('set TRACE_CLOSURE_FIXTURE to retained source-only trace namespace')
        root=Path(fixture);contract=json.loads((root/'fixture-prepinned-policy.json').read_text());text=(root/'qualified-full.strace').read_text()
        self.assertEqual(trace.validate(text,contract)['successful_executions'],2)
        for old,new in [('O_RDONLY|O_CLOEXEC','O_RDWR|O_CLOEXEC'),('"-I"','"-E"'),('/usr/bin/python3','/usr/bin/./python3')]:
            with self.subTest(mutation=old),self.assertRaises(ValueError):trace.validate(text.replace(old,new,1),contract)

if __name__=='__main__':unittest.main(verbosity=2)
