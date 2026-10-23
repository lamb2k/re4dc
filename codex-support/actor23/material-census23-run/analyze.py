"""Parse captured census logs; output is unqualified until new image binding."""
import argparse,json
from pathlib import Path
from material_census import census
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--result',required=True);p.add_argument('--log',required=True);p.add_argument('--output');a=p.parse_args();r=census(json.loads(Path(a.result).read_text()),Path(a.log).read_text(errors='replace'));raw=json.dumps(r,indent=2)+'\n'
 if a.output:
  with Path(a.output).open('x')as out:out.write(raw)
 else:print(raw,end='')
if __name__=='__main__':main()
