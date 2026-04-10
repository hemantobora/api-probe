---
name: api-probe:sync
description: Sync an existing probes.yaml with an updated API collection (Postman, Bruno, Insomnia, OpenAPI, HAR) — preserving all developer-written validation
---

Sync an existing probe file with an updated API collection, preserving all developer-written validation.

**Global rules:**
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

**Resolved file does not exist** → tell the user and stop. Suggest running `/api-probe:generate` first.

All subsequent steps operate on the single resolved path.

---

## Ownership model (critical)

| Owner | Fields | Rule |
|-------|--------|------|
| **Sync-owned** (from collection) | `name`, `type`, `endpoint`, `method`, `headers`, `body` | Always update from collection |
| **User-owned** (from developer) | `validation`, `output`, `ignore`, `delay`, `timeout`, `retry`, `debug`, `verify` | Never overwrite — preserve exactly as-is |

**`!include` is user-owned.** If any field uses `!include` — whether `body`, `validation`, or `variables` — treat the entire field as user-owned and do not replace it with inline content. Preserve the `!include` reference exactly.

---

## Step 1 — Parse both inputs

Parse the collection file (same format detection as the generate prompt Phase 2b).
Parse the existing probe file at the resolved path.

Note any probes that use `!include` for body, validation, or variables — these are flagged as `!include`-protected and their referenced fields will never be touched.

**If any existing probes are `type: graphql`** — also scan the project for a GraphQL schema:
- Look for `schema.graphql`, `*.graphql` in `graphql/`, `src/graphql/`, `api/`, or any `schema/` directory
- Also check for `schema.json` (introspection result)
- If found, parse it to build an operation map: operation name → required variables (non-null `!` args) + return type non-null fields
- If a probe uses `query: !include queries/[file].graphql` — read that file to extract the operation name and field selection for comparison
- If no schema is found — note it and skip GraphQL schema diffing; only collection-level changes are detected

---

## Step 2 — Diff

**Pass 1 — match by name** (exact, case-sensitive):
- In both → potential update
- Only in collection → `added`
- Only in existing → `removed`

**Pass 2 — match remaining by (method, endpoint)**:
- Normalise: `null` method = `"GET"`, `null` type = `"rest"`
- Match found → treat as rename (update name from collection, preserve all user-owned fields)

**Pass 3 — GraphQL schema diff** (only if schema was found in Step 1):

For each matched GraphQL probe, compare against the parsed schema:

| What to check | How to detect | Action |
|---|---|---|
| Required variable added (`Arg!` now non-null) | Arg present in schema with `!`, missing from probe `variables:` | Flag `updated` — add `# SYNC: new required variable [VAR_NAME] ([Type]!)` |
| Required variable removed or renamed | Arg no longer in schema operation signature | Flag `updated` — add `# SYNC: variable [VAR_NAME] removed from schema` |
| Variable type changed | Schema arg type differs from probe | Flag `updated` — add `# SYNC: variable [VAR_NAME] type changed to [NewType]` |
| Non-null return field added to queried type | Schema has new `Field!` not in `!include` query file or inline query | Flag `updated` — add `# SYNC: schema added required field [field] — update your query/validation` |
| Operation removed from schema | Query/mutation no longer exists | Classify as `removed` |
| Query param added/removed (REST) | Endpoint URL or OpenAPI `parameters` changed | Flag `updated` via endpoint or headers diff |

For `!include`-protected queries (`query: !include queries/[file].graphql`): read the `.graphql` file, extract field selection, diff against schema. Do not modify the `!include` reference — only add a `# SYNC:` comment describing what changed so the developer can update the file manually.

Classify each probe: `added` | `updated` | `removed` | `unchanged`

---

## Step 3 — Merge

```
UPDATED probe  = sync-owned fields from collection + user-owned fields from existing (unchanged)
ADDED probe    = collection probe + placeholder validation comment
REMOVED probe  = keep in file, mark with # SYNC: removed comment
```

For `!include`-protected fields: copy the existing `!include` reference as-is. Do not expand or replace it.

Order: existing order preserved → removed probes marked in place → added probes appended at end.

---

## Step 4 — Apply DAG to added probes only

Run DAG detection on added probes only (same logic as `/api-probe:generate` Phase 4 DAG ordering).
Insert new probes in dependency order relative to existing probes.
Do **not** reorder existing probes.

---

## Step 5 — Executions block

- Add new environment variables found in collection but not in existing executions
- Never remove or overwrite existing variable values
- If an execution uses `validations: !include validations/[env].yaml` → preserve that line exactly, do not replace with inline validations
- Add new execution entries only if collection defines environments not already present

---

## Step 6 — Update config.yaml (multi-file safe)

When writing back to `.api-probe/config.yaml` after a sync:
- Load the full existing config
- Update only the entry for the file that was just synced
- Preserve all other `probes:` entries exactly as-is — never rewrite the entire list

```yaml
# Before sync (two files):
probes:
  - api-probe/orders/probes.yaml
  - api-probe/products/probes.yaml

# After syncing only orders/probes.yaml — products reference must survive:
probes:
  - api-probe/orders/probes.yaml   # ← synced
  - api-probe/products/probes.yaml # ← untouched
```

If the config uses a single-path string and the synced file matches — leave the format as a string (do not convert to a list).

---

## Step 7 — Emit with inline comments

```yaml
  # SYNC: endpoint updated from /user/${ID}
  - name: "Get User"
    type: rest
    endpoint: "${BASE_URL}/accounts/${USER_ID}"   # ← updated
    method: GET
    validation:                                    # ← preserved
      status: 200
      body:
        present: ["id", "email"]

  # SYNC: body updated — !include reference preserved
  - name: "Create Order"
    type: rest
    endpoint: "${BASE_URL}/orders"
    method: POST
    body: !include includes/create-order.json     # ← preserved
    validation: !include validations/create-order.yaml  # ← preserved

  # SYNC: removed from collection — delete if no longer needed
  - name: "Legacy Endpoint"
    ...

  # SYNC: added — review and add validation
  - name: "New Endpoint"
    ...
    validation:
      status: "2xx"
      # TODO: add body assertions after testing

  # SYNC: new required variable customerId (String!) — add to variables block
  # SYNC: schema added required field data.order.trackingId — update queries/create-order.graphql and validation
  - name: "Create Order (GraphQL)"
    type: graphql
    endpoint: "${BASE_URL}/graphql"
    query: !include queries/create-order.graphql   # ← update this file manually
    variables:
      # TODO: add customerId: "${CUSTOMER_ID}"
    validation: !include validations/create-order.yaml  # ← preserved
```

---

## Check mode

If user asks to **check for drift only** (no file changes):
- Output a diff summary: probe name, what changed (endpoint, method, headers, body, GraphQL variables, schema fields)
- "✓ in sync" or "✗ X probes drifted — run /api-probe:sync to update"
- Do not modify any files

---

After writing changes, always append:

> 📄 **Schema reference:** https://github.com/hemantobora/api-probe/blob/main/docs/SCHEMA_SPECIFICATION.md
