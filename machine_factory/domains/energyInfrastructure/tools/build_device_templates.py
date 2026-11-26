#!/usr/bin/env python3
"""Catalog every DI type and its source declarations; no UA server executes."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
UA='http://opcfoundation.org/UA/'
DI=UA+'DI/'
NS={'u':'http://opcfoundation.org/UA/2011/03/UANodeSet.xsd'}
PINNED={
 'intake/opcua-di/Opc.Ua.Di.NodeSet2.xml':('40a02d98a8b2a014ec9f961625a422df3566d4dd783151ec6ae55b47296199de','ed0b821f6a6f1f0c440c442ed95a9146ae8b7f8d'),
 'intake/opcua-di/Opc.Ua.NodeSet2.xml':('d9377ad5e0880528367ed6a7ab6a1d0654ef1e5807323aa3bee286ea2ee26731','dee199135d85a5cb0dc5db25e27228b1f9d7ea0d')}
TYPE_CLASSES={'UAObjectType','UAVariableType','UADataType','UAReferenceType'}

def render(root):
    receipt=json.loads((root/'assets/opcua-source-receipt.json').read_text())
    if receipt['repository']!='https://github.com/OPCFoundation/UA-Nodeset' or receipt['ragIndexed'] or len(receipt['files'])!=2 or {f['path'] for f in receipt['files']}!=set(PINNED):raise ValueError('OPC source identity/collection boundary mismatch')
    actual={p.relative_to(root).as_posix() for p in (root/'intake/opcua-di').rglob('*') if p.is_file() and p.name!='.DS_Store'}
    if actual!=set(PINNED)|{'intake/opcua-di/.gitattributes'}:raise ValueError('Unlisted OPC source artifact')
    nodes={};models={};required={};di_keys=[]
    for source in receipt['files']:
        path=source['path'];digest,commit=PINNED[path];raw=(root/path).read_bytes()
        if source['sha256']!=digest or source['commit']!=commit or hashlib.sha256(raw).hexdigest()!=digest or len(raw)!=source['bytes']:raise ValueError('OPC source hash mismatch')
        if b'OPC Foundation MIT License 1.00' not in raw[:2000] or b'<!DOCTYPE' in raw:raise ValueError('OPC source license/parser boundary mismatch')
        document=ET.fromstring(raw);model=document.find('u:Models/u:Model',NS)
        if source['model']!=model.attrib or source['requiredModels']!=[e.attrib for e in model]:raise ValueError('OPC model metadata mismatch')
        model_uri=model.attrib['ModelUri'];models[model_uri]=dict(model.attrib);required[model_uri]=[dict(e.attrib) for e in model]
        namespaces=[UA]+[e.text for e in document.findall('u:NamespaceUris/u:Uri',NS)]
        aliases={e.attrib['Alias']:e.text for e in document.findall('u:Aliases/u:Alias',NS)}
        def key(token):
            token=aliases.get(token,token)
            match=re.fullmatch(r'(?:ns=(\d+);)?([isgb]=.+)',token)
            if not match:raise ValueError('Unsupported NodeId: '+str(token))
            index=int(match[1] or 0)
            if index>=len(namespaces):raise ValueError('Unresolved NodeId namespace')
            return namespaces[index]+'|'+match[2]
        for node in document:
            kind=node.tag.split('}')[-1]
            if not kind.startswith('UA') or 'NodeId' not in node.attrib:continue
            node_key=key(node.attrib['NodeId'])
            if node_key in nodes:raise ValueError('Duplicate namespace-qualified NodeId')
            refs=[{'referenceType':key(r.attrib['ReferenceType']),'target':key(r.text),'forward':r.attrib.get('IsForward','true')=='true'} for r in node.findall('u:References/u:Reference',NS)]
            fields=[]
            for f in node.findall('u:Definition/u:Field',NS):
                record=dict(f.attrib)
                if 'DataType' in f.attrib:record['dataTypeNodeKey']=key(f.attrib['DataType'])
                fields.append(record)
            value=node.find('u:Value',NS)
            entry={'nodeKey':node_key,'nodeClass':kind,'attributes':dict(node.attrib),
                'sourcePath':path,'sourceLocator':"UANodeSet/"+kind+"[@NodeId='"+node.attrib['NodeId']+"']",
                'documentation':[e.text for e in node.findall('u:Documentation',NS)],'references':refs,'definitionFields':fields,
                'valueDefinitionXML':ET.tostring(value,encoding='unicode') if value is not None else None,
                'dataTypeNodeKey':key(node.attrib['DataType']) if 'DataType' in node.attrib else None,
                'parentNodeKey':key(node.attrib['ParentNodeId']) if 'ParentNodeId' in node.attrib else None}
            nodes[node_key]=entry
            if model_uri==DI:di_keys.append(node_key)
    if DI not in models or UA not in models or len(required[DI])!=1:raise ValueError('Missing DI/core model dependency')
    for field in ['ModelUri','Version','PublicationDate']:
        if required[DI][0][field]!=models[UA][field]:raise ValueError('Required core model edition/date mismatch')
    def k(i):return UA+'|i='+str(i)
    unresolved=[];reference_count=0
    for node_key in di_keys:
        node=nodes[node_key]
        targets=[r[field] for r in node['references'] for field in ['referenceType','target']]
        targets += [v for v in [node['dataTypeNodeKey'],node['parentNodeKey']] if v]
        targets += [f['dataTypeNodeKey'] for f in node['definitionFields'] if 'dataTypeNodeKey' in f]
        reference_count+=len(node['references'])
        unresolved.extend(t for t in targets if t not in nodes)
    if unresolved:raise ValueError('Unresolved DI source references: '+str(sorted(set(unresolved))[:8]))
    def bases(node):return [r['target'] for r in node['references'] if r['referenceType']==k(45) and not r['forward']]
    def ancestors(node_key,seen=()):
        if node_key in seen:raise ValueError('Cyclic type inheritance')
        result=[]
        for base in bases(nodes[node_key]):
            if base not in nodes:raise ValueError('Unresolved base type')
            result.append(base);result.extend(ancestors(base,seen+(node_key,)))
        return result
    # Resolve hierarchical reference subtypes without assuming every reference is a child.
    hierarchical={k(33)}
    changed=True
    while changed:
        changed=False
        for key,node in nodes.items():
            if node['nodeClass']=='UAReferenceType' and key not in hierarchical and any(b in hierarchical for b in bases(node)):
                hierarchical.add(key);changed=True
    templates=[];support=set()
    for node_key in di_keys:
        node=nodes[node_key]
        if node['nodeClass'] not in TYPE_CLASSES:continue
        chain=ancestors(node_key)
        members=[r['target'] for r in node['references'] if r['forward'] and r['referenceType'] in hierarchical]
        support.update(key for key in chain+members if key not in di_keys)
        templates.append({'templateId':'opcua-di-'+node['attributes']['NodeId'].replace(';','-').replace('=',''),
            'classId':node_key,'nodeClass':node['nodeClass'],'browseName':node['attributes']['BrowseName'],
            'isAbstract':node['attributes'].get('IsAbstract','false')=='true','standardId':'OP17',
            'integrationContextStandardId':'OP23','integrationContextArtifact':'assets/fsgim-integration-context.json',
            'edition':models[DI],'sourceLocator':node['sourceLocator'],'documentation':node['documentation'],
            'baseTypeKeys':bases(node),'ancestorTypeKeys':chain,'declaredMemberKeys':members,
            'declaredMandatoryMemberKeys':[m for m in members if any(r['referenceType']==k(37) and r['target']==k(78) and r['forward'] for r in nodes[m]['references'])],
            'declaredMandatoryPlaceholderKeys':[m for m in members if any(r['referenceType']==k(37) and r['target']==k(11510) and r['forward'] for r in nodes[m]['references'])],
            'interfaceKeys':[r['target'] for r in node['references'] if r['forward'] and r['referenceType']==k(17603)],
            'instanceRequirements':{'hardwareMode':'SIMULATED_REQUIRED_HARDWARE','genericAllowedForAllCases':True,
                'concreteDerivedTypeRequiredIfAbstract':True,'topologyBindings':[],'authorityBindings':[],
                'parameterUnitsUncertaintyFaults':None,'simulatorVersion':None,'controlAction':'DENY','measuredIntegrationReceipt':None,
                'status':'UNBOUND_TEMPLATE_NOT_RUNTIME_NODE'}})
    counts=dict(sorted(Counter(t['nodeClass'] for t in templates).items()))
    if counts!={'UADataType':9,'UAObjectType':42,'UAReferenceType':5,'UAVariableType':2} or len(di_keys)!=447:raise ValueError('DI type/declaration coverage mismatch')
    # Preserve modelling-rule targets as explicit metadata; no privilege is inferred.
    for node_key in di_keys:
        node=nodes[node_key]
        dependencies=[r[field] for r in node['references'] for field in ['referenceType','target']]
        dependencies += [v for v in [node['dataTypeNodeKey'],node['parentNodeKey']] if v]
        dependencies += [f['dataTypeNodeKey'] for f in node['definitionFields'] if 'dataTypeNodeKey' in f]
        support.update(key for key in dependencies if key not in di_keys)
    return {'schemaVersion':'1.0.0','status':'PARTIAL_OP17_DI_FORMAL_TYPE_COVERAGE_NOT_STACK_CONFORMANCE',
        'sourceReceipt':'assets/opcua-source-receipt.json','normativeCoverageComplete':False,
        'models':models,'requiredModels':required,'coreDependencyEditionMatched':True,'typeCounts':counts,
        'diDeclarationCount':447,'diReferenceCount':reference_count,'templates':templates,
        'declarations':{key:nodes[key] for key in di_keys},'supportingCoreDefinitions':{key:nodes[key] for key in sorted(support)},
        'remaining':['Complete OPC UA core/MQTT and selected companion/profile scope review','Full prose/modelling-rule/inherited-instance and wire codec validation','Reviewed role/class mappings, units, safety/fault/uncertainty parameters','Secure peer pins, actual simulator/runtime/adapter and authentic admission evidence']}

def check(root):
    try:return [] if render(root)==json.loads((root/'assets/device-class-catalog.json').read_text()) else ['DI class catalog/source mismatch']
    except (OSError,ValueError,KeyError,TypeError,IndexError,ET.ParseError) as e:return [str(e)]

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write',action='store_true');args=p.parse_args()
    if args.write:(ROOT/'assets/device-class-catalog.json').write_text(json.dumps(render(ROOT),indent=2)+'\n')
    errors=check(ROOT);print(json.dumps({'result':'FAIL' if errors else 'PASS','diTypeTemplates':58,'diDeclarations':447,'normativeCoverageComplete':False,'errors':errors}));raise SystemExit(bool(errors))
