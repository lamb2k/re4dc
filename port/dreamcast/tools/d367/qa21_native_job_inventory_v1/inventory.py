"""Inventory before strict membership refusal; no native operations at import."""
import json

def error(exc):return {'type':type(exc).__name__,'text':str(exc),'winerror':getattr(exc,'winerror',None)}

def capture(api,job,expected,inspect,publish):
    # Persist raw list and expected identity BEFORE any per-member native query.
    pids=api.job_pids(job)
    row={'expected_inner':dict(expected),'member_pids':pids,
         'added':sorted(set(pids)-{expected['pid']}),'missing':sorted({expected['pid']}-set(pids)),
         'members':[],'strict_membership':pids==[expected['pid']]}
    publish(row)
    for pid in pids:
        member={'pid':pid}
        try:member['proof']=inspect(pid)
        except Exception as exc:member['query_error']=error(exc)
        row['members'].append(member);publish(row)
    if not row['strict_membership']:raise RuntimeError('unexpected/missing private job member; inventory preserved')
    if any('query_error' in m or 'query_error' in m.get('proof',{}) for m in row['members']):raise RuntimeError('member identity query failed; inventory preserved')
    return row
