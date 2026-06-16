# Source parsing reference

Detail for Phase 2 of the generate skill: how to locate routes in a codebase, how to detect a collection's format, and how to classify auth.

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

## 2d — Auth classification

| Type | Signals | How to probe |
|---|---|---|
| User token | Login endpoint (`/auth/login`, `/token`, `/signin`), returns JWT or session | Auth probe first → capture `TOKEN`, use as `Bearer ${TOKEN}` |
| Service token / API key | `X-API-Key`, `Authorization: ApiKey`, env var like `API_KEY`, no login endpoint | No auth probe needed — use `${API_KEY}` directly in headers |
| Mixed | Some endpoints need user token, others just API key | Auth probe for user-protected endpoints only |
| No auth | All endpoints public | No auth headers |
