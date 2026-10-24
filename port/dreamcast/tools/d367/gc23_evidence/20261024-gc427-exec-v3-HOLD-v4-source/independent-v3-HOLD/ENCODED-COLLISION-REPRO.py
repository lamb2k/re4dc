import json
drift=[]
baseline={"members":{}}
def encoded(j):
    return (json.dumps(j, indent=1) + '\n').encode()
encoded = (json.dumps(drift, indent=1) + '\n').encode()
baseline_bytes = encoded(baseline)
