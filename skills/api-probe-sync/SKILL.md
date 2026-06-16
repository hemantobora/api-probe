---
name: api-probe-sync
description: Synchronise an existing api-probe probes.yaml with an updated API collection while preserving all developer-written validation and output wiring. Use when the user asks to "sync probes", "update probes from the collection", "check probe drift", or has changed a Postman/Bruno/Insomnia/OpenAPI/HAR source and wants the existing probe file reconciled without losing their validation.
metadata:
  author: hemantobora
  version: 0.1.0
  category: API Testing
  tags: [api-probe, sync, yaml, testing]
---

# api-probe: Sync

Sync an existing probe file with an updated API collection, preserving all developer-written validation. Work through the steps in order. Reach for the bundled references only when a step needs the detail they hold.

## Global rules

- If the user says **stop**, **exit**, or **terminate** at any point, stop immediately. Do not write any changes.
- If the user says **continue** or **resume** and you were waiting for a response, re-ask the same question — do not skip it.
- Never ask the user to reply with numbers. Always present visual lists or checkbox tables and accept natural language responses.

---

## Step 0 — Resolve probe file location

Check `.api-probe/config.yaml`. The `probes:` key can be a single path or a list:

```yaml
# Single file
probes: api-probe/probes.yaml

# Multiple files
probes:
  - api-probe/orders/probes.yaml
  - api-probe/products/probes.yaml
```

**Single path** → use it directly.

**Multiple paths** → determine which file to sync:
1. Compare endpoint overlap — which probe file contains the most endpoints that also appear in the incoming collection? Use that one.
2. If overlap is unclear or equal → present a menu:

   > "I found multiple probe files. Which one should I sync with this collection?
   >
   > ▸ api-probe/orders/probes.yaml
   > ▸ api-probe/products/probes.yaml"

3. Wait for selection, then proceed with the chosen file only.

**No config found** → fall back to `api-probe/probes.yaml`.

**Resolved file does not exist** → tell the user and stop. Suggest running the generate skill first.

All subsequent steps operate on the single resolved path.

---

## Ownership model (critical)

Sync touches structural fields only and never overwrites developer intent. The full field-by-field ownership table and the `!include`-protection rule are in [`references/diff-and-ownership.md`](references/diff-and-ownership.md). In short: `name`, `type`, `endpoint`, `method`, `headers`, `body` are sync-owned (update from collection); `validation`, `output`, `ignore`, `delay`, `timeout`, `retry`, `debug`, `verify` are user-owned (preserve exactly). Any field using `!include` is user-owned and its reference is preserved verbatim.

---

## Step 1 — Parse both inputs

Parse the collection file (same format detection as the generate skill's Phase 2b). Parse the existing probe file at the resolved path. Note any probes using `!include` for body, validation, or variables — these are `!include`-protected and never touched.

**If any existing probes are `type: graphql`**, also scan the project for a GraphQL schema (`schema.graphql`, `*.graphql` under `graphql/`/`src/graphql/`/`api/`/`schema/`, or `schema.json` introspection). If found, build an operation map (operation → required non-null args + return-type non-null fields) for the Step 2 diff. If a probe uses `query: !include queries/[file].graphql`, read that file to extract its operation name and field selection. If no schema is found, skip GraphQL schema diffing and detect collection-level changes only.

---

## Step 2 — Diff

Run the three-pass diff (name match → method+endpoint match for renames → GraphQL schema diff) and classify each probe as `added` | `updated` | `removed` | `unchanged`. The full pass logic and the GraphQL schema-diff detection table are in [`references/diff-and-ownership.md`](references/diff-and-ownership.md).

---

## Step 3 — Merge

```
UPDATED probe  = sync-owned fields from collection + user-owned fields from existing (unchanged)
ADDED probe    = collection probe + placeholder validation comment
REMOVED probe  = keep in file, mark with # SYNC: removed comment
```

For `!include`-protected fields, copy the existing reference as-is — never expand or replace it. Order: existing order preserved → removed probes marked in place → added probes appended at end.

---

## Step 4 — Apply DAG to added probes only

Run DAG detection on added probes only (same logic as the generate skill's Phase 4 DAG ordering). Insert new probes in dependency order relative to existing probes. Do **not** reorder existing probes.

---

## Step 5 — Executions block

- Add new environment variables found in the collection but not in existing executions.
- Never remove or overwrite existing variable values.
- If an execution uses `validations: !include validations/[env].yaml`, preserve that line exactly — do not replace with inline validations.
- Add new execution entries only if the collection defines environments not already present.

---

## Step 6 — Update config.yaml (multi-file safe)

When writing back to `.api-probe/config.yaml`: load the full existing config, update only the entry for the file just synced, and preserve all other `probes:` entries exactly. Never rewrite the entire list. If the config uses a single-path string and the synced file matches, leave it as a string (do not convert to a list). Worked example in [`references/merge-and-emit.md`](references/merge-and-emit.md).

---

## Step 7 — Emit with inline comments

Write the merged file using `# SYNC:` comments to flag every change (updated endpoints, preserved `!include` references, removed probes, added probes needing validation, new GraphQL variables/fields). See [`references/merge-and-emit.md`](references/merge-and-emit.md) for the full annotated emit example.

---

## Check mode

If the user asks to **check for drift only** (no file changes): output a diff summary (probe name + what changed: endpoint, method, headers, body, GraphQL variables, schema fields) and a verdict — "✓ in sync" or "✗ X probes drifted — run sync to update". Do not modify any files.

---

After writing changes, always append:

> 📄 **Schema reference:** https://github.com/hemantobora/api-probe/blob/main/docs/SCHEMA_SPECIFICATION.md
