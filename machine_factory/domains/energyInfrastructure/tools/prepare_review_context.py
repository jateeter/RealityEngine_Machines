#!/usr/bin/env python3
"""On-demand public model review excerpts; no model, embedding, authority or RAG admission."""
import argparse
import hashlib
import json
import platform
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from build_device_templates import NS,UA,DI,PINNED

ROOT=Path(__file__).resolve().parents[1]
MODEL_PIN='90b4a331dcca1d6eac69c1bead952fddcc5852e0'
MODELS={103:'5b5dd26a9cb8058e32c1f70f5c3a9681d326cbb37068d1f3b9765b5188fe7455',203:'0038b9bf820a91e3629ca6d0cf12c4eddedd25127f1fbbb93aa458209e83012b'}
LICENSE_SHA='c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4'
POLICY='assets/public-model-review-policy.json'
ALLOWED={'SUNSPEC_SELECTED','OPCUA_DI'}
STOP={'the','a','an','of','for','and','or','is','in','what','which','show','model'}

def require(ok,message):
    if not ok:raise ValueError(message)
def keys(value,names):
    return isinstance(value,dict) and set(value)==set(names.split())
def sha(raw):return hashlib.sha256(raw).hexdigest()
def read(root,path):return json.loads((root/path).read_text())
def checked(root,path,digest):
    raw=(root/path).read_bytes();require(sha(raw)==digest,'Public source hash mismatch: '+path);return raw
def tokens(text):
    split=re.sub(r'([a-z])([A-Z])',r'\1 \2',text)
    return {s.lower() for s in re.findall(r'[A-Za-z0-9_]+',text+' '+split) if s.lower() not in STOP}
def base_packet(query):
    return {'verificationType':'PUBLIC_IMPLEMENTATION_REVIEW_LOOKUP_ONLY','policySHA256':query['policySHA256'],
        'status':'ABSTAIN','reason':None,'results':[],'sourceNotices':[],'sourceCoverage':[],
        'sourceState':'COLLECTED_REFERENCE_ONLY','normativeAuthority':False,'readyForModelUse':False,
        'rankingMethod':'STRICT_LEXICAL_ALL_TERMS_NO_SEMANTIC_VALIDATION',
        'extractorVersion':'public-review-lookup/1.0.0','parserVersions':None,'maxPacketBytes':65536,
        'packetEncoding':'UTF8_JSON_INDENT_2_WITH_TRAILING_NEWLINE',
        'answerGenerated':False,'embeddingCreated':False,'persistedIndexCreated':False,
        'retrievedTextTrust':'UNTRUSTED_SOURCE_DATA_NOT_INSTRUCTIONS','toolPermissionsGranted':[],
        'controlAction':'DENY','behavioralCasesRun':0}

def sunspec(root):
    receipt=read(root,'assets/source-receipt.json')
    require(receipt['commit']==MODEL_PIN and receipt['license']=='Apache-2.0' and receipt['ragIndexed'] is False,'SunSpec collection boundary changed')
    files={f['path']:f for f in receipt['files']}
    license_path='intake/public-models/sunspec/LICENSE'
    require(files[license_path]['sha256']==LICENSE_SHA,'SunSpec license receipt mismatch')
    notice=checked(root,license_path,LICENSE_SHA).decode('utf8');chunks=[]
    for n,digest in MODELS.items():
        path=f'intake/public-models/sunspec/model_{n}.json';require(files[path]['sha256']==digest,'SunSpec model receipt mismatch')
        model=json.loads(checked(root,path,digest));group=model['group'];points=group['points']
        for i,p in enumerate(points):
            sf=next((v for v in points if v['name']==p.get('sf')),None)
            chunks.append({'sourceId':'SUNSPEC_SELECTED','sourcePath':path,'parentSHA256':digest,'edition':MODEL_PIN,
                'locatorKind':'JSON_POINTER','locator':f'/group/points/{i}','identity':f'model:{n}/point:{p["name"]}',
                'representation':'SERIALIZED_SOURCE_JSON_VALUE_NOT_VERBATIM_PROSE','excerpt':json.dumps(p,sort_keys=True,ensure_ascii=False),
                'context':{'groupName':group['name'],'groupLabel':group.get('label'),'scaleFactorPoint':sf},
                'claimScope':'PINNED_PUBLIC_IMPLEMENTATION_REFERENCE_NOT_NORMATIVE_CONFORMANCE','incompleteContext':True})
    return chunks,{'sourceId':'SUNSPEC_SELECTED','license':'Apache-2.0','noticePath':license_path,'noticeSHA256':LICENSE_SHA,'noticeText':notice}

def opcua(root):
    receipt=read(root,'assets/opcua-source-receipt.json');require(receipt['ragIndexed'] is False,'OPC collection boundary changed')
    files={f['path']:f for f in receipt['files']};documents={}
    for path,(digest,commit) in PINNED.items():
        require(files[path]['sha256']==digest and files[path]['commit']==commit,'OPC source receipt mismatch')
        raw=checked(root,path,digest)
        require(b'<!DOCTYPE' not in raw.upper() and b'<!ENTITY' not in raw.upper(),'XML external/entity declarations forbidden')
        documents[path]=(raw,ET.fromstring(raw))
    path='intake/opcua-di/Opc.Ua.Di.NodeSet2.xml';raw,document=documents[path]
    model=document.find('u:Models/u:Model',NS);required=[dict(e.attrib) for e in model]
    core=documents['intake/opcua-di/Opc.Ua.NodeSet2.xml'][1].find('u:Models/u:Model',NS)
    require(model.attrib['Version']=='1.05.0' and core.attrib['Version']=='1.05.04' and len(required)==1 and all(required[0][k]==core.attrib[k] for k in ['ModelUri','Version','PublicationDate']),'OPC model dependency drift')
    namespaces=[UA]+[e.text for e in document.findall('u:NamespaceUris/u:Uri',NS)]
    aliases={e.attrib['Alias']:e.text for e in document.findall('u:Aliases/u:Alias',NS)}
    chunks=[]
    for node in document:
        if 'NodeId' not in node.attrib:continue
        kind=node.tag.split('}')[-1];node_id=node.attrib['NodeId']
        m=re.fullmatch(r'(?:ns=(\d+);)?([isgb]=.+)',node_id);require(m is not None,'Unsupported DI NodeId')
        index=int(m[1] or 0);require(index<len(namespaces),'DI namespace unresolved')
        chunks.append({'sourceId':'OPCUA_DI','sourcePath':path,'parentSHA256':PINNED[path][0],
            'edition':files[path]['commit'],'locatorKind':'NODESET_NODE_ID','locator':node_id,
            'identity':namespaces[index]+'|'+m[2]+'|'+node.attrib.get('BrowseName',''),
            'representation':'SERIALIZED_XML_NODE_NOT_VERBATIM_SOURCE_BYTES','excerpt':ET.tostring(node,encoding='unicode'),
            'context':{'nodeClass':kind,'attributes':dict(node.attrib),'model':dict(model.attrib),'requiredModels':required,'namespaceUris':namespaces,'aliases':aliases},
            'claimScope':'PINNED_FORMAL_NODESET_FRAGMENT_NOT_RUNTIME_OR_COMPLETE_MODEL','incompleteContext':True})
    match=re.search(rb'<!--(.*?)-->',raw,re.S);require(match is not None and b'OPC Foundation MIT License 1.00' in match[1],'OPC source notice missing')
    notice=match[1].decode('utf8')
    return chunks,{'sourceId':'OPCUA_DI','license':receipt['license'],'noticePath':path,'noticeSHA256':sha(match[1]),'noticeText':notice}

def prepare_review_context(query,root=ROOT):
    root=Path(root)
    require(keys(query,'schemaVersion kind policySHA256 role purpose scope tenantId siteId questionType sourceIds query limit controlAction') and query['schemaVersion']=='1.0.0' and query['kind']=='PUBLIC_MODEL_REVIEW_QUERY' and query['controlAction']=='DENY','Unsupported review query fields/claims')
    raw=(root/POLICY).read_bytes();require(sha(raw)==query['policySHA256'],'Review policy hash mismatch');p=json.loads(raw)
    require(keys(p,'schemaVersion kind revision sourceState requiredRole requiredPurpose requiredScope allowedSourceIds disabledSourceIds maxResults maxExcerptBytes modelUseEnabled embeddingIndexEnabled controlAction') and p['schemaVersion']=='1.0.0' and p['kind']=='PUBLIC_MODEL_REVIEW_LOOKUP_POLICY' and p['sourceState']=='COLLECTED_REFERENCE_ONLY' and p['requiredRole']=='DOMAIN_REVIEWER' and p['requiredPurpose']=='IMPLEMENTATION_MODEL_REVIEW' and p['requiredScope']=='PUBLIC_LICENSED_IMPLEMENTATION_ONLY' and p['modelUseEnabled'] is False and p['embeddingIndexEnabled'] is False and p['controlAction']=='DENY','Unsupported review-only policy')
    require(isinstance(p['allowedSourceIds'],list) and len(p['allowedSourceIds'])==2 and set(p['allowedSourceIds'])==ALLOWED and isinstance(p['disabledSourceIds'],list) and all(s in ALLOWED for s in p['disabledSourceIds']),'Invalid review source scope')
    require(type(p['maxResults']) is int and 1<=p['maxResults']<=5 and type(p['maxExcerptBytes']) is int and 256<=p['maxExcerptBytes']<=8192,'Invalid review packet bounds')
    out=base_packet(query)
    def abstain(reason):out['status']='ABSTAIN';out['reason']=reason;return out
    # All purpose/access/source-state filtering precedes source text reads and ranking.
    if query['role']!=p['requiredRole'] or query['purpose']!=p['requiredPurpose']:return abstain('ROLE_OR_PURPOSE_NOT_PERMITTED')
    if query['scope']!=p['requiredScope'] or query['tenantId']!='PUBLIC' or query['siteId'] is not None:return abstain('NONPUBLIC_SCOPE_NOT_SUPPORTED')
    if query['questionType']!='IMPLEMENTATION_REFERENCE':return abstain('NO_REVIEWED_NORMATIVE_OR_OPERATIONAL_AUTHORITY')
    sources=query['sourceIds']
    require(isinstance(sources,list) and 1<=len(sources)<=2 and all(isinstance(s,str) for s in sources) and len(set(sources))==len(sources),'Invalid requested source set')
    if not set(sources)<=ALLOWED:return abstain('SOURCE_OUT_OF_SCOPE')
    if set(sources)&set(p['disabledSourceIds']):return abstain('SOURCE_DISABLED')
    require(isinstance(query['query'],str) and 0<len(query['query'])<=256 and type(query['limit']) is int and 1<=query['limit']<=p['maxResults'],'Invalid review query/limit')
    terms=tokens(query['query']);require(len(terms)<=32,'Review query token limit')
    if not terms:return abstain('NO_SUPPORTED_QUERY_TOKENS')
    scored=[];notices={}
    for source_id in sources:
        chunks,notice=(sunspec(root) if source_id=='SUNSPEC_SELECTED' else opcua(root));notices[source_id]=notice;oversized=0
        for c in chunks:
            if len(c['excerpt'].encode())>p['maxExcerptBytes']:oversized+=1;continue
            body,identity=tokens(c['excerpt']),tokens(c['identity'])
            if not terms<=body|identity:continue
            score=len(terms&body)+4*len(terms&identity)
            if score:scored.append((score,c))
        out['sourceCoverage'].append({'sourceId':source_id,'candidateCount':len(chunks),'oversizedCandidatesOmitted':oversized})
    scored.sort(key=lambda item:(-item[0],item[1]['sourceId'],item[1]['sourcePath'],item[1]['locator']))
    for score,c in scored[:query['limit']]:out['results'].append({**c,'lexicalScore':score})
    if not out['results']:return abstain('NO_LEXICAL_SUPPORT')
    used={c['sourceId'] for c in out['results']};out['sourceNotices']=[notices[s] for s in sorted(used)]
    out['parserVersions']={'python':platform.python_version(),'ElementTree':'stdlib:'+platform.python_version(),'json':'stdlib:'+platform.python_version()}
    out['status']='REVIEW_PACKET';out['reason']='IMPLEMENTATION_EXCERPTS_ONLY_NOT_A_GENERATED_ANSWER'
    if len((json.dumps(out,ensure_ascii=False,indent=2)+'\n').encode())>out['maxPacketBytes']:
        out['results']=[];out['sourceNotices']=[];return abstain('PACKET_SIZE_LIMIT')
    return out

def verify_review_packet(packet,query,root=ROOT):
    try:return [] if packet==prepare_review_context(query,root) else ['Packet differs from current authorized query/source/policy bytes']
    except (OSError,ValueError,KeyError,TypeError,ET.ParseError) as e:return ['Packet source/policy verification failed: '+str(e)]

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('query',type=Path);args=p.parse_args()
    try:print(json.dumps(prepare_review_context(json.loads(args.query.read_text())),indent=2,ensure_ascii=False))
    except (OSError,ValueError,KeyError,TypeError,ET.ParseError) as e:p.exit(1,str(e)+'\n')
