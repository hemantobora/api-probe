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

Parse the collection file (same format detection as `/api-probe:generate` Phase 2b).
Parse the existing probe file at the resolved path.

Note any probes that use `!include` for body or validation — these are flagged as `!include`-protected and their referenced fields will never be touched.

---

## Step 2 — Diff

**Pass 1 — match by name** (exact, case-sensitive):
- In both → potential update
- Only in collection → `added`
- Only in existing → `removed`

**Pass 2 — match remaining by (method, endpoint)**:
- Normalise: `null` method = `"GET"`, `null` type = `"rest"`
- Match found → treat as rename (update name from collection, preserve all user-owned fields)

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

## Step 6 — Emit with inline comments

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
```

---

## Check mode

If user asks to **check for drift only** (no file changes):
- Output a diff summary: probe name, what changed (endpoint, method, headers, body)
- "✓ in sync" or "✗ X probes drifted — run /api-probe:sync to update"
- Do not modify any files

---

After writing changes, always append:

> 📄 **Schema reference:** https://github.com/hemantobora/api-probe/blob/main/docs/SCHEMA_SPECIFICATION.md
