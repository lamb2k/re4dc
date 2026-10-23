"""Join strict aggregate closure with exact material-r1 owner observations."""
import hashlib,re
from census_log import census as aggregate_census
from actor_log import require
import parse_owner_witness as owner
SOURCE='f2405bb06ebaff6e2a7681479d5308ec5d3b988a'
PROGRAMME='41beee7f50af4ff50c49b03a7cfa53d794086646322c5ebe7a85ffc7805a883d'
def census(result,text):
 proof=aggregate_census(result,text)
 raw=text.encode('utf-8')
 parsed=owner.parse(raw,dict(source=SOURCE,source_parent=owner.SOURCE_PARENT,
  format_source_sha256=owner.FORMAT_SOURCE_SHA256,log_sha256=hashlib.sha256(raw).hexdigest(),
  programme_sha256=PROGRAMME,reader_complete=True,log_overflow=False))
 require(parsed['format_complete'], 'incomplete/refused material owner witness: '+parsed.get('error','unknown'))
 require(parsed['mode']==1 and parsed['qualified'] is False and parsed['reported_owner2b_pre_position_skips']==parsed['reported_owner2b_positions_avoided']==0,'mode1 material observations only')
 terminal=text.index('[end: head=')
 rows=list(re.finditer(r'^AV23OWNER[^\r\n]*',text,re.M))
 require(rows and all(row.end()<terminal for row in rows),'all owner continuations must flush inside original reader output')
 require(parsed['reported_owner2b_potential_sections']>0 and sum(row['would'] for row in parsed['roles'])>0,'meaningful census requires attributable owner2b potential')
 proof.update(owner_observations=parsed,owner_parser_schema=owner.SCHEMA_ID,
  owner_attributable_potential_observed=True,qualified=False,
  actor_attribution='AV23 totals remain aggregate only. Owner2b potential is attributed only by the complete material-r1 owner records.',
  scope='Mode1 draws everything. No actual culling, matched pixels, work RAM or physical console performance qualification.')
 return proof
