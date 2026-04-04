---
description: Sync an existing probes.yaml with an updated API collection (Postman, Bruno, Insomnia, OpenAPI, HAR) — preserving all developer-written validation
---

Sync an existing `api-probe/probes.yaml` with an updated API collection, preserving all developer-written validation.

---

## Ownership model (critical)

| Owner | Fields | Rule |
|-------|--------|------|
| **Sync-owned** (from collection) | `name`, `type`, `endpoint`, `method`, `headers`, `body` | Always update from collection |
| **User-owned** (from developer) | `validation`, `output`, `ignore`, `delay`, `timeout`, `retry`, `debug`, `verify` | Never overwrite |

---

## Step 1 — Parse both inputs

Parse the collection file (same format detection as `/api-probe:generate` Step 2).
Parse the existing `probes.yaml`.

---

## Step 2 — Diff

**Pass 1 — match by name** (exact):
- In both → potential update
- Only in collection → `added`
- Only in existing → `removed`

**Pass 2 — match remaining by (method, endpoint)**:
- Normalise: `null` method = `"GET"`, `null` type = `"rest"`
- Match found → treat as rename (name updated, user-owned fields preserved)

Classify each probe: `added` | `updated` | `removed` | `unchanged`

---

## Step 3 — Merge

```
UPDATED probe  = sync fields from collection + user fields from existing
ADDED probe    = collection probe + placeholder validation comment
REMOVED probe  = keep in file with # SYNC: removed comment
```

Order: existing order → removed probes marked in place → added probes appended at end.

---

## Step 4 — Apply DAG to added probes only

Run DAG detection (from `/api-probe-generate` Step 4) on added probes only.
Insert new probes in dependency order relative to existing probes.
Do NOT reorder existing probes.

---

## Step 5 — Executions block

- Add new environment variables from collection
- Never remove or overwrite existing variable values
- Add new environment entries if collection has more envs

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
- Output diff summary only
- "✓ in sync" or "✗ X probes drifted — run /api-probe:sync to update"
