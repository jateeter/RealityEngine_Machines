// Validate this package's candidate machines against the repository's
// machine.schema.json with the same Ajv setup scripts/validate-schemas.mjs uses.
//   node tools/validate_schema.mjs [repo-root]
import { readFileSync, readdirSync } from "node:fs";
import { createRequire } from "node:module";
import { join, dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const PKG = join(dirname(fileURLToPath(import.meta.url)), "..");
const REPO = resolve(process.argv[2] || join(PKG, "..", "..", ".."));
const require = createRequire(join(REPO, "package.json"));
const Ajv2020 = require("ajv/dist/2020.js").default ?? require("ajv/dist/2020.js");
const addFormatsMod = require("ajv-formats");
const addFormats = addFormatsMod.default ?? addFormatsMod;

const ajv = new Ajv2020({ strict: false, allErrors: true, allowUnionTypes: true });
addFormats(ajv);
const SCHEMA_DIR = join(REPO, "schemas");
for (const f of readdirSync(SCHEMA_DIR).filter((n) => n.endsWith(".schema.json"))) {
  ajv.addSchema(JSON.parse(readFileSync(join(SCHEMA_DIR, f), "utf8")));
}
const v = ajv.getSchema("https://realityengine.example.org/schemas/machine.schema.json");

let bad = 0;
const dir = join(PKG, "machines");
const files = readdirSync(dir).filter((n) => n.endsWith(".json")).sort();
for (const f of files) {
  const data = JSON.parse(readFileSync(join(dir, f), "utf8"));
  if (!v(data)) {
    bad++;
    for (const e of v.errors.slice(0, 5)) console.log(`FAIL ${f}: ${e.instancePath || "(root)"} ${e.message}`);
  }
}
console.log(`schema: ${files.length - bad} valid / ${bad} invalid (vs schemas/machine.schema.json)`);

const vb = ajv.getSchema("https://realityengine.example.org/schemas/agent-behavior.schema.json");
const adir = join(PKG, "agent-candidates", "ai-governance-regime");
const afiles = readdirSync(adir).filter((n) => n.endsWith(".agent.json")).sort();
let abad = 0;
for (const f of afiles) {
  const data = JSON.parse(readFileSync(join(adir, f), "utf8"));
  if (!vb(data)) {
    abad++;
    for (const e of vb.errors.slice(0, 5)) console.log(`FAIL ${f}: ${e.instancePath || "(root)"} ${e.message}`);
  }
}
console.log(`behaviors: ${afiles.length - abad} valid / ${abad} invalid (vs schemas/agent-behavior.schema.json)`);
process.exit(bad || abad ? 1 : 0);
