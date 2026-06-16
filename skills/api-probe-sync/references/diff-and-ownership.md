# Ownership & diff reference

Detail for Steps "Ownership model" and Step 2 of the sync skill.

## Ownership model

| Owner | Fields | Rule |
|-------|--------|------|
| **Sync-owned** (from collection) | `name`, `type`, `endpoint`, `method`, `headers`, `body` | Always update from collection |
| **User-owned** (from developer) | `validation`, `output`, `ignore`, `delay`, `timeout`, `retry`, `debug`, `verify` | Never overwrite — preserve exactly as-is |

**`!include` is user-owned.** If any field uses `!include` — whether `body`, `validation`, or `variables` — treat the entire field as user-owned and do not replace it with inline content. Preserve the `!include` reference exactly.

## Step 2 — Diff passes

**Pass 1 — match by name** (exact, case-sensitive):
- In both → potential update
- Only in collection → `added`
- Only in existing → `removed`

**Pass 2 — match remaining by (method, endpoint):**
- Normalise: `null` method = `"GET"`, `null` type = `"rest"`
- Match found → treat as rename (update name from collection, preserve all user-owned fields)

**Pass 3 — GraphQL schema diff** (only if a schema was found in Step 1):

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

Classify each probe: `added` | `updated` | `removed` | `unchanged`.
