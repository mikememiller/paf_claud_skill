<!-- Syntax Corporation © 2026 — EBS PAF Agent skill -->
# Observability & monitoring (PAF 26.4)

Distilled from the PAF Platform Monitoring & Agentic Observability TDD (v0.3).
This is the decision-ready reference a build turn uses; the TDD is the full
design and the per-tenancy deliverable template.

**Positioning.** Generation is commoditized. Monitoring is the operational
mechanism that makes "we stand behind agents in production" real, demonstrable,
and billable. It is the engineering substantiation of the moat — not an add-on
afterthought.

## The two planes (keep them architecturally distinct)

Running an agent against a live EBS estate needs two different questions answered
continuously, with two different instruments. Conflating them is the most common
reason monitoring misses real incidents.

| | **Plane A — agent observability** | **Plane B — platform availability** |
|---|---|---|
| Question | Are the agents behaving? | Is the platform alive? |
| Source | PAF 26.4 native OTEL trace export | External synthetic probes + resource collectors |
| Granularity | Per run / step / tool-call / LLM-call | Per component / per dependency edge |
| Backend | Tracing provider (Phoenix / Langfuse / Opik) | OCI Monitoring, Health Checks, DB Management, Logging |
| Role | **Differentiated supervision (the moat)** | Managed-service SLA (table stakes) |
| Dependency class | Soft — PAF runs if it fails | Mixed — covers hard and soft dependencies |

A failure in one plane (e.g. a stalled trace pipeline) must not blind the other.

## PAF 26.4 constraints that shape the build

Four properties of PAF 26.4 observability are hard constraints — respect them or
the design breaks:

1. **One tracing configuration per instance.** PAF allows exactly one active
   tracing tool config; the add control is disabled while one exists. Multi-
   destination / multi-tenant routing must happen **downstream, in an OTEL
   collector** — PAF points at the collector, never at a backend directly.
2. **Admin-only and per-environment.** Enabling observability requires PAF
   administrator rights, and the config does **not travel** between environments
   (same rule as every other resource binding). If you are viewer-only, the
   tracing-config step is assigned to an admin in each tenancy.
3. **Masking is binary, payload-level.** It either redacts sensitive payloads or
   it does not — **no field-level granularity**. This forces an explicit per-
   customer data-handling decision (below).
4. **External backends require proxy changes.** A backend outside the PAF network
   needs "Allow User Supplied Proxy" on and the backend URL permitted. The same
   proxy posture governs private MCP reachability — so proxy config is itself a
   monitored surface (Plane B §6.3 in the TDD).

## Backends — three supported providers

PAF 26.4 supports **Arize Phoenix**, **Langfuse**, and **Comet Opik**. All three
have an OSS, self-hostable core (no licence fee); each has a paid tier for
compliance / retention / support.

| Provider | OSS core | Self-host footprint | Traces endpoint pattern |
|---|---|---|---|
| Arize Phoenix | self-hostable, no fee | container + persistent store | `http://<host>:6006/v1/traces` |
| Langfuse | MIT core | Postgres + ClickHouse + Redis + S3-compatible store | `http://<host>:3000/api/public/otel/v1/traces` |
| Comet Opik | self-hostable, no fee | container + persistent store | `http://<host>:5173/opik/api/v1/private/otel/v1/traces` |

**Recommendation.** Self-host **Langfuse** for the shared multi-tenant backend —
MIT core, project-level segregation that maps to per-customer separation, OTEL-
native ingestion that fits the collector pattern. ClickHouse storage is the
dominant cost driver. **Phoenix** is the better choice for a single-container
lighthouse footprint. Confirm self-host requirements against current provider
docs at implementation time — the hosting stack and tiers change.

## Masking — the per-customer data-handling decision

The central governance call for Plane A, and a genuine tradeoff:

- **Masking ON** (default): redacts LLM inputs/outputs, tool inputs/outputs, and
  OpenInference payload attributes before export. **Retained:** token counts,
  model identifiers, latency, and trace/span/session identifiers. Sufficient for
  availability, latency, cost attribution, and routing review. **Cannot** show
  whether an answer was *wrong* — only that one was produced.
- **Masking OFF**: full prompts, completions, tool args/results exported and
  stored. Required to catch hallucination or a bad tool result — but ERP-derived,
  potentially sensitive data then flows to the backend.

**Rule:** default masked. Unmasked **only** with (a) explicit customer
authorization, (b) a defined retention window, and (c) the backend hosted inside
the customer's own boundary where residency requires it. Record the choice in the
customer's **data-handling profile** (the `observability.customer_data_handling_profile`
spec field).

### Closing the masking gap — automated evaluation
Masked traces prove an answer was produced, not that it was correct. Resolve with
**automated evaluation** — score runs rather than store payloads. All three
backends expose eval hooks. Online evaluators emit scores (groundedness,
relevance, tool-call validity, refusal/error) as span attributes; LLM-as-judge or
rule checks score a sampled, consent-based subset, retaining only the score + a
redacted rationale; groundedness/citation checks on Knowledge-Agent answers
compare against the sources PAF already records. The score becomes another column
in the Plane A run list and another input to the SLA evidence base — quality
signal with no extra payload exposure.

## The OTEL collector pattern (non-negotiable for multi-tenant)

```
PAF (one tracing config) → OTEL collector → ┬→ tracing backend (operator drill-down)
                                            ├→ CxHub ingestion path (tagged by customer)
                                            └→ per-run digest (metadata only) → OCI Logging Analytics
```

The collector is the **only** component that knows about multiple tenants and
multiple destinations. This keeps PAF's single-config constraint from limiting
fan-out and keeps per-customer routing logic in one place. PAF's tracing config
points at the collector, full stop.

## OCI analysis plane — Logging Analytics as correlation hub

Plane A says "what did this run do," Plane B says "is each dependency up." Neither
correlates a failing run with the infra/security event that caused it. **OCI
Logging Analytics** is the log plane and correlation surface — ingest, detect,
correlate:

- **Ingest.** A Management Agent on the PAF VM collects OS, container-runtime, and
  PAF application logs (the PAF/WayFlow format needs a **custom Log Source +
  parser** — a prototype task, not an assumption). A Service Connector brings OCI
  service logs (Audit, VCN flow, Load Balancer, Bastion, Cloud Guard) into the
  same log groups. Database audit flows from both the ADB sidecar and the EBS
  estate; the preconfigured **E-Business Suite Log Analytics** application covers
  the ERP tier behind the MCP servers.
- **Detect.** Three layers: detector rules at ingest (credential errors, `ORA-`
  patterns, HTTP 401/429 from the model endpoint); scheduled saved searches
  (error-rate trends, SLO burn); ML clustering for novel signatures. Every
  "silent failure mode" in the Plane B dependency inventory earns a named
  detector here.
- **Correlate.** Entities/topology model the PAF VM, both databases, each MCP
  server, and the model endpoint as related entities, so "agent runs failing" and
  "EBS concurrent manager down" surface as one incident.

## MCP access security & the audit chain — the per-agent OAuth rule

In the target architecture the customer's EBS DB is on OCI Database (DBaaS/Exadata)
and agents reach it through the **OCI Database Tools managed MCP server**, which
enforces access at three layers:

- **IAM:** OAuth 2.0 against an OCI Identity Domain; tool access governed by app
  roles (`MCP_Administrator` / `MCP_Operator` / `MCP_User`). Production posture
  for agent-facing toolsets = **`MCP_User`**, named reports + validated custom
  PL/SQL tools only, **no ad-hoc `run-sql`**, private endpoint behind an NSG.
- **Service:** SQL Reports publish known, parameterized SQL as reusable tools —
  the product expression of the deterministic-policy principle (the model never
  derives SQL).
- **Database:** the server propagates end-user identity into the DB session via
  `CLIENTCONTEXT` (OAuth subject, user/client OCIDs, roles, MCP server OCID,
  compartment), readable with `SYS_CONTEXT` and usable for row-level controls.

> **HARD DESIGN REQUIREMENT — one OAuth client per agent (family), never a shared
> "PAF" client.** When a token's subject type is "client," the audited principal
> resolves to the client name. Per-agent registration yields per-agent attribution
> for free; a shared client collapses all 25 agents into one indistinguishable
> identity and destroys the audit chain.

**The audit chain joins three records on one key** (`opc-request-id`): the
`InvokeMcpServer` event in OCI Audit (principal, source IP, auth type, path,
status, request id); the Unified Audit Trail row after
`AUDIT CONTEXT NAMESPACE CLIENTCONTEXT` is enabled (request id in `EXECUTION_ID`,
principal/server-OCID/compartment in `APPLICATION_CONTEXTS`); and the §trace
digest. The chain reads **agent run → MCP invocation → SQL executed**, answerable
in one Log Explorer query. (Open prototype item: confirm `opc-request-id` reaches
the MCP client so the collector can stamp it into the digest; fallback is
time-window + client-name correlation.)

## Plane B — dependency inventory & probe set

Monitor **from PAF's vantage point, outward.** Real outages are silent and
asymmetric: PAF's host stays green while a wallet expires, an SSE connection
drops, an LLM quota trips, or a proxy rule starts blocking a private URL. The core
of Plane B is **continuous synthetic probes** replicating each PAF connection (the
automated equivalent of PAF's "Test connection"), plus resource monitoring.

| Target | Probe | Interval | Alarm condition | Class |
|---|---|---|---|---|
| PAF service / Agent Builder UI | HTTP health check | 1 min | non-200 / timeout ×2 | hard |
| PAF host | resource metrics | 1 min | disk > 85%, mem/CPU > 90% sustained | hard |
| Database 26ai / ADB | synthetic connect + light query | 2 min | connect fail / latency over baseline | hard |
| Select AI profile | profile-bound test query | 5 min | error / no response | hard |
| Model endpoint | minimal completion probe | 5 min | error / 429 / latency over threshold | hard |
| MCP server — liveness | SSE / HTTPS liveness | 1 min | connection drop / non-response | hard |
| MCP server — ERP backend | tool-call success rate | 5 min | success rate below threshold | hard |
| Egress / proxy path | reachability to each required URL | 2 min | any required URL unreachable | hard |
| Tracing backend | ingestion health + storage | 5 min | ingest backlog / store fill | **soft** |
| Credentials | expiry-calendar evaluation | daily | any binding inside renewal window | hard |
| Watched configuration | proxy / tracing config drift | on change + hourly | any change to monitored settings | hard |

**Two probes per MCP server.** EBSVision (or the managed server) can report healthy
while the EBS instance behind it is down — PAF then gets tool errors against a
green server. **Tool-call success rate** is the signal that distinguishes the two.

**Config is a monitored surface.** "Allow User Supplied Proxy", "Block Private
Outbound Urls", and the tracing config can each silently sever connectivity with
no resource alarm. Drift detection on them is cheap and prevents a whole class of
silent outage.

## Phase sequencing (vs. the 25.3 → 26.4 upgrade — now complete)

- **Plane B first, any version.** Availability monitoring of host, DB 26ai, MCP,
  and network does not depend on PAF version — stand it up immediately; it also
  de-risks the upgrade by giving dependency visibility during the change.
- **Plane A requires 26.4 + admin.** Native trace export is a 26.4 capability; an
  administrator configures the single tracing tool to point at the collector,
  masking on by default. The estate is now on 26.4, so Plane A is unblocked.

## Maturity ladder
- **L1 Availability** — Plane B (in scope).
- **L2 Traceability** — Plane A: per-run traces, latency, tool-calls, cost (in scope).
- **L3 Quality** — automated eval scoring (designed; next increment).
- **L4 Auto-remediation** — closed-loop failover / rotation / throttle (roadmap).

## Sources
PAF Monitoring & Agentic Observability TDD v0.3; PAF 26.4 manual (Observability,
Proxy Settings, Export/Import); OCI Database Tools managed-MCP docs; OCI Logging
Analytics / Cloud Guard docs. Cost and SLO figures in the TDD are planning
estimates — validate against live tenancy sizing before any commercial use.
