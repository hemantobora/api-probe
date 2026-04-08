---
name: api-probe:generate
description: Generate api-probe YAML probe files by scanning the codebase or from a collection file (Postman, Bruno, Insomnia, OpenAPI, HAR, curl)
---

Generate an api-probe YAML probe file for this project.

**Global rules — check on every user message:**
- If the user says **stop**, **exit**, or **terminate** at any point, stop immediately. Do not generate any YAML. Acknowledge and exit.
- If the user says **continue** or **resume** and the last thing you asked was a question, **re-ask that exact question** — do not assume it was answered or skip it.
- Do not generate any YAML until Phase 3 is complete and the user has answered all relevant questions.
- Do not make assumptions about API endpoints — always verify from the codebase or provided sources.
- Never ask the user to reply with numbers. Always present visual lists or checkbox tables and accept natural language responses.

---

# Phase 1 — Understand inputs

Determine what source materials to use. Follow the decision tree exactly — do not ask unnecessary questions.

## Decision tree

### A — Nothing provided
Silently begin a codebase scan (Phase 2a). Do not ask the user anything yet.
- If endpoints are found → proceed to Phase 2, then Phase 3
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

- If yes → run Phase 2a (codebase scan) after Phase 2b
- If no → proceed with Phase 2b results only

### C — Appending to existing probes
If the user mentions adding probes to an existing file, check `.api-probe/config.yaml` for the file location and treat this as an append workflow — generate new probes only, merge with existing, preserve all existing content.

---

# Phase 2 — Analyze

Silently build a complete picture from all confirmed source materials using `@workspace` for codebase. Do not output findings yet.

## 2a — Codebase scan (if included)

Identify the framework and find all routes:

| Project type | Framework signals | Where to find routes |
|---|---|---|
| Node.js | `express`, `fastify`, `nestjs`, `koa` in package.json | `routes/`, `controllers/`, `src/`, `@Controller` decorators |
| Python | `fastapi`, `flask`, `django` in requirements/pyproject | `routers/`, `views.py`, `@app.route`, `@router.get` |
| Java / Spring Boot | `spring-boot` in pom.xml / build.gradle | `@RestController`, `@RequestMapping`, `@GetMapping` etc. |
| Java / MicroProfile | `microprofile`, `quarkus` in pom.xml / build.gradle | `@Path`, `@GET`, `@POST`, JAX-RS annotations |
| Java / Quarkus | `quarkus` in pom.xml | `@Path`, `@GET`, `@POST`, Quarkus REST annotations, `application.properties` |
| Go | `gin`, `chi`, `echo`, `fiber` in go.mod | `router.GET`, `r.Handle`, route group definitions |
| .NET | `Microsoft.AspNetCore` in .csproj | `[ApiController]`, `[HttpGet]`, `MapGet` |
| Ruby | `rails`, `sinatra` in Gemfile | `routes.rb`, `config/routes.rb` |
| PHP | `laravel`, `symfony` in composer.json | `routes/api.php`, `#[Route]` |
| AWS Lambda | `serverless.yml`, `template.yaml` (SAM), `handler.js/py` | `functions:` block in serverless.yml, `Events.Api` in SAM |
| Azure Functions | `function.json`, `host.json` | `bindings` with `httpTrigger`, route in `function.json` |
| GCP Functions | `index.js/py` exported functions, `functions-framework` | Exported HTTP handler functions |

## 2b — Collection / HAR parsing (if provided)

| Input | Format |
|-------|--------|
| JSON with `info.schema` containing `"postman-collection"` | Postman |
| JSON with `_type: "export"` and `__export_format` | Insomnia |
| JSON/YAML with `openapi` or `swagger` key | OpenAPI / Swagger |
| JSON with `log.entries` and `log.version` | HAR |
| `.bru` file or directory of `.bru` files | Bruno |
| curl commands | Parse each curl |

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

**Auth type:**

| Type | Signals | How to probe |
|---|---|---|
| User token | Login endpoint (`/auth/login`, `/token`, `/signin`), returns JWT or session | Auth probe first → capture `TOKEN`, use as `Bearer ${TOKEN}` |
| Service token / API key | `X-API-Key`, `Authorization: ApiKey`, env var like `API_KEY`, no login endpoint | No auth probe needed — use `${API_KEY}` directly in headers |
| Mixed | Some endpoints need user token, others just API key | Auth probe for user-protected endpoints only |
| No auth | All endpoints public | No auth headers |

**Dependencies:**
- Which endpoints use a resource ID produced by another
- Confidence: HIGH (clear `${ID}` chain) or LOW (inferred from shared noun)

**Grouping signals:**
- **Parallel candidates** (flat group): endpoints that share no variables and can run simultaneously
- **Parallel workflow candidates** (staged group): two or more independent chains each needing their own auth + sequence
- **Dependency chains**: must stay sequential — variables flow naturally without grouping

**Existing probe config:**
- Check `.api-probe/config.yaml` for previously saved output location

---

# Phase 3 — Questions

Present a short summary (endpoint count, auth type, API type, any grouping opportunities), then work through the questions below **one at a time**, in order.

**Important rules for this phase:**
- The Q1, Q2… labels below are internal sequencing only — never show them in your responses to the user.
- Before asking any question, check whether the user already provided that information — in their initial prompt or earlier in the conversation. If yes, skip it silently.
- Ask only one question per message. Wait for a response before continuing.
- If the user says **continue** or **resume** without answering, re-ask the same question.

---

## Q1 — Endpoint selection
*Ask if more than one endpoint was found.*

First ask whether to proceed with all endpoints or make a selection:

> "I found X endpoints. Would you like to proceed with all of them, or select specific ones?"

If the user wants to select: present all endpoints as a multi-select list using the best mechanism available in the current environment — native VS Code QuickPick if in agent mode, or a structured table otherwise. Include method, type (REST/GraphQL), and path/operation name for each item. All items pre-selected by default.

Also accept natural language alongside or instead of selection — e.g. "skip the health check", "only the REST ones", "leave out GraphQL". Resolve descriptions to specific endpoints yourself without asking for numbered confirmation.

---

## Q2 — Uncertain dependencies
*Ask for each LOW-confidence dependency.*

> "I think [GET /orders/{id}] depends on [POST /orders] to create the order ID first, but I'm not certain. Should I treat these as dependent?"

Ask separately for each. Do not batch.

---

## Q3 — Auth
*Ask if auth type is ambiguous or missing.*

If no auth found but endpoints seem protected:
> "I couldn't detect an auth mechanism. Is authentication required? If so — is it a user login (returns a token) or a service/API key in headers or environment variables?"

If API key detected:
> "I found what looks like an API key (`X-Api-Key` / `API_KEY`). Should I use `${API_KEY}` as a header, or is there a login step first?"

If auth endpoint found but excluded from Q1 selection:
> "I found a login endpoint outside your selection. Should I include it anyway since other probes depend on the token it produces?"

---

## Q4 — Output location
*Always ask.*

> "Where should I save the probe file?
>
> ▸ Default — `api-probe/probes.yaml`
> ▸ Custom location"

If custom: ask for the path. Save to `.api-probe/config.yaml`.

---

## Q5 — Executions
*Always ask.*

> "Would you like to run probes in a single execution or multiple executions? An execution is a sandboxed running context with its own variables.
>
> ▸ Single execution
> ▸ Multiple executions (e.g. staging + production, or multiple tenants)"

If multiple: ask how many, what to name each, and their base URLs.

---

## Q6 — Validation review
*Always ask — this is the most important question before generating.*

By this point you have analysed the codebase and/or collection. Present a concrete per-probe validation plan — what you intend to generate — and ask the user to confirm, adjust, or add to it. Do not ask an open-ended question. Show your work:

```
Here's the validation I plan to generate for each probe:

**GET /orders/{id}**
- status: 200
- body.present: id, status, items, total
- body.absent: internalCost, debug (marked internal in code)
- body.type: total → number, items → array

**POST /orders**
- status: 201
- body.present: id, status
- body.equals: status → "pending"

**createOrder (GraphQL)**
- status: 200
- body.present: data.createOrder.id, data.createOrder.status
- body.absent: errors

Anything to add, change, or correct? For example:
- A field that should always be absent (sensitive/internal)
- A known expected value for a specific field
- A response time requirement for a particular probe
- A field whose type you want asserted
```

Wait for the user's response before generating. If they say "looks good" or "proceed", use the plan as-is.

---

## Q7 — Execution-specific validation differences
*Ask only if Q5 = multiple executions.*

Based on Q6's validated plan, ask what — if anything — differs between executions:

```
You have X executions: [list them]. Should the validation differ between them?

For example:
- Stricter response time in production
- Additional field checks in one environment
- Relaxed status codes in staging (e.g. 2xx instead of 200)

Or are the same validation rules fine for all executions?
```

If differences exist: generate a separate `validations/[env].yaml` per execution and wire with `validations: !include validations/[env].yaml`. This is a **total replacement per probe** — probes not listed fall back to their inline `validation:`.

---

## Q8 — Any other constraints
*Always ask last.*

> "Anything else before I generate? For example: endpoints to skip, known slow endpoints, retry behaviour."

---

# Phase 4 — Generate

Only after all relevant questions are answered.

## Probe naming

Use meaningful names from HTTP method, path, and business context:

| Instead of | Use |
|---|---|
| `GET /users/{id}` | `"Get User by ID"` |
| `POST /orders` | `"Create Order"` |
| `DELETE /sessions/{id}` | `"Logout"` |
| `GET /products?category=X` | `"List Products by Category"` |
| `mutation CreatePost` | `"Create Post (GraphQL)"` |

## GraphQL probes

For every GraphQL query or mutation:

- **Be exhaustive** — include every field visible in the response type from the schema or introspection. Do not omit nested fields.
- **Queries** → `validation.body.present` lists all expected `data.*` fields; `absent: ["errors"]`
- **Mutations** → validate both the returned payload fields AND the absence of `errors`
- **Use `body.type`** for known scalar types (`String`, `Int`, `Boolean`, etc.)
- **Externalise the query** with `query: !include queries/[operation-name].graphql` — do not inline long queries

After generating GraphQL probes, add this comment block in the YAML:

```yaml
# ⚠️  GraphQL review required:
#    - Verify field selections match your actual schema
#    - Add variables for any dynamic inputs
#    - Confirm mutation side-effects are testable via follow-up queries
```

## DAG ordering

1. Auth probe first (user token type only) → `output: { TOKEN: "access_token" }`
2. Resource-creating POSTs → `output: { RESOURCE_ID: "id" }`
3. Remaining in dependency order by `${VAR}` usage
4. Add `ignore: "empty(RESOURCE_ID)"` to probes depending on a variable that may not be set

## Grouping

Only apply when it genuinely fits the schema semantics.

**Flat group** — parallel probes, shared scope. All run simultaneously. Use when probes have no inter-dependencies:
```yaml
- group:
    name: "Independent Checks"
    probes:
      - name: "Health Check"
        ...
      - name: "Get API Version"
        ...
```

**Staged group** — parallel isolated workflows. Stages run simultaneously, probes within each stage run sequentially, each stage has isolated variable scope. Use when running the same flow for multiple independent users/tenants/regions:
```yaml
- group:
    name: "Parallel Tenant Flows"
    stages:
      - name: "Tenant A"
        probes:
          - name: "Login - Tenant A"
            output:
              TOKEN_A: "access_token"
          - name: "Create Order - Tenant A"
            headers:
              Authorization: "Bearer ${TOKEN_A}"
      - name: "Tenant B"
        probes:
          - name: "Login - Tenant B"
            output:
              TOKEN_B: "access_token"
          - name: "Create Order - Tenant B"
            headers:
              Authorization: "Bearer ${TOKEN_B}"
```

**No grouping** — for single dependency chains, list flat in order.

## Per-probe validation

For every probe, derive validation individually from its response schema. Do not apply one rule set to all probes.

Apply **all validators that are supported by the known response shape**:

| Validator | When to apply |
|---|---|
| `status` | Always — every probe must have this |
| `response_time` | Only if user specified in Q7/Q8 or SLA is in code |
| `body.present` | Fields that must exist — from DTOs, response models, or examples |
| `body.absent` | Sensitive/internal fields that must NOT appear (password, secret, debug, internal_id, stack_trace) |
| `body.equals` | Known specific values (e.g. `status: "active"`, `enabled: true`) |
| `body.type` | Type assertions for key fields from response schema |
| `body.matches` | Regex for fields with known patterns (UUID, email, ISO date) |
| `body.contains` | Substring or array element checks where applicable |
| `body.length` | Array responses where min/max count is known |
| `body.range` | Numeric fields with known bounds |

Example of a richly validated probe:
```yaml
- name: "Get Order"
  type: rest
  endpoint: "${BASE_URL}/orders/${ORDER_ID}"
  method: GET
  headers:
    Authorization: "Bearer ${TOKEN}"
  validation:
    status: 200
    body:
      present:
        - "id"
        - "status"
        - "items"
        - "total"
      absent:
        - "internalCost"
        - "debug"
      equals:
        id: "${ORDER_ID}"
      type:
        id: string
        total: number
        items: array
      length:
        items: [1, null]    # at least 1 item
```

If a field's value or type is unknown: include `present` only and add `# TODO: add type/equals after first test run`.

## Externalise large bodies and validations with `!include`

Prefer `!include` over inline content whenever a body or validation block would be large. `!include` is a first-class api-probe feature — paths are relative to the probe file.

**Request body > 5 fields** → external file:
```yaml
# probes.yaml
probes:
  - name: "Create Order"
    type: rest
    endpoint: "${BASE_URL}/orders"
    method: POST
    headers:
      Content-Type: "application/json"
    body: !include includes/create-order.json
    validation:
      status: 201
```
```json
// includes/create-order.json — variables ARE substituted at runtime
{
  "customerId": "${USER_ID}",
  "items": [{ "sku": "ITEM-001", "qty": 2 }],
  "shippingAddress": { "line1": "123 Main St", "city": "Austin", "zip": "78701" }
}
```

**GraphQL query** → always externalise:
```yaml
- name: "Search Products"
  type: graphql
  query: !include queries/search-products.graphql
  variables:
    category: "${CATEGORY}"
```

**Probe-level validation > 10 assertions** → external file:
```yaml
- name: "Create Order"
  validation: !include validations/create-order.yaml
```

**YAML anchors** are acceptable for small inline reuse (e.g. a shared header block). Prefer `!include` for anything that would make the probe file hard to read.

## Infer optional probe fields

**retry** — for async/long-running endpoints:
```yaml
retry:
  max_attempts: 3
  delay: 2        # seconds between retries
```

**delay** — after probes triggering async work:
```yaml
delay: 1    # seconds to wait before executing this probe
```

## Emit YAML

Save to the location confirmed in Q4. Create the directory if needed.

Write to `.api-probe/config.yaml`:
```yaml
probes: api-probe/probes.yaml
```

## Quality checklist

- [ ] Auth probe is first (user token type only)
- [ ] No `${VAR}` used before it is produced
- [ ] Every probe has `name`, `type`, `endpoint`, `method`, `validation.status`
- [ ] Names are meaningful — no raw paths
- [ ] Validation is per-probe, derived from individual response schema
- [ ] All applicable validators used per probe (present, absent, equals, type, etc.)
- [ ] `response_time` only where explicitly known
- [ ] Large bodies use `!include` (not inline)
- [ ] Large probe validations use `!include` (not inline)
- [ ] Per-execution validation overrides use `validations: !include validations/[env].yaml`
- [ ] Grouping applied only where it fits schema semantics
- [ ] Dependency chains are flat sequential — never in a staged group
- [ ] POST/PUT/PATCH probes with body include `Content-Type` header
- [ ] `retry` / `delay` / `ignore` added where applicable
- [ ] No duplicate probe names
- [ ] `.api-probe/config.yaml` written with output path
- [ ] YAML is valid

---

After outputting the YAML, always append:

> 📄 **Schema reference:** https://github.com/hemantobora/api-probe/blob/main/docs/SCHEMA_SPECIFICATION.md
