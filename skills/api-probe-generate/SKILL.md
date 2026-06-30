---
name: api-probe-generate
description: Generate api-probe YAML probe files for testing HTTP and GraphQL APIs. Use when the user asks to "generate probes", "create api-probe tests", "set up API testing", or wants probes built from a codebase scan, a Postman/Bruno/Insomnia/OpenAPI/HAR collection, curl commands, or a plain-English description of endpoints.
metadata:
  author: hemantobora
  version: 0.1.0
  category: API Testing
  tags: [api-probe, generate, yaml, testing]
---

# api-probe: Generate

Generate an api-probe YAML probe file for this project. Work through the phases in order. Reach for the bundled references only when a phase needs the detail they hold — do not inline them here.

## Global rules — check on every user message

- If the user says **stop**, **exit**, or **terminate** at any point, stop immediately. Do not generate any YAML. Acknowledge and exit.
- If the user says **continue** or **resume** and the last thing you asked was a question, **re-ask that exact question** — do not assume it was answered or skip it.
- Do not generate any YAML until Phase 3 is complete and the user has answered all relevant questions.
- Do not make assumptions about API endpoints — always verify from the codebase or provided sources.
- Never ask the user to reply with numbers. Always present visual lists or checkbox tables and accept natural language responses.

---

# Phase 1 — Understand inputs

Determine what source materials to use. Follow the decision tree exactly — do not ask unnecessary questions.

### A — Nothing provided
Silently begin a codebase scan (Phase 2a). Do not ask the user anything yet.
- If endpoints are found → proceed to Phase 2, then Phase 3.
- If **no endpoints are found** → tell the user, then ask:

  > "I couldn't find any API endpoints in the codebase. Do you have any of the following?
  >
  > ▸ A collection file (Postman, Bruno, Insomnia, OpenAPI/Swagger)
  > ▸ A HAR file
  > ▸ curl commands (paste them here)
  > ▸ A plain description of the endpoints"

  Wait for input, then parse and continue.

### B — Collection file, HAR, curl, or OpenAPI provided
Parse the provided input first (Phase 2b).

**If the parsed input contains ONLY auth-related endpoints** (paths matching `/auth`, `/login`, `/token`, `/signin`, `/oauth`, `/session`, `/authenticate`) — auto-scan the codebase without asking. The user is providing auth context, not defining the full endpoint set. Proceed directly to Phase 2a + 2b combined.

**Otherwise** ask:

> "Got it — I'll use the [collection / HAR / curl / spec] you provided.
> Would you also like me to scan the project codebase to enrich the probes with response schemas, auth patterns, and validation context?"
>
> ▸ Yes, scan the project too
> ▸ No, use only what I provided

- If yes → run Phase 2a (codebase scan) after Phase 2b.
- If no → proceed with Phase 2b results only.

### C — Appending to existing probes
If the user mentions adding probes to an existing file, check `.api-probe/config.yaml` for the file location and treat this as an append workflow — generate new probes only, merge with existing, preserve all existing content.

---

# Phase 2 — Analyze

Silently build a complete picture from all confirmed source materials. Use the richest codebase-navigation mechanism your environment supports. Do not output findings yet.

**For framework/route detection (2a) and collection/HAR/curl format detection (2b), consult [`references/source-parsing.md`](references/source-parsing.md)** — it holds the per-language route-location table and the collection-format signatures.

## 2c — For each endpoint, collect
- HTTP method and path
- Path params, query params
- Request body shape (field names, types, nesting depth)
- Response shape (field names, types, nesting — from DTOs, response models, schema, or examples)
- Which fields are required vs optional
- Which fields are sensitive (password, secret, token, internal_id) — note for `absent` validation
- Auth middleware or guards applied
- Whether async, long-running, or triggers background work
- Any SLA / timeout config

## 2d — Detect patterns

**Auth type** — classify as one of: user token (login endpoint returns JWT/session → auth probe first, capture `TOKEN`), service token / API key (`X-API-Key` or env var, no login → use `${API_KEY}` directly), mixed, or no auth. Full signal table in [`references/source-parsing.md`](references/source-parsing.md).

**Dependencies:** which endpoints consume a resource ID produced by another. Mark confidence HIGH (clear `${ID}` chain) or LOW (inferred from a shared noun).

**Grouping signals:** parallel candidates (flat group, no shared variables), parallel workflow candidates (staged group, independent chains each with own auth), and dependency chains (stay sequential).

**Existing config:** check `.api-probe/config.yaml` for a previously saved output location.

---

# Phase 3 — Questions

Present a short summary (endpoint count, auth type, API type, any grouping opportunities), then work through the questions below **one at a time**, in order.

- The Q1, Q2… labels are internal sequencing only — never show them to the user.
- Before asking any question, check whether the user already answered it earlier. If so, skip it silently.
- Ask only one question per message. Wait for a response before continuing.
- If the user says **continue** or **resume** without answering, re-ask the same question.

**Use the host's native question UI when it offers one.** These questions are about *intent*, not *presentation* — render each one with the richest input mechanism the environment actually exposes, and fall back to plain text otherwise. You can't draw UI yourself; you can only use what the host provides. In rough order of preference:

- A **structured question / choice tool** (e.g. a multiple-choice prompt that returns the user's pick) — ideal for the single-answer questions (auth type in Q3, single-vs-multiple executions in Q5). Use it when the host exposes one.
- A **multi-select picker** (e.g. VS Code QuickPick) — ideal for endpoint selection in Q1.
- A **confirmation prompt** (proceed / cancel) — fine for yes/no gates.
- **Plain text** — the universal fallback. Always works; use it when none of the above exist, and never fake a clickable control in plain text.

This keeps the skill portable: the same questions surface as slick widgets in a capable host (Cowork's question card, VS Code's pickers) and as readable prose everywhere else.

### Q1 — Endpoint selection
*Ask only if more than one endpoint was found.* First ask whether to proceed with everything or pick a subset:

> "I found {N} endpoints. Proceed with all of them, or select a subset?"

If they want all → continue to Q2. If they want to select, present the endpoints (method, type REST/GraphQL, path/operation) using whichever of these fits the environment:

- **Interactive multi-select UI available** (e.g. VS Code QuickPick): list the endpoints in it, all pre-selected, and let the UI handle selection. Paginate **only if the UI itself caps how many items it can show** — otherwise show them all in one view. Do not also render a text table.
- **Plain chat (no interactive UI):** render the **full** list once as a plain table — **no checkbox glyphs**, since a chat list is not clickable and ☑ would falsely imply it is. Make clear the choice is made in words. Do not paginate.

  ```
  I found {N} endpoints (all included unless you tell me otherwise):

  | Type      | Endpoint / Operation  |
  |-----------|-----------------------|
  | REST GET  | /orders/{id}          |
  | REST POST | /orders               |
  | GraphQL   | createOrder mutation  |
  | GraphQL   | getProduct query      |

  Tell me what to leave out in plain language, or say "all good" to keep them all.
  ```

Accept natural language in either mode ("skip the health check", "only the REST ones", "leave out GraphQL") and resolve it to specific endpoints yourself — never ask for numbered confirmation.

### Q2 — Uncertain dependencies
*Ask separately for each LOW-confidence dependency. Do not batch.*
> "I think [GET /orders/{id}] depends on [POST /orders] to create the order ID first, but I'm not certain. Should I treat these as dependent?"

### Q3 — Auth
*Ask only if auth type is ambiguous or missing.*
- No auth found but endpoints seem protected → ask whether auth is required and whether it's a user login (returns a token) or a service/API key.
- API key detected → confirm whether to use `${API_KEY}` as a header or there's a login step first.
- Auth endpoint found but excluded in Q1 → ask whether to include it anyway since other probes depend on its token.

### Q4 — Output location
*Always ask.*
> "Where should I save the probe file?
> ▸ Default — `api-probe/probes.yaml`
> ▸ Custom location"

If custom, ask for the path. Save the choice to `.api-probe/config.yaml`.

### Q5 — Executions
*Always ask.*
> "Should these probes run once, or repeat under multiple execution contexts? An execution is an isolated run with its own variables — its primary use is exercising the *same* endpoints as different **users / accounts / tenants** (e.g. an admin vs a basic user, customer A vs customer B), to confirm the API behaves correctly for each. Differing environments like staging vs production is technically possible, but it's the weaker use — comparing responses across environments rarely tells you much.
> ▸ Single run
> ▸ Multiple execution contexts (different users, accounts, or tenants)"

If multiple, ask how many, what to name each, and **which variables differ per context** (user ID, account, API key/token). A base URL can be one of those variables if it genuinely differs, but it isn't the point — the value is the same endpoints under different identities/data.

### Q6 — Validation review
*Always ask — this is the most important question before generating.* Present a concrete per-probe validation plan and ask the user to confirm, adjust, or add. Do not ask open-ended — show your work. Crucially, go beyond `status`/`present`/`type`: surface the **value-level assertions** (`equals`, `matches`, `range`, `length`, `contains`) that make api-probe worth running, including the best-guess ones you've inferred from the code and intend to emit commented-out for the user to confirm. See [`references/validation.md`](references/validation.md) for the catalogue, the value-level scaffolding guidance, and worked examples. Wait for the response before generating; "looks good" / "proceed" means use the plan as-is.

### Q7 — Context-specific validation differences
*Ask only if Q5 = multiple execution contexts.* Ask whether the **expected response differs per context** — this is where contexts pay off: same probe, context-specific assertions. Examples: an admin context returns extra fields a basic user must not see; user A's response must contain A's own ID/email, not B's; a premium tenant has a higher rate-limit or quota field. If differences exist, generate a separate `validations/[context].yaml` per execution and wire with `validations: !include validations/[context].yaml` — a total replacement per probe; unlisted probes fall back to inline `validation:`.

### Q8 — Any other constraints
*Always ask last.*
> "Anything else before I generate? For example: endpoints to skip, known slow endpoints, retry behaviour."

---

# Phase 4 — Generate

Only after all relevant questions are answered. **Consult [`references/validation.md`](references/validation.md)** for the full validator catalogue, the richly-validated probe example, `!include` externalisation rules, grouping patterns, DAG ordering, optional fields (`retry`/`delay`/`ignore`), and the pre-flight quality checklist.

## Pattern library

Before emitting, look at the closest match in [`references/examples/`](references/examples/) (see its `INDEX.md`) for the canonical **shape** of the feature you're generating — REST, GraphQL, flat/staged groups, multiple executions, `!include` bodies, SOAP/XML, or rich validation. If the project being probed has its own `examples/` directory of api-probe probes, prefer those as the more current reference.

**Use examples for structure only — never copy their content.** Endpoints, hostnames, request bodies, and expected values in the examples (e.g. `httpbin.org`, `countries.trevorblades.com`, sample IDs) are placeholders. Every real value in the generated probes must come from the user's actual API, codebase, or collection — match the YAML shape, not the data.

## Probe naming
Use meaningful names from method, path, and business context — never raw paths. `GET /users/{id}` → `"Get User by ID"`; `POST /orders` → `"Create Order"`; `DELETE /sessions/{id}` → `"Logout"`; `mutation CreatePost` → `"Create Post (GraphQL)"`.

## GraphQL probes
For every query/mutation: be exhaustive (include every field in the response type from schema/introspection). Queries → `body.present` lists all `data.*` fields, `absent: ["errors"]`. Mutations → validate payload fields AND absence of `errors`. Use `body.type` for known scalars. Always externalise the query with `query: !include queries/[operation-name].graphql`. After generating GraphQL probes, add this comment block:

```yaml
# ⚠️  GraphQL review required:
#    - Verify field selections match your actual schema
#    - Add variables for any dynamic inputs
#    - Confirm mutation side-effects are testable via follow-up queries
```

## Emit YAML
Save to the location confirmed in Q4, creating the directory if needed. Write the output path to `.api-probe/config.yaml`:
```yaml
probes: api-probe/probes.yaml
```

Run through the quality checklist in [`references/validation.md`](references/validation.md) before finalising.

---

After outputting the YAML, always append:

> 📄 **Schema reference:** https://github.com/hemantobora/api-probe/blob/main/docs/SCHEMA_SPECIFICATION.md
