# Architecture Decision Records

These records describe decisions visible in the current implementation. They document the repository as it exists; they are not claims about a deployed system.

## ADR-001: FastAPI for the HTTP API

**Status:** Accepted

**Context:** The API needs typed request and response models around Python analysis functions and should be easy to inspect during local development.

**Decision:** Use FastAPI with Pydantic schemas and synchronous SQLAlchemy sessions.

**Alternatives:** Flask would reduce framework surface but require additional validation and API documentation wiring. A TypeScript or Java service would offer a shared frontend language or stronger compile-time constraints, but would separate the analysis logic from its Python implementation.

**Tradeoffs:** FastAPI provides validation and OpenAPI documentation with little glue code. Synchronous handlers are simple, but report execution occupies an API worker until all steps finish.

**Consequences:** New endpoints should define explicit schemas. Long-running or concurrent workloads would require a worker boundary or an asynchronous redesign.

## ADR-002: PostgreSQL as the system of record

**Status:** Accepted

**Context:** Cost records, findings, recommendations, and report runs have relational fields and are queried by date, service, and severity.

**Decision:** Store demo inputs and derived results in PostgreSQL through SQLAlchemy.

**Alternatives:** SQLite would remove a local service dependency. Document storage would allow flexible records but is unnecessary for the fixed relational schema.

**Tradeoffs:** PostgreSQL demonstrates a realistic service boundary and aggregation queries at the cost of heavier local setup.

**Consequences:** Docker Compose provisions PostgreSQL. The repository currently creates tables from SQLAlchemy metadata and needs migrations before schemas can evolve safely.

## ADR-003: Redis as an optional dashboard cache

**Status:** Accepted

**Context:** Dashboard assembly repeats aggregate database queries, while cache availability should not determine API availability.

**Decision:** Cache the serialized dashboard response for 300 seconds and treat Redis errors as cache misses.

**Alternatives:** Query PostgreSQL on every request, cache in process, or precompute aggregates. In-process caching would diverge across workers; precomputation adds scheduling that the demo does not need.

**Tradeoffs:** Redis demonstrates an external cache and shared TTL behavior, but adds a service for a small synthetic dataset.

**Consequences:** The dashboard remains usable when Redis is unavailable. Other endpoints are intentionally uncached, and invalidation is limited to expiry or a completed report run.

## ADR-004: Deterministic rules before model-generated prose

**Status:** Accepted

**Context:** Operational findings need traceable inputs and must still work without external credentials.

**Decision:** Derive costs, anomalies, infrastructure findings, and recommendations with local rules. Use OpenAI only to summarize those derived facts, with a deterministic text fallback.

**Alternatives:** A model could generate findings directly, or the application could require an external model for every report. Both would make local behavior less repeatable and increase the risk of unsupported claims.

**Tradeoffs:** Rules are explainable but simplistic. The optional summary improves presentation but adds cost, latency, data-sharing, and model-availability considerations.

**Consequences:** Model output must not be treated as an independent source of truth. Analysis rules require tests and documented thresholds as they evolve.

## ADR-005: HCL parsing for bounded Terraform fixtures

**Status:** Accepted for the current demo scope

**Context:** The repository needs a small, inspectable demonstration of infrastructure findings against known sample files.

**Decision:** Parse Terraform with `python-hcl2`, inspect selected resource attributes, and restrict requests to `.tf` file names under the configured samples directory.

**Alternatives:** Regex matching is smaller but cannot represent HCL reliably. A policy tool such as Checkov, tfsec, or Open Policy Agent would cover more controls but would make this repository an integration wrapper rather than an inspectable analyzer example.

**Tradeoffs:** Structural parsing handles normal HCL syntax and malformed-input errors, but it does not evaluate modules, variables, expressions, plans, provider defaults, or remote state.

**Consequences:** Results remain review prompts rather than security or compliance guarantees. Plan-aware checks would require a separate evaluation boundary.

## ADR-006: Docker Compose for local topology

**Status:** Accepted

**Context:** Reviewers need one command that starts the frontend, API, PostgreSQL, and Redis with predictable networking and seed behavior.

**Decision:** Use Docker Compose and health-dependent startup for local evaluation.

**Alternatives:** Host each component separately, use a development script, or provide Kubernetes manifests.

**Tradeoffs:** Compose is portable and inspectable but does not address secrets, autoscaling, ingress, backup, or rollout strategy.

**Consequences:** The Compose file is a development environment, not a deployment recommendation.

## ADR-007: Explicit demo, connected, and offline modes

**Status:** Accepted

**Context:** A provider failure must not silently substitute simulated records, and local evaluation must not require cloud credentials.

**Decision:** Select one operating mode at process startup. Demo mode seeds deterministic fixtures. Connected mode creates an empty schema and permits explicit provider sync operations. Offline mode creates an empty schema and rejects provider calls while retaining previously stored data.

**Alternatives:** Automatically fall back to demo data after provider errors, or infer mode from the presence of credentials.

**Tradeoffs:** Explicit configuration adds one deployment setting but makes the provenance of displayed data unambiguous.

**Consequences:** Connected installations need an intentional first sync. Mode changes require a process restart and do not transform existing records.

## ADR-008: AWS credential chain with optional AssumeRole

**Status:** Accepted

**Context:** The application needs to read billing data locally, in containers, and across accounts without storing long-lived credentials.

**Decision:** Use the boto3 default credential chain. When `AWS_ROLE_ARN` is configured, obtain a short-lived session through STS and optionally pass an external ID.

**Alternatives:** Store access keys in the database or application configuration, shell out to the AWS CLI, or require AssumeRole for every environment.

**Tradeoffs:** The SDK chain supports several hosting environments, but credential resolution errors can be less obvious than explicit keys. AssumeRole adds trust-policy and session-lifetime considerations.

**Consequences:** Deployments should use workload identities or dedicated profiles and least-privilege policies. The application never returns credential material in its API.

## ADR-009: Operator-triggered provider snapshots

**Status:** Accepted

**Context:** Provider imports must be observable and failure-safe without introducing a scheduler or task queue.

**Decision:** Expose explicit synchronization endpoints. Finish remote reads before transactionally replacing the relevant stored window or workload snapshot.

**Alternatives:** Poll providers during web startup, schedule work inside the API process, or add a durable worker and queue.

**Tradeoffs:** Explicit syncs are simple and auditable but can occupy an API worker and become stale until invoked again.

**Consequences:** A shared deployment needs endpoint authorization and should move synchronization into a scheduled background worker.
