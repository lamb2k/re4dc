#!/usr/bin/env python3
"""Build an isolated hwsim_cg copy with per-frame self-cost exports.

The instruction model and trace order are unchanged. Function charges can also
be split at an audited entry PC, with narrow busy-loop caller attribution. Input
source is read-only, and the copied source plus hashes are retained.
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f'Expected one source anchor, found {text.count(old)}: {old[:60]}')
    return text.replace(old, new, 1)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, default=Path('/root/probe/d367-agents/design-logic/tools/hwsim_cg.c'))
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    original = a.source.read_bytes()
    s = original.decode().replace('\r\n', '\n')
    s = replace_once(s, 'static PcStat other;   /* PCs outside RAM */',
                     'static PcStat other;   /* PCs outside RAM */\n'
                     '''static u32 *frame_pc_func; static u64 *frame_function_cycles;
static u64 *segment_function_cycles;
static u32 frame_function_count;
static unsigned char *bench_marker_map;
static unsigned char *bench_pc_phase;
static u64 *bench_function_cycles;
static u64 *bench_segment_cycles;
static int bench_phase = 4, bench_instrumentation, bench_stack[32], bench_depth;
static u32 bench_other_phase = 4;
static u32 bench_events[11], bench_errors, bench_marker_executing;
static u64 wait_pc_cycles[2][2][0x1000];
static unsigned char wait_pc_context[0x800];
static u32 segment_entry, wait_loop_start, wait_loop_end, wait_func_start, wait_func_end;
static u32 wait_call_pc, wait_return_pc, segment_entries;
static int current_segment, in_wait_call;
static u32 env_hex(const char *name) {
    const char *s = getenv(name); return s ? (u32)strtoul(s, NULL, 16) : 0;
}''')
    s = replace_once(s, '    s->cyc[cat] += (u64)llround(c * 16.0);   /* 1/16 cycle fixed point */',
                     '    s->cyc[cat] += (u64)llround(c * 16.0);   /* 1/16 cycle fixed point */\n'
                     '''    if (frame_function_cycles) {
        u32 idx = s == &other ? 0 : frame_pc_func[s - ps];
        u64 cost = (u64)llround(c * 16.0);
        frame_function_cycles[idx] += cost;
        segment_function_cycles[current_segment * frame_function_count + idx] += cost;
        if (bench_function_cycles) {
            u32 phase = s == &other ? bench_other_phase : bench_pc_phase[s - ps];
            bench_function_cycles[phase * frame_function_count + idx] += cost;
            bench_segment_cycles[(current_segment * 7 + phase) * frame_function_count + idx] += cost;
        }
        u32 pc = s == &other ? 0 : 0x8c000000U + 2U * (u32)(s - ps);
        if (wait_loop_start && pc >= wait_loop_start && pc < wait_loop_end)
            wait_pc_cycles[current_segment][0][(pc - wait_loop_start) >> 1] += cost;
        if (wait_func_start && pc >= wait_func_start && pc < wait_func_end)
            /* Keep the context of the charged PC, including delayed branch stalls. */
            wait_pc_cycles[current_segment][wait_pc_context[(pc - wait_func_start) >> 1]][0x800 + ((pc - wait_func_start) >> 1)] += cost;
    }''')
    s = replace_once(s, '    PcStat *s = PS(pc);\n    double cg_t_in = t_prev;', '''    if (segment_entry && pc == segment_entry) { current_segment = 1; segment_entries++; }
    if (wait_call_pc && pc == wait_call_pc) in_wait_call = 1;
    if (wait_return_pc && pc == wait_return_pc) in_wait_call = 0;
    if (wait_func_start && pc >= wait_func_start && pc < wait_func_end)
        wait_pc_context[(pc - wait_func_start) >> 1] = in_wait_call ? 1 : 0;
    bench_marker_executing = bench_marker_map && ram_valid(pc) ? bench_marker_map[(pc & 0xFFFFFF) >> 1] : 0;
    if (bench_marker_executing) {
        u32 event = bench_marker_executing;
        bench_events[event]++;
        if (event <= 6) bench_phase = event - 1;
        else if (event == 7) bench_instrumentation++;
        else if (event == 8) { if (bench_instrumentation) bench_instrumentation--; else bench_errors++; }
        else if (event == 9) {
            if (bench_depth < 32) bench_stack[bench_depth++] = bench_phase;
            else bench_errors++;
            bench_phase = 2;
        } else if (event == 10) {
            if (bench_depth) bench_phase = bench_stack[--bench_depth];
            else bench_errors++;
        }
    }
    if (bench_pc_phase && ram_valid(pc))
        bench_pc_phase[(pc & 0xFFFFFF) >> 1] = (bench_marker_executing || bench_instrumentation) ? 6 : bench_phase;
    else if (bench_pc_phase)
        bench_other_phase = bench_instrumentation ? 6 : bench_phase;
    PcStat *s = PS(pc);
    double cg_t_in = t_prev;''')
    s = replace_once(s, '    for (int i = 0; i < ntr; i++) {\n', '''    FILE *cg_self_frames = NULL;
    FILE *function_self_frames = NULL;
    FILE *function_segments = NULL, *wait_segments = NULL, *segment_counts = NULL;
    FILE *bench_frames = NULL, *bench_states = NULL, *bench_segments = NULL;
    if (CG) {
        snprintf(path, sizeof(path), "%s.self_frames.tsv", CG_OUT);
        cg_self_frames = fopen(path, "w");
        if (!cg_self_frames) { perror(path); return 1; }
        fprintf(cg_self_frames, "frame\\tnode\\tparent\\tentry\\tself_cycles\\tcalls\\n");
        snprintf(path, sizeof(path), "%s.function_frames.tsv", CG_OUT);
        function_self_frames = fopen(path, "w");
        if (!function_self_frames) { perror(path); return 1; }
        fprintf(function_self_frames, "frame\\tentry\\tself_cycles_16\\n");
        snprintf(path, sizeof(path), "%s.function_segments.tsv", CG_OUT);
        function_segments = fopen(path, "w");
        snprintf(path, sizeof(path), "%s.wait_segments.tsv", CG_OUT);
        wait_segments = fopen(path, "w");
        snprintf(path, sizeof(path), "%s.segment_counts.tsv", CG_OUT);
        segment_counts = fopen(path, "w");
        if (!function_segments || !wait_segments || !segment_counts) return 1;
        fprintf(function_segments, "frame\\tsegment\\tentry\\tself_cycles_16\\n");
        fprintf(wait_segments, "frame\\tsegment\\tpc\\tcontext\\tself_cycles_16\\n");
        fprintf(segment_counts, "frame\\tboundary_entries\\n");
        segment_entry = env_hex("OTHER_SEGMENT_ENTRY");
        wait_loop_start = env_hex("OTHER_WAIT_LOOP_START"); wait_loop_end = env_hex("OTHER_WAIT_LOOP_END");
        wait_func_start = env_hex("OTHER_WAIT_FUNC_START"); wait_func_end = env_hex("OTHER_WAIT_FUNC_END");
        wait_call_pc = env_hex("OTHER_WAIT_CALL_PC"); wait_return_pc = env_hex("OTHER_WAIT_RETURN_PC");
        if (wait_loop_end < wait_loop_start || wait_loop_end - wait_loop_start > 0x1000 ||
            wait_func_end < wait_func_start || wait_func_end - wait_func_start > 0x1000) return 1;
        frame_pc_func = calloc(NPC, sizeof(u32));
        frame_function_count = nfstart + 1;
        frame_function_cycles = calloc(nfstart + 1, sizeof(u64));
        segment_function_cycles = calloc(2 * (nfstart + 1), sizeof(u64));
        if (!frame_pc_func || !frame_function_cycles || !segment_function_cycles) return 1;
        const char *markers = getenv("OTHER_MARKERS_FILE");
        if (markers && *markers) {
            FILE *mf = fopen(markers, "r");
            if (!mf) { perror(markers); return 1; }
            bench_marker_map = calloc(NPC, 1);
            bench_pc_phase = calloc(NPC, 1);
            bench_function_cycles = calloc(7 * (nfstart + 1), sizeof(u64));
            bench_segment_cycles = calloc(14 * (nfstart + 1), sizeof(u64));
            if (!bench_marker_map || !bench_pc_phase || !bench_function_cycles || !bench_segment_cycles) return 1;
            u32 pc, event, count = 0;
            while (fscanf(mf, "%x %u", &pc, &event) == 2) {
                if (!ram_valid(pc) || !event || event > 10 || bench_marker_map[(pc & 0xFFFFFF) >> 1]) return 1;
                bench_marker_map[(pc & 0xFFFFFF) >> 1] = event;
                count++;
            }
            fclose(mf);
            if (!count) return 1;
            snprintf(path, sizeof(path), "%s.bench_function_frames.tsv", CG_OUT);
            bench_frames = fopen(path, "w");
            snprintf(path, sizeof(path), "%s.bench_state_frames.tsv", CG_OUT);
            bench_states = fopen(path, "w");
            snprintf(path, sizeof(path), "%s.bench_segments.tsv", CG_OUT);
            bench_segments = fopen(path, "w");
            if (!bench_frames || !bench_states || !bench_segments) return 1;
            fprintf(bench_frames, "frame\\tphase\\tentry\\tself_cycles_16\\n");
            fprintf(bench_segments, "frame\\tsegment\\tphase\\tentry\\tself_cycles_16\\n");
            fprintf(bench_states, "frame\\tfinal_phase\\tinstrumentation_depth\\tactor_depth\\terrors\\tphase0\\tphase1\\tphase2\\tphase3\\tphase4\\tphase5\\tinstr_begin\\tinstr_end\\tpush_actor\\tpop_actor\\n");
        }
        u32 ordinal = 0;
        for (u32 j = 0; j < NPC; ++j) {
            while (ordinal < (u32)nfstart && ((fstart[ordinal] & 0xFFFFFF) >> 1) <= j) ordinal++;
            frame_pc_func[j] = ordinal;
        }
    }
    for (int i = 0; i < ntr; i++) {
        if (CG) memset(frame_function_cycles, 0, sizeof(u64) * (nfstart + 1));
        if (CG) memset(segment_function_cycles, 0, sizeof(u64) * 2 * (nfstart + 1));
        memset(wait_pc_cycles, 0, sizeof(wait_pc_cycles));
        memset(wait_pc_context, 0, sizeof(wait_pc_context));
        current_segment = 0; segment_entries = 0; in_wait_call = 0;
        if (bench_function_cycles) memset(bench_function_cycles, 0, sizeof(u64) * 7 * (nfstart + 1));
        if (bench_segment_cycles) memset(bench_segment_cycles, 0, sizeof(u64) * 14 * (nfstart + 1));
        if (bench_pc_phase) memset(bench_pc_phase, 4, NPC);
        /* Frame_cnt advances in OTHER, immediately before the phase-0 marker. */
        bench_phase = 4; bench_instrumentation = 0; bench_depth = 0; bench_errors = 0;
        bench_other_phase = 4;
        memset(bench_events, 0, sizeof(bench_events)); bench_marker_executing = 0;
        /* Tooling-only snapshot; preserve the model's complete input history. */
        u32 old_n = CG ? cgn_n : 0;
        double *old_self = CG ? malloc(sizeof(double) * old_n) : NULL;
        u64 *old_calls = CG ? malloc(sizeof(u64) * old_n) : NULL;
        if (CG && (!old_self || !old_calls)) { fprintf(stderr, "snapshot allocation failed\\n"); return 1; }
        for (u32 j = 0; j < old_n; ++j) { old_self[j] = cgn[j].self; old_calls[j] = cgn[j].calls; }
''')
    s = replace_once(s, '        run_trace(tr[i]);\n', '''        run_trace(tr[i]);
        if (CG) for (u32 j = 0; j < cgn_n; ++j) {
            double own = cgn[j].self - (j < old_n ? old_self[j] : 0);
            u64 calls = cgn[j].calls - (j < old_n ? old_calls[j] : 0);
            if (own != 0 || calls != 0)
                fprintf(cg_self_frames, "%d\\t%u\\t%u\\t%08x\\t%.9f\\t%llu\\n", i, j,
                        cgn[j].parent, cgn[j].entry, own, (unsigned long long)calls);
        }
        free(old_self); free(old_calls);
        if (CG) for (u32 j = 0; j <= (u32)nfstart; ++j) if (frame_function_cycles[j])
            fprintf(function_self_frames, "%d\\t%08x\\t%llu\\n", i, j ? fstart[j - 1] : 0,
                    (unsigned long long)frame_function_cycles[j]);
        if (CG) {
            if (bench_function_cycles) {
                for (u32 phase = 0; phase < 7; ++phase) for (u32 j = 0; j <= (u32)nfstart; ++j) {
                    u64 cost = bench_function_cycles[phase * (nfstart + 1) + j];
                    if (cost) fprintf(bench_frames, "%d\\t%u\\t%08x\\t%llu\\n", i, phase,
                                      j ? fstart[j - 1] : 0, (unsigned long long)cost);
                }
                fprintf(bench_states, "%d\\t%d\\t%d\\t%d\\t%u", i, bench_phase, bench_instrumentation, bench_depth, bench_errors);
                for (u32 seg = 0; seg < 2; ++seg) for (u32 phase = 0; phase < 7; ++phase)
                    for (u32 j = 0; j <= (u32)nfstart; ++j) {
                        u64 cost = bench_segment_cycles[(seg * 7 + phase) * (nfstart + 1) + j];
                        if (cost) fprintf(bench_segments, "%d\\t%u\\t%u\\t%08x\\t%llu\\n", i, seg, phase,
                                          j ? fstart[j - 1] : 0, (unsigned long long)cost);
                    }
                for (u32 event = 1; event <= 10; ++event) fprintf(bench_states, "\\t%u", bench_events[event]);
                fprintf(bench_states, "\\n");
            }
            fprintf(segment_counts, "%d\\t%u\\n", i, segment_entries);
            for (u32 seg = 0; seg < 2; ++seg) {
                for (u32 j = 0; j <= (u32)nfstart; ++j) {
                    u64 cost = segment_function_cycles[seg * (nfstart + 1) + j];
                    if (cost) fprintf(function_segments, "%d\\t%u\\t%08x\\t%llu\\n", i, seg,
                                      j ? fstart[j - 1] : 0, (unsigned long long)cost);
                }
                for (u32 ctx = 0; ctx < 2; ++ctx) for (u32 j = 0; j < 0x1000; ++j) {
                    u64 cost = wait_pc_cycles[seg][ctx][j];
                    u32 pc = j < 0x800 ? wait_loop_start + 2*j : wait_func_start + 2*(j-0x800);
                    if (cost) fprintf(wait_segments, "%d\\t%u\\t%08x\\t%s\\t%llu\\n", i, seg, pc,
                        j < 0x800 ? "busy_loop_pc" : ctx ? "retrace_from_busy_loop" : "retrace_other_call",
                        (unsigned long long)cost);
                }
            }
        }
''')
    s = replace_once(s, '    fclose(ff);\n    if (CG) {\n',
                     '    fclose(ff);\n    if (cg_self_frames) fclose(cg_self_frames);\n'
                     '    if (function_self_frames) fclose(function_self_frames);\n'
                     '    if (function_segments) fclose(function_segments);\n'
                     '    if (wait_segments) fclose(wait_segments);\n'
                     '    if (segment_counts) fclose(segment_counts);\n    if (CG) {\n')
    s = replace_once(s, '    if (segment_counts) fclose(segment_counts);\n',
                     '    if (segment_counts) fclose(segment_counts);\n'
                     '    if (bench_frames) fclose(bench_frames);\n'
                     '    if (bench_states) fclose(bench_states);\n'
                     '    if (bench_segments) fclose(bench_segments);\n')
    s = replace_once(s, 'restored %llu synthetic %llu\\n", cgn_n,',
                     'restored %llu synthetic %llu resolved %llu swapped %llu\\n", cgn_n,')
    copied = a.out / 'hwsim_cg_frames.c'
    copied.write_text(s)
    exe = a.out / 'hwsim_cg_frames'
    command = ['cc', '-std=c99', '-O2', str(copied), '-lm', '-o', str(exe)]
    subprocess.run(command, check=True)
    provenance = dict(source=str(a.source), source_sha256=hashlib.sha256(original).hexdigest(),
                      copied_source_sha256=hashlib.sha256(copied.read_bytes()).hexdigest(), command=command,
                      executable=str(exe), executable_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),
                      change='Export self-cost frame/phase deltas and narrow polling PCs; model execution and trace order unchanged')
    (a.out / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
    print(json.dumps(provenance, indent=2))


if __name__ == '__main__':
    main()
