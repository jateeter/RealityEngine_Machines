#!/usr/bin/env python3
"""Derive project TAXII resource schemas from retained normative property tables."""
import argparse
from collections import defaultdict
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SOURCE_HASH='ae8cf71e9527a066ec3cbc8fff631c4832600aad01f521b274b1636919f1f420'
SOURCE_URL='https://docs.oasis-open.org/cti/taxii/v2.1/os/taxii-v2.1-os.html'
CLASSES=[('error','3.6.1 Error Message',0),('envelope','3.7 Envelope Resource',0),('discovery','4.1.1 Discovery Resource',0),('api-root','4.2.1 API Root Resource',0),('status','4.3.1 Status Resource',0),('status-details','4.3.1 Status Resource',1),('collections','5.1.1 Collections Resource',0),('collection','5.2.1 Collection Resource',0),('manifest','5.3.1 Manifest Resource',0),('manifest-record','5.3.1 Manifest Resource',1),('versions','5.8.1 Versions Resource',0)]

class Tables(HTMLParser):
    def __init__(self):
        super().__init__();self.heading=None;self.heading_text=[];self.last='';self.depth=0;self.rows=[];self.row=[];self.cell=None;self.tables=defaultdict(list)
    def handle_starttag(self,tag,attrs):
        if tag in ['h1','h2','h3','h4']:self.heading=tag;self.heading_text=[]
        if tag=='table':
            self.depth+=1
            if self.depth==1:self.rows=[]
        if self.depth==1 and tag=='tr':self.row=[]
        if self.depth==1 and tag in ['td','th']:self.cell=[]
    def handle_data(self,data):
        if self.heading:self.heading_text.append(data)
        if self.cell is not None:self.cell.append(data)
    def handle_endtag(self,tag):
        if tag==self.heading:self.last=' '.join(''.join(self.heading_text).split());self.heading=None
        if self.depth==1 and tag in ['td','th'] and self.cell is not None:self.row.append(' '.join(''.join(self.cell).split()));self.cell=None
        if self.depth==1 and tag=='tr':self.rows.append(self.row)
        if tag=='table':
            if self.depth==1 and self.rows and self.rows[0] and self.rows[0][0]=='Property Name':self.tables[self.last].append(self.rows[1:])
            self.depth-=1

def render(root):
    receipt=json.loads((root/'assets/taxii-source-receipt.json').read_text())
    if receipt['url']!=SOURCE_URL or receipt['sha256']!=SOURCE_HASH or receipt['encoding']!='windows-1252' or receipt['ragIndexed'] or receipt['path']!='intake/taxii21/taxii-v2.1-os.html':raise ValueError('TAXII source identity/rights boundary mismatch')
    if receipt['edition']!='TAXII Version 2.1 OASIS Standard 2021-06-10':raise ValueError('TAXII source edition mismatch')
    source=root/receipt['path'];raw=source.read_bytes()
    if len(raw)!=receipt['bytes'] or hashlib.sha256(raw).hexdigest()!=SOURCE_HASH:raise ValueError('TAXII source hash mismatch')
    parser=Tables();parser.feed(raw.decode('windows-1252'))
    if sum(map(len,parser.tables.values()))!=11:raise ValueError('TAXII property-table inventory mismatch')
    definitions={};templates=[]
    def property_schema(kind):
        if kind in ['string','identifier']:return {'type':'string','minLength':1}
        if kind=='timestamp':return {'type':'string','format':'date-time','pattern':'Z$'}
        if kind=='boolean':return {'type':'boolean'}
        if kind=='integer':return {'type':'integer','minimum':0,'maximum':9007199254740991}
        if kind=='dictionary':return {'type':'object'}
        if kind.startswith('list of type '):
            target=kind.removeprefix('list of type ')
            items={'type':'object'} if target=='<STIX Object>' else ({'type':'string','minLength':1} if target=='string' else {'$ref':'#/$defs/'+target})
            return {'type':'array','minItems':1,'items':items}
        raise ValueError('Unreviewed TAXII property type: '+kind)
    for name,heading,ordinal in CLASSES:
        rows=parser.tables[heading][ordinal];properties={};required=[];trace=[]
        for row in rows:
            label,kind=row[:2];field=label.split(' (')[0];mandatory=label.endswith('(required)')
            if not mandatory and not label.endswith('(optional)'):raise ValueError('Unknown property requirement: '+label)
            properties[field]=property_schema(kind)
            if mandatory:required.append(field)
            trace.append({'name':field,'type':kind,'required':mandatory})
        if name=='status':properties['status']['enum']=['complete','pending']
        definitions[name]={'type':'object','properties':properties,'required':required,'additionalProperties':False}
        templates.append({'templateId':'taxii21-'+name,'classId':name,'classKind':'SUPPORTING_RECORD' if name in ['status-details','manifest-record'] else 'TAXII_RESOURCE','standardId':'SC16','edition':receipt['edition'],'sourceURL':SOURCE_URL,'sourceSection':heading.split()[0],'sourcePropertyTableOrdinal':ordinal,'propertyDeclarations':trace,'schemaRef':'assets/taxii-resource.schema.json#/$defs/'+name,'schemaAuthority':'PROJECT_AUTHORED_NON_NORMATIVE','instance':{'payload':None,'synthetic':True,'networkExecution':False,'controlAction':'DENY','measuredIntegrationReceipt':None}})
    schema={'$schema':'https://json-schema.org/draft/2020-12/schema','$id':'https://realityengine.local/energyInfrastructure/taxii-resource.schema.json','$comment':'Project closed fixture profile derived from property tables; not an OASIS schema. Original source and Notices are retained at intake/taxii21/taxii-v2.1-os.html.','$defs':definitions}
    catalog={'schemaVersion':'1.0.0','status':'TAXII_RESOURCE_TABLE_COVERAGE_NOT_PROTOCOL_CONFORMANCE','sourceReceipt':'assets/taxii-source-receipt.json','resourceCount':9,'supportingRecordCount':2,'normativeCoverageComplete':False,'templates':templates,'profileRestrictions':['Unknown/custom properties rejected','Nonempty strings/lists when present','Nonnegative safe JSON integer counts','UTC timestamps','Synthetic offline fixtures only'],'remaining':['Full prose/errata and protocol/security review','Authentication, TLS, HTTP/media negotiation and pagination behavior','Actual peer selection and end-to-end integration','Operational threat assessment and authentic admission evidence']}
    return {'assets/taxii-resource.schema.json':schema,'assets/taxii-resource-catalog.json':catalog}

def check(root):
    try:return [rel+' differs from TAXII source-derived output' for rel,data in render(root).items() if not (root/rel).is_file() or json.loads((root/rel).read_text())!=data]
    except (OSError,ValueError,KeyError,TypeError,IndexError) as e:return [str(e)]

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write',action='store_true');args=p.parse_args()
    if args.write:
        for rel,data in render(ROOT).items():(ROOT/rel).write_text(json.dumps(data,indent=2)+'\n')
    errors=check(ROOT);print(json.dumps({'result':'FAIL' if errors else 'PASS','taxiiResources':9,'supportingRecords':2,'normativeCoverageComplete':False,'errors':errors}));raise SystemExit(bool(errors))
