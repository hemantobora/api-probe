---
description: Generate api-probe YAML probe files by scanning the codebase or from a collection file (Postman, Bruno, Insomnia, OpenAPI, HAR, curl)
---

Generate an api-probe YAML probe file for this project.

**Important:** Do not generate any YAML until Phase 2 is complete and the user has answered all relevant questions.

---

# Phase 1 — Analyze

Use `@workspace` to scan the codebase, or parse the provided collection file. Build a complete internal picture before asking anything. Do not output findings yet — just collect them.

## 1a — Identify the input

### Primary — codebase scan

Identify the framework, then find all routes:

| Project type | Framework signals | Where to find routes |
|---|---|---|
| Node.js | `express`, `fastify`, `nestjs`, `koa` in package.json | `routes/`, `controllers/`, `src/`, `@Controller` decorators |
| Python | `fastapi`, `flask`, `django` in requirements/pyproject | `routers/`, `views.py`, `@app.route`, `@router.get` |
| Java | `spring-boot` in pom.xml / build.gradle | `@RestController`, `@RequestMapping`, `@GetMapping` etc. |
| Go | `gin`, `chi`, `echo`, `fiber` in go.mod | `router.GET`, `r.Handle`, route group definitions |
| .NET | `Microsoft.AspNetCore` in .csproj | `[ApiController]`, `[HttpGet]`, `MapGet` |
| Ruby | `rails`, `sinatra` in Gemfile | `routes.rb`, `config/routes.rb` |
| PHP | `laravel`, `symfony` in composer.json | `routes/api.php`, `#[Route]` |

### Secondary — collection file

| Input | Format |
|-------|--------|
| JSON with `info.schema` containing `"postman-collection"` | Postman |
| JSON with `_type: "export"` and `__export_format` | Insomnia |
| JSON/YAML with `openapi` or `swagger` key | OpenAPI / Swagger |
| JSON with `log.entries` and `log.version` | HAR |
| `.bru` file or directory of `.bru` files | Bruno |
| curl commands | Parse each curl |

## 1b — For each endpoint, collect

- HTTP method and path
- Path params, query params
- Request body shape (field names and types)
- Response shape (field names and types, from DTOs / schema / examples)
- Auth middleware or guards applied
- Whether the endpoint is async, long-running, or triggers background work
- Any SLA / timeout config in the code

## 1c — Detect patterns

**Auth:**
- Look for JWT/OAuth/API key/Basic middleware, guards, or decorators
- Identify which endpoints are protected vs public
- Find the login/token endpoint if present

**Dependencies:**
- Which endpoints use a resource ID produced by another endpoint
- Confidence level: HIGH (clear `${ID}` chain) or LOW (inferred, e.g. path shares a noun with a POST)

**API type:**
- REST, GraphQL, SOAP, or mixed
- For GraphQL: find queries and mutations separately

**Environments:**
- Config files (`.env`, `application.yml`, `config/`, `appsettings.json`)
- How many distinct environments are configured (local, staging, production, etc.)

---

# Phase 2 — Present findings and clarify

Present a short summary of what was found (endpoint count, auth pattern, API type, executions detected), then ask the questions below **one at a time**, in order, skipping any that are not relevant.

If the user already answered a question in their initial prompt (e.g. "probe all endpoints", "no auth needed", "single execution"), skip it and do not ask again.

---

## Q1 — Endpoint selection
*Ask if more than one endpoint was found.*

> "I found X endpoints. Would you like to probe all of them, or only specific ones?"

If the user selects specific ones, show the list and let them choose.

---

## Q2 — Uncertain dependencies
*Ask for each dependency where confidence is LOW.*

> "I think [GET /orders/{id}] depends on [POST /orders] to create the order ID first, but I'm not certain. Should I treat these as dependent — so the create probe runs before the get probe?"

Ask separately for each uncertain dependency. Do not batch them.

---

## Q3 — Auth
*Ask if no auth mechanism was found but one or more endpoints appear to require it (e.g. they return 401 in the schema, or they access user-scoped data).*

> "I couldn't detect an auth mechanism, but some endpoints look like they require authentication. Is there an auth endpoint or token I should include? If so, what type — Bearer token, API key, Basic auth, or something else?"

*Also ask if an auth endpoint was found but it is NOT in the selected set from Q1.*

> "I found a login endpoint [POST /auth/login] but it wasn't in your selection. Should I include it anyway, since other probes depend on the token it produces?"

---

## Q4 — GraphQL validation depth
*Ask only if GraphQL was detected.*

> "For GraphQL probes, how strict should validation be?
> 1. Errors only — check that the response has no `errors` field (fast, works for any query)
> 2. Field presence — also verify that expected fields appear in `data`
> 3. Value matching — also assert specific field values where known"

---

## Q5 — Executions
*Always ask.*

> "Would you like to run probes in a single execution or multiple executions? An execution is a sandbox running context — each one runs probes independently with its own variables.
> 1. Single execution
> 2. Multiple executions"

If multiple: ask how many and what to name each one. Ask for the base URL of each execution, or use any detected from config files and ask the user to confirm.

---

## Q6 — Validation per execution
*Ask only if Q5 = multiple executions.*

> "Would you like to override or separate validation for each execution? For example, stricter response time checks in one execution, or different expected values in another."

If yes: ask the user to describe what differs per execution. Capture these before generating.

---

## Q7 — Any other constraints
*Always ask last, as a catch-all.*

> "Anything else I should know before generating? For example: endpoints to skip, known slow endpoints, specific response time requirements, or retry behaviour."

---

# Phase 3 — Generate

Only after all relevant questions have been answered, generate the YAML.

## Apply DAG ordering

1. Auth endpoint first → add `output: { TOKEN: "access_token", USER_ID: "user.id" }`
2. Resource-creating POSTs next → add `output: { RESOURCE_ID: "id" }`
3. Remaining probes in dependency order by `${VAR}` usage
4. Add `ignore: "empty(RESOURCE_ID)"` to probes that depend on a variable that may not be set

## Infer optional fields

**validation.body.present**
- Use real field names from DTOs / response schema / examples
- If unknown: leave `# TODO: add body.present after first test run`

**validation.response_time**
- Only add if the user specified a requirement in Q7, or if the code has explicit SLA/timeout config
- Never guess

**retry**
Add when endpoint is async or long-running:
```yaml
retry:
  max_attempts: 3
  delay: 2000
```
Signals: async handlers, `/generate|export|report|process|batch` in path, queue consumers

**delay**
Add after probes that trigger async work:
```yaml
delay: 1000   # ms — wait before next probe
```

## Emit YAML

Save as `api-probe/probes.yaml` by default (create the folder if it doesn't exist). Use a different location only if the user specified one in Q7.

```yaml
# Generated by api-probe
# Run:  api-probe run api-probe/probes.yaml
# Sync: api-probe sync <collection-file> api-probe/probes.yaml

executions:
  - name: "Local"
    vars:
      - BASE_URL: "http://localhost:3000"
      - USER_EMAIL: "${USER_EMAIL}"
      - USER_PASSWORD: "${USER_PASSWORD}"

probes:
  - name: "Login"
    type: rest
    endpoint: "${BASE_URL}/auth/login"
    method: POST
    headers:
      Content-Type: "application/json"
    body:
      email: "${USER_EMAIL}"
      password: "${USER_PASSWORD}"
    output:
      TOKEN: "access_token"
      USER_ID: "user.id"
    validation:
      status: 200
      body:
        present: ["access_token", "user.id"]
```

**Rules:**
- Always include `type:`
- Double-quote strings containing `${`
- Uppercase `method:`
- `validation.status` on every probe
- Sensitive values as `${PLACEHOLDER}` — never hardcoded

## Quality check before output

- [ ] Auth probe is first
- [ ] No `${VAR}` used before it is produced
- [ ] Every probe has `name`, `type`, `endpoint`, `method`, `validation.status`
- [ ] `body.present` uses real field names or has a `# TODO`
- [ ] `retry` / `delay` / `ignore` added where applicable
- [ ] `response_time` only where explicitly known
- [ ] No duplicate probe names
- [ ] YAML is valid
