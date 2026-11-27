#!/usr/bin/env python3
"""Reproduce public implementation review policy/query, without admitting a RAG collection."""
import argparse
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def encode(v):return (json.dumps(v,indent=2)+'\n').encode()
def build(root):
    policy={'schemaVersion':'1.0.0','kind':'PUBLIC_MODEL_REVIEW_LOOKUP_POLICY','revision':'review.lookup.v1','sourceState':'COLLECTED_REFERENCE_ONLY','requiredRole':'DOMAIN_REVIEWER','requiredPurpose':'IMPLEMENTATION_MODEL_REVIEW','requiredScope':'PUBLIC_LICENSED_IMPLEMENTATION_ONLY','allowedSourceIds':['SUNSPEC_SELECTED','OPCUA_DI'],'disabledSourceIds':[],'maxResults':3,'maxExcerptBytes':8192,'modelUseEnabled':False,'embeddingIndexEnabled':False,'controlAction':'DENY'}
    query={'schemaVersion':'1.0.0','kind':'PUBLIC_MODEL_REVIEW_QUERY','policySHA256':hashlib.sha256(encode(policy)).hexdigest(),'role':'DOMAIN_REVIEWER','purpose':'IMPLEMENTATION_MODEL_REVIEW','scope':'PUBLIC_LICENSED_IMPLEMENTATION_ONLY','tenantId':'PUBLIC','siteId':None,'questionType':'IMPLEMENTATION_REFERENCE','sourceIds':['SUNSPEC_SELECTED'],'query':'AC Power Watts','limit':2,'controlAction':'DENY'}
    return {'public-model-review-policy.json':policy,'public-model-review-query.json':query}
def check(root):
    try:return ['Review lookup policy/query drift: '+n for n,d in build(root).items() if not (root/'assets'/n).is_file() or json.loads((root/'assets'/n).read_text())!=d]
    except (OSError,ValueError,KeyError,TypeError) as e:return [str(e)]
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write',action='store_true');args=p.parse_args()
    if args.write:
        for n,d in build(ROOT).items():(ROOT/'assets'/n).write_bytes(encode(d))
    errors=check(ROOT);print(json.dumps({'result':'FAIL' if errors else 'PASS','reviewLookupPolicies':1,'errors':errors}));raise SystemExit(bool(errors))
