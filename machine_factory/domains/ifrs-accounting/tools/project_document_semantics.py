"""Independent documentary workflow graph; not a replacement native OWL corpus."""
import json
from pathlib import Path
from urllib.parse import quote
from rdflib import Graph,Literal,Namespace,RDF,RDFS,OWL
ROOT=Path(__file__).resolve().parents[1];D=Namespace('urn:re:ifrs:document:');g=Graph();g.bind('doc',D);g.bind('owl',OWL);g.bind('rdfs',RDFS)
for cls in ['DocumentAssetType','AgentFamily','Machine','DocumentDuty','AccountingControl']:
 g.add((D[cls],RDF.type,OWL.Class));g.add((D[cls],RDFS.label,Literal(cls)))
for p in ['ownsAssetType','dependsOn','requiresControl','hasDuty','contributesTo','performedByFamily']:
 g.add((D[p],RDF.type,OWL.ObjectProperty))
for p in ['motivation','ownerName','reviewerName','authorityClass','machineId','responsibility','paragraphs']:
 g.add((D[p],RDF.type,OWL.DatatypeProperty))
catalog=json.loads((ROOT/'document-asset-catalog.json').read_text())['assetTypes']
for a in catalog:
 node=D['asset-'+a['assetTypeId']];f=D['family-'+a['familyId']]
 for triple in [(node,RDF.type,D.DocumentAssetType),(node,RDFS.label,Literal(a['title'])),(node,D.motivation,Literal(a['motivation'])),(node,D.ownerName,Literal(a['ownerName'])),(node,D.reviewerName,Literal(a['reviewerName'])),(node,D.authorityClass,Literal(a['authorityClass'])),(f,RDF.type,D.AgentFamily),(f,D.ownsAssetType,node)]:g.add(triple)
 for dep in a['dependencies']:g.add((node,D.dependsOn,D['asset-'+dep]))
 for c in a['controlIds']:g.add((node,D.requiresControl,D['control-'+c]))
for c in json.loads((ROOT/'source-requirements.json').read_text())['controls']:
 node=D['control-'+c['id']];g.add((node,RDF.type,D.AccountingControl));g.add((node,RDFS.label,Literal(c['obligation'])));g.add((node,D.paragraphs,Literal(c['paragraphs'])))
for m in json.loads((ROOT/'machine-document-duty-index.json').read_text())['machines']:
 node=D['machine-'+quote(m['machineId'],safe='')];g.add((node,RDF.type,D.Machine));g.add((node,D.machineId,Literal(m['machineId'])))
 for duty in m['responsibilityContract']['duties']:
  d=D['duty-'+quote(m['machineId'],safe='')+'-'+duty['assetTypeId']]
  for t in [(d,RDF.type,D.DocumentDuty),(node,D.hasDuty,d),(d,D.contributesTo,D['asset-'+duty['assetTypeId']]),(d,D.performedByFamily,D['family-'+m['familyId']]),(d,D.motivation,Literal(duty['motivation'])),(d,D.responsibility,Literal(duty['responsibility']))]:g.add(t)
(ROOT/'semantics').mkdir(exist_ok=True);(ROOT/'semantics/document-workflows.ttl').write_text('# Documentary workflow graph. Deterministically sorted N-Triples, valid Turtle syntax.\n'+'\n'.join(sorted(g.serialize(format='nt').splitlines()))+'\n');parsed=Graph().parse(ROOT/'semantics/document-workflows.ttl',format='turtle')
print(json.dumps({'status':'PASS','tripleCount':len(parsed),'assetTypes':len(catalog),'scope':'RDF parse and projection counts only; no native ELK/HermiT or live semantic acceptance claimed'}))
