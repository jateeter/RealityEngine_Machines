"""Read-only compliance evidence screen. Never certifies or publishes statements.

The caller must hold the canonical store transaction and authenticate context.
Inventory completeness is measured against the versioned development control
inventory; its interpretation and coverage still require independent review.
"""
import hashlib
import json


def assess(store, rules, context, requirements, catalog):
    blockers, snapshots = [], {}

    def current(aid):
        if aid in snapshots:
            return snapshots[aid]
        head = store.head(context, aid)
        if not head or head.get("status") != "APPROVED":
            blockers.append({"assetTypeId": aid, "reason": "MISSING_OR_UNAPPROVED"})
            snapshots[aid] = None
            return None
        revision = store.revision(context, aid, head["revision"])
        if (not revision or revision.get("contentHash") != head.get("contentHash")
                or revision.get("evidenceClass") != context["evidenceClass"]
                or head.get("inputFingerprint") != rules.input_fingerprint(context, store._upstream(context, aid))):
            blockers.append({"assetTypeId": aid, "reason": "STALE_OR_SCOPE_MISMATCH"})
            snapshots[aid] = None
            return None
        keys = ["assetTypeId", "entityId", "period", "evidenceClass", "content", "evidenceRefs", "upstreamRefs", "inputFingerprint"]
        if any(k not in revision for k in keys) or rules.hashed({k: revision[k] for k in keys}) != head["contentHash"]:
            blockers.append({"assetTypeId": aid, "reason": "CANONICAL_CONTENT_HASH_MISMATCH"})
            snapshots[aid] = None
            return None
        review = head.get("review") or {}
        if (review.get("revision") != head["revision"] or review.get("contentHash") != head["contentHash"]
                or review.get("reviewerName") != store.catalog[aid]["reviewerName"]
                or review.get("ownerName") == review.get("reviewerName")
                or review.get("unresolvedItems") != []
                or any(review.get(k) is not True for k in ["evidenceChecked", "citationsChecked", "reconciliationsChecked"])):
            blockers.append({"assetTypeId": aid, "reason": "EXACT_INDEPENDENT_REVIEW_MISSING"})
            snapshots[aid] = None
            return None
        snapshots[aid] = (head, revision)
        return snapshots[aid]

    if context.get("unresolvedRequirements") != []:
        blockers.append({"reason": "OPEN_OR_UNASSESSED_ACCOUNTING_REQUIREMENTS"})
    for aid in ["ELIGIBILITY-MEMO", "EDITION-TRANSITION-PACK", "STATEMENT-BUNDLE"]:
        current(aid)
    eligibility = snapshots.get("ELIGIBILITY-MEMO")
    if eligibility and eligibility[1]["content"].get("conclusion") != "ELIGIBLE_SUBJECT_TO_REVIEW":
        blockers.append({"reason": "ELIGIBILITY_NOT_ESTABLISHED"})
    checklist = current("DISCLOSURE-CHECKLIST")
    expected = {c["id"] for c in requirements["controls"]}
    mandatory = {c["id"] for c in requirements["controls"] if c.get("sectionId") == "03" and c.get("paragraphs") == "3.3"}
    count = 0
    if checklist:
        rows = checklist[1]["content"].get("requirements")
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            blockers.append({"reason": "TYPED_REQUIREMENT_DISPOSITIONS_MISSING"})
        else:
            ids = [r.get("controlId") for r in rows]
            if any(not isinstance(i, str) for i in ids) or len(ids) != len(set(ids)) or set(ids) != expected:
                blockers.append({"reason": "INVENTORY_INCOMPLETE_DUPLICATE_OR_UNKNOWN"})
            mapping = {cid: {a["assetTypeId"] for a in catalog["assetTypes"] if a["assetTypeId"] not in {"COMPLIANCE-REVIEW", "DISCLOSURE-CHECKLIST"} and any(r["controlId"] == cid for r in a["sourceRequirements"])} for cid in expected}
            for row in rows:
                cid = row.get("controlId")
                if not isinstance(cid, str):
                    blockers.append({"reason": "INVALID_CONTROL_IDENTIFIER"})
                    continue
                if (not isinstance(row.get("basis"), str) or not row["basis"].strip()
                        or not isinstance(row.get("evidenceRefs"), list) or not row["evidenceRefs"]
                        or any(not isinstance(ref, str) or not ref.strip() for ref in row["evidenceRefs"])):
                    blockers.append({"controlId": cid, "reason": "DISPOSITION_BASIS_OR_EVIDENCE_MISSING"})
                    continue
                if row.get("disposition") == "NOT_APPLICABLE" and cid in mandatory:
                    blockers.append({"controlId": cid, "reason": "COMPLIANCE_REQUIREMENT_CANNOT_BE_WAIVED"})
                    continue
                if row.get("disposition") == "NOT_APPLICABLE":
                    # Whole-checklist exact independent approval covers this rationale.
                    count += 1
                    continue
                refs = row.get("assetRefs")
                if row.get("disposition") != "MET" or not isinstance(refs, list) or not refs:
                    blockers.append({"controlId": cid, "reason": "REQUIREMENT_NOT_SATISFIED"})
                    continue
                for ref in refs:
                    aid = ref.get("assetTypeId") if isinstance(ref, dict) else None
                    if aid not in mapping.get(cid, set()):
                        blockers.append({"controlId": cid, "reason": "UNMAPPED_ACCOUNTING_EVIDENCE"})
                        continue
                    value = current(aid)
                    if value and (ref.get("revision") != value[0]["revision"] or ref.get("contentHash") != value[0]["contentHash"]):
                        blockers.append({"controlId": cid, "reason": "REFERENCED_REVISION_NOT_CURRENT"})
                count += 1
    return {"status": "UNRESOLVED" if blockers else "ADVISORY",
            "decision": "COMPLIANCE_EVIDENCE_INCOMPLETE" if blockers else "READY_FOR_INDEPENDENT_COMPLIANCE_CONCLUSION",
            "sourceControl": "3.3", "reviewRequired": True, "releasePerformed": False,
            "requirementCount": len(expected), "dispositionsInspected": count,
            "blockerCount": len(blockers), "blockers": blockers[:100],
            "canonicalRefs": [{"assetTypeId": aid, "revision": value[0]["revision"], "contentHash": value[0]["contentHash"]} for aid, value in sorted(snapshots.items()) if value],
            "inventorySHA256": hashlib.sha256(json.dumps(requirements, sort_keys=True).encode()).hexdigest()}
