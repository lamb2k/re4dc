"""Bridge retained bea2 private readback without changing its provenance."""
from pathlib import Path
import importlib.util
P=Path(__file__).resolve().parent
def normalized_actual_private(private,pin):
 path=P.parent/'package-coverage-census23/contracts.py'
 spec=importlib.util.spec_from_file_location('retained_private_contract',path)
 previous=importlib.util.module_from_spec(spec);spec.loader.exec_module(previous)
 result=previous.normalized_actual_private(private,pin)
 return dict(result,source='f2405bb06ebaff6e2a7681479d5308ec5d3b988a',retained_private_authority_source=private['source'])
