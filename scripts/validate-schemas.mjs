#!/usr/bin/env node
/**
 * JSON-Schema validation of the machine corpus and its contract artifacts.
 *
 * Loads every schema in schemas/ into Ajv (draft 2020-12) and validates:
 *   - machines/**.json              -> machine.schema.json
 *   - domains/domain-manifest.json  -> domain-manifest.schema.json
 *   - domains/domain-registry.json  -> domain-registry.schema.json
 *   - domains/semantic-bus-registry.json -> semantic-bus-registry.schema.json
 *   - triggers/*.example.json       -> ai-trigger-envelope.schema.json
 *   - triggers/*scenario*.json      -> trigger-scenario.schema.json
 *   (triggers/*.template.json is a documentation scaffold and is skipped.)
 *
 * Exits non-zero on any schema violation. This is the enforcement the hand-coded
 * audit-corpus.py cannot provide (it once missed matchAlgorithm:"exact").
 */
import { readFileSync, readdirSync, existsSync } from "node:fs";
import { join, dirname, basename } from "node:path";
import { fileURLToPath } from "node:url";
import Ajv2020 from "ajv/dist/2020.js";
import addFormats from "ajv-formats";

const REPO = join(dirname(fileURLToPath(import.meta.url)), "..");
const SCHEMA_DIR = join(REPO, "schemas");

const ajv = new Ajv2020({ strict: false, allErrors: true, allowUnionTypes: true });
addFormats.default ? addFormats.default(ajv) : addFormats(ajv);

// register every schema by its $id (refs resolve $id-to-$id; $ids are filename-based)
for (const f of readdirSync(SCHEMA_DIR).filter((n) => n.endsWith(".schema.json"))) {
  ajv.addSchema(JSON.parse(readFileSync(join(SCHEMA_DIR, f), "utf8")));
}

const BASE = "https://realityengine.example.org/schemas/";
const validators = {};
function V(schemaFile) {
  if (!validators[schemaFile]) validators[schemaFile] = ajv.getSchema(BASE + schemaFile);
  const v = validators[schemaFile];
  if (!v) throw new Error(`schema not registered: ${schemaFile}`);
  return v;
}

function walk(dir) {
  const out = [];
  for (const e of readdirSync(dir, { withFileTypes: true })) {
    const p = join(dir, e.name);
    if (e.isDirectory()) out.push(...walk(p));
    else if (e.name.endsWith(".json")) out.push(p);
  }
  return out;
}

let total = 0, failed = 0;
const failures = [];

function validateSet(label, files, schemaFile) {
  const v = V(schemaFile);
  let ok = 0, bad = 0;
  for (const f of files) {
    total++;
    let data;
    try { data = JSON.parse(readFileSync(f, "utf8")); }
    catch (e) { bad++; failed++; failures.push([f, `unparseable: ${e.message}`]); continue; }
    if (v(data)) { ok++; }
    else {
      bad++; failed++;
      const e = v.errors[0];
      failures.push([f, `${e.instancePath || "(root)"} ${e.message}`]);
    }
  }
  console.log(`  ${bad === 0 ? "ok  " : "FAIL"} ${label.padEnd(46)} ${ok} valid / ${bad} invalid  (vs ${schemaFile})`);
}

const machines = existsSync(join(REPO, "machines")) ? walk(join(REPO, "machines")) : [];
validateSet(`machines (${machines.length})`, machines, "machine.schema.json");
validateSet("domain-manifest", [join(REPO, "domains/domain-manifest.json")], "domain-manifest.schema.json");
validateSet("domain-registry", [join(REPO, "domains/domain-registry.json")], "domain-registry.schema.json");
validateSet("semantic-bus-registry", [join(REPO, "domains/semantic-bus-registry.json")], "semantic-bus-registry.schema.json");

const trig = existsSync(join(REPO, "triggers")) ? readdirSync(join(REPO, "triggers")).filter((n) => n.endsWith(".json")) : [];
const examples = trig.filter((n) => n.endsWith(".example.json")).map((n) => join(REPO, "triggers", n));
const scenarios = trig.filter((n) => n.includes("scenario")).map((n) => join(REPO, "triggers", n));
validateSet(`trigger envelopes (${examples.length})`, examples, "ai-trigger-envelope.schema.json");
validateSet(`trigger scenarios (${scenarios.length})`, scenarios, "trigger-scenario.schema.json");

console.log(`\n  total=${total} failed=${failed}`);
if (failed) {
  console.log("\n  first failures:");
  for (const [f, msg] of failures.slice(0, 25)) console.log(`    ${basename(f)}: ${msg}`);
  process.exit(1);
}
console.log("  all corpus artifacts are schema-valid.");
