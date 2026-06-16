# Validation, grouping & emit reference

Detail for Phase 4 of the generate skill.

## Per-probe validation

For every probe, derive validation individually from its response schema. Do not apply one rule set to all probes. Apply **all validators supported by the known response shape**:

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

Richly validated example:
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

## Grouping

Only apply when it genuinely fits the schema semantics.

**Flat group** — parallel probes, shared scope, all run simultaneously. Use when probes have no inter-dependencies:
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

## DAG ordering

1. Auth probe first (user token type only) → `output: { TOKEN: "access_token" }`
2. Resource-creating POSTs → `output: { RESOURCE_ID: "id" }`
3. Remaining in dependency order by `${VAR}` usage
4. Add `ignore: "empty(RESOURCE_ID)"` to probes depending on a variable that may not be set

Dependency chains stay flat sequential — never wrap them in a staged group.

## Infer optional probe fields

**retry** — for async/long-running endpoints (signals: async handlers, `/generate|export|report|process|batch` in path):
```yaml
retry:
  max_attempts: 3
  delay: 2        # seconds between retries
```

**delay** — after probes triggering async work:
```yaml
delay: 1    # seconds to wait before executing this probe
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
