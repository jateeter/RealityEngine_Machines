# Release Note: ISO/IEC 42001 Statement of Applicability (SoA) Template

Here is your file: `ISO42001_Statement_of_Applicability_Template.md`.

This standalone Markdown file packages the **ISO/IEC 42001:2023 Statement of Applicability (SoA) Template** for your audit binder, including:

* **Annex A Control Mapping Matrix (`A.2` – `A.10`):** Links every ISO/IEC 42001 Annex A control objective directly to its **`AIGovernanceRegime`** implementation mechanism and the corresponding cryptographic receipt inside the **`M-GOV-13` (`ControlCrosswalkAssembler`)** Auditor Evidence Pack.
* **External Auditor Verification Procedure:** Outlines the three deterministic verification steps (`RFC 8785` + `Ed25519` signature check, `re:AuditorEvidencePackShape` SHACL validation, and `3-of-3` C++/Scala/Lisp deterministic replay from initial state $S_0$).
* **Certification Sign-Off Record:** Provides a structured table for Preparer, Approver, and External Lead Auditor WebIDs and canonical `SHA-256` receipt hashes.

---

> **Authoritative Source Note:** All architectural primitives, receipt formats, and audit gates in this SoA template are grounded in **RealityEngine: Deterministic Pre-Execution Governance for Agentic AI with Temporally Bounded Incompleteness**, **Version 0.18 (Working Draft, 19 November 2026)**, which serves as the current authoritative specification.
