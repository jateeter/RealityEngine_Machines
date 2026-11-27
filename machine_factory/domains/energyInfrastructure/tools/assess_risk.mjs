#!/usr/bin/env node
/** Conservative synthetic posture only; no clearance, incident action or risk acceptance. */
import {readFileSync} from 'node:fs';
import {resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {isDeepStrictEqual} from 'node:util';
import Ajv2020 from 'ajv/dist/2020.js';
import addFormats from 'ajv-formats';
import {validateThreatFixture} from './validate_threat_fixture.mjs';
import {validateFunctionBindings} from './validate_function_bindings.mjs';
import {screenStorageProposal} from './screen_storage_proposal.mjs';
const ROOT=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const read=p=>JSON.parse(readFileSync(p,'utf8'));
const hash=b=>createHash('sha256').update(b).digest('hex');
const require=(ok,msg)=>{if(!ok)throw Error(msg);};
const keys=(o,s)=>o&&typeof o==='object'&&!Array.isArray(o)&&isDeepStrictEqual(Object.keys(o).sort(),s.split(' ').sort());
const ajv=new Ajv2020({strict:false});addFormats(ajv);
const date=ajv.compile({type:'string',format:'date-time',pattern:'^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d{3})?Z$'});
const time=s=>{require(date(s)&&Number.isFinite(Date.parse(s)),'Invalid risk timestamp');return Date.parse(s);};
const contextKeys='topologyRevision credentialRevision firmwareRevision policyRevision modelRevision ragRevision electricalMode';
function context(c){require(keys(c,contextKeys)&&Object.values(c).every(v=>typeof v==='string'&&v.length>0)&&['GRID_CONNECTED','DEGRADED_OBSERVABILITY','RECOVERY'].includes(c.electricalMode),'Invalid risk context');}
function source(root,path,expected){const b=readFileSync(resolve(root,path));require(hash(b)===expected,'Risk source hash mismatch: '+path);return JSON.parse(b);}

export function assessRisk(input,root=ROOT) {
 require(keys(input,'schemaVersion kind sourceProjection sourceProjectionSHA256 sourceThreatFixture sourceThreatFixtureSHA256 policyPath policySHA256 evaluationAt context previousContext priorRiskDisposition feed assetBindings findings engineeringReview controlAction behavioralCasesRun'),'Unsupported risk fields');
 require(input.schemaVersion==='1.0.0'&&input.kind==='SYNTHETIC_OT_RISK_ASSESSMENT'&&input.sourceProjection==='assets/function-bindings/ref01_connected.json'&&input.sourceThreatFixture==='assets/synthetic-threat-fixture.json'&&input.policyPath==='assets/generic-risk-policy.json'&&input.engineeringReview==='PENDING'&&input.controlAction==='DENY'&&input.behavioralCasesRun===0,'Unsupported risk scope/claims');
 const projection=source(root,input.sourceProjection,input.sourceProjectionSHA256);require(!validateFunctionBindings(projection,root).length,'Invalid risk asset projection');
 const threat=source(root,input.sourceThreatFixture,input.sourceThreatFixtureSHA256);require(!validateThreatFixture(threat).length,'Invalid pinned synthetic threat fixture');
 const p=source(root,input.policyPath,input.policySHA256);
 require(keys(p,'schemaVersion kind revision status maxFeedAgeMs maxFindingAgeMs clearanceSupported treatment controlAction')&&p.schemaVersion==='1.0.0'&&p.kind==='DRAFT_GENERIC_RISK_POLICY'&&typeof p.revision==='string'&&p.revision.length>0&&p.status==='NOT_SECURITY_APPROVED'&&p.clearanceSupported===false&&p.treatment==='HOLD_DISCRETIONARY_PROPOSALS_ONLY'&&p.controlAction==='DENY'&&['maxFeedAgeMs','maxFindingAgeMs'].every(k=>Number.isSafeInteger(p[k])&&p[k]>0&&p[k]<=3600000),'Unsupported conservative risk policy');
 context(input.context);context(input.previousContext);require(input.context.policyRevision===p.revision&&['UNKNOWN','BLOCKED'].includes(input.priorRiskDisposition),'Unsupported policy revision/prior posture');
 const evaluation=time(input.evaluationAt),feed=input.feed;
 require(keys(feed,'sourceId receivedAt quality complete')&&feed.sourceId==='SYNTHETIC_FEED'&&['GOOD','BAD','UNKNOWN'].includes(feed.quality)&&typeof feed.complete==='boolean','Invalid synthetic feed metadata');
 const received=time(feed.receivedAt);require(received<=evaluation,'Future threat-feed receipt');
 const reasons=['NO_CLEARANCE_IMPLEMENTED'],freshFeed=feed.quality==='GOOD'&&evaluation-received<=p.maxFeedAgeMs;
 if(!freshFeed)reasons.push('THREAT_FEED_UNUSABLE_OR_STALE');
 if(!feed.complete)reasons.push('THREAT_FEED_INCOMPLETE');
 const changed=Object.keys(input.context).filter(k=>input.context[k]!==input.previousContext[k]);
 if(changed.length)reasons.push('CONTEXT_CHANGED_REASSESSMENT_REQUIRED');
 require(Array.isArray(input.assetBindings)&&input.assetBindings.length>0&&input.assetBindings.length<=128&&Array.isArray(input.findings)&&input.findings.length<=128,'Invalid risk input count');
 const objects=new Map(threat.bundle.objects.map(o=>[o.id,o])),assets=new Set(projection.bindings.map(b=>b.assetId)),bound=new Map(),mappedAssets=new Set();
 for(const b of input.assetBindings){require(keys(b,'infrastructureRef assetId')&&objects.get(b.infrastructureRef)?.type==='infrastructure'&&assets.has(b.assetId)&&!bound.has(b.infrastructureRef)&&!mappedAssets.has(b.assetId),'Invalid/duplicate infrastructure asset mapping');bound.set(b.infrastructureRef,b.assetId);mappedAssets.add(b.assetId);}
 const ids=new Set(),findings=[];let affected=false;
 for(const f of input.findings) {
  require(keys(f,'id infrastructureRef vulnerabilityRef relationshipRef assetId observedAt receivedAt quality applicability evidenceClass')&&typeof f.id==='string'&&f.id.length>0&&!ids.has(f.id)&&['GOOD','BAD','UNKNOWN'].includes(f.quality)&&['AFFECTED','UNKNOWN','NOT_AFFECTED'].includes(f.applicability)&&f.evidenceClass==='SYNTHETIC_ASSERTION_ONLY','Invalid synthetic finding');ids.add(f.id);
  const infra=objects.get(f.infrastructureRef),vuln=objects.get(f.vulnerabilityRef),rel=objects.get(f.relationshipRef);
  require(bound.get(f.infrastructureRef)===f.assetId&&infra?.type==='infrastructure'&&vuln?.type==='vulnerability'&&rel?.type==='relationship'&&rel.relationship_type==='related-to'&&rel.source_ref===f.infrastructureRef&&rel.target_ref===f.vulnerabilityRef,'Finding source/type/asset mismatch');
  const observed=time(f.observedAt),rtime=time(f.receivedAt);require(observed<=rtime&&rtime<=evaluation&&rtime<=received,'Invalid finding/feed receipt ordering');
  const why=[];
  if(f.quality!=='GOOD'||evaluation-observed>p.maxFindingAgeMs)why.push('FINDING_UNUSABLE_OR_STALE');
  if([infra,vuln,rel].some(o=>o.revoked===true||time(o.modified)>evaluation))why.push('THREAT_OBJECT_REVOKED_OR_NOT_AVAILABLE');
  if(changed.length)why.push('FINDING_CONTEXT_REASSESSMENT_REQUIRED');
  const usable=freshFeed&&!why.length;
  if(f.applicability==='AFFECTED'&&usable){affected=true;why.push('AFFECTED_SYNTHETIC_ASSERTION');}
  else if(f.applicability==='NOT_AFFECTED')why.push('NO_QUALIFIED_CLEARANCE_EVIDENCE');
  else if(f.applicability==='UNKNOWN')why.push('APPLICABILITY_UNRESOLVED');
  findings.push({id:f.id,assetId:f.assetId,usable,assertedApplicability:f.applicability,reasons:why});
 }
 if(!input.findings.length)reasons.push('NO_ASSESSMENT_FINDINGS');
 const latched=input.priorRiskDisposition==='BLOCKED';if(latched)reasons.push('PRIOR_BLOCK_REQUIRES_SEPARATE_REVIEW');
 if(affected)reasons.push('AFFECTED_ASSERTION_HOLDS_DISCRETIONARY_ACTIONS');
 return {verificationType:'SYNTHETIC_CONSERVATIVE_RISK_ASSESSMENT_ONLY',riskDisposition:latched||affected?'BLOCKED':'UNKNOWN',treatment:'HOLD_DISCRETIONARY_PROPOSALS_ONLY',reasons,findings,reassessmentContextChanges:changed,electricalMode:input.context.electricalMode,residualRiskAccepted:false,clearanceSupported:false,operatingAuthorityGranted:false,controlAction:'DENY',behavioralCasesRun:0};
}

export function evaluateRiskProposalBridge(input,root=ROOT) {
 require(keys(input,'schemaVersion kind sourceAssessment sourceAssessmentSHA256 sourceProposalTemplate sourceProposalTemplateSHA256 proposalFrame controlAction behavioralCasesRun')&&input.schemaVersion==='1.0.0'&&input.kind==='SYNTHETIC_RISK_PROPOSAL_BRIDGE'&&input.sourceAssessment==='assets/risk-assessment-fixture.json'&&input.sourceProposalTemplate==='assets/storage-proposal-screen.json'&&input.controlAction==='DENY'&&input.behavioralCasesRun===0,'Unsupported risk bridge scope/claims');
 const assessment=source(root,input.sourceAssessment,input.sourceAssessmentSHA256),template=source(root,input.sourceProposalTemplate,input.sourceProposalTemplateSHA256),frame=structuredClone(input.proposalFrame);
 const withoutTimes=v=>{const x=structuredClone(v);delete x.evaluationAt;delete x.state.observedAt;delete x.state.receivedAt;delete x.proposal.issuedAt;delete x.proposal.expiresAt;return x;};
 require(isDeepStrictEqual(withoutTimes(frame),withoutTimes(template)),'Bridge may only shift synthetic template clock fields');
 require(frame.evaluationAt===assessment.evaluationAt&&frame.sourceProjection===assessment.sourceProjection&&frame.sourceProjectionSHA256===assessment.sourceProjectionSHA256&&frame.state.topologyRevision===assessment.context.topologyRevision&&frame.state.mode===assessment.context.electricalMode,'Risk/proposal context binding mismatch');
 const before=screenStorageProposal(frame,root),risk=assessRisk(assessment,root);
 // Apply only a stricter posture; electrical/protection state and proposal authority stay untouched.
 const rank={CLEAR:0,UNKNOWN:1,BLOCKED:2};if(rank[risk.riskDisposition]>rank[frame.state.riskDisposition])frame.state.riskDisposition=risk.riskDisposition;
 const after=screenStorageProposal(frame,root);
 return {verificationType:'SYNTHETIC_RISK_PROPOSAL_BRIDGE_ONLY',risk,proposalBefore:before,proposalAfter:after,composedState:frame.state,electricalProtectionStateUnchanged:isDeepStrictEqual({...frame.state,riskDisposition:template.state.riskDisposition},{...input.proposalFrame.state,riskDisposition:template.state.riskDisposition}),controlAction:'DENY',behavioralCasesRun:0};
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
 try {if(process.argv.length!==3)throw Error('Usage: node tools/assess_risk.mjs <assessment-or-bridge.json>');const d=read(resolve(process.argv[2]));console.log(JSON.stringify({result:'PASS',...(d.kind==='SYNTHETIC_RISK_PROPOSAL_BRIDGE'?evaluateRiskProposalBridge(d):assessRisk(d))},null,2));}
 catch(e){console.error(e.message);process.exitCode=1;}
}
