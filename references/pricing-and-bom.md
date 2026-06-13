<!-- Syntax Corporation © 2026 — EBS PAF Agent skill -->
# Pricing model + OCI Bill of Materials

`templates/deliverables/pricing.py` computes **one** pricing model from `spec.yaml`
and emits JSON consumed by the SOW, sales deck, and ROI calculator — so every
figure matches across documents.

## Delivery rate card (default)
Blended from: **onshore $175/hr, nearshore $85/hr, offshore $65/hr** and a
`delivery_mix` (e.g. 20/40/40 → blended ≈ $93/hr). Used for the fixed-fee
implementation SOW (est. hours × blend) and the managed-services run team.

## Managed-services pricing (per month; 12 / 24 / 36-mo)
`monthly = run_hours_per_month × blended_rate + OCI_run_cost + agent_license/12`,
with term discounts **0 / 10 / 20 %** for 12/24/36 months. Output as a
signature-ready 3-term table in the SOW; same numbers flow to deck + ROI.

## OCI Bill of Materials (line items)
- **ADB 26ai** (PAF sidecar) — ECPU, License Included or BYOL (~76% lower).
- **Private Agent Factory — $0** (included with AI Database 26ai).
- **OCI Database Tools / Managed MCP** — *new line; confirm metered vs included
  at install* (verify item). Replaces the old self-hosted broker VM.
- **OCI Generative AI** — per-token (model-dependent), consumption.
- **OCI Document Understanding (OCR)** — per-page, optional (per-domain ingestion).
- Storage + networking. (No broker VM, no Instant Client host in production.)

### Monitoring & observability lines (when `spec.observability` is set — `observability.md`)
- **Tracing backend — software:** $0 (self-hosted OSS core: Phoenix / Langfuse /
  Opik).
- **Tracing backend — infrastructure:** compute + storage; ClickHouse is the
  dominant driver for Langfuse. Scales with trace volume × spans/run × payload
  size × masking state (~10:1 compression typical; masked is materially smaller
  than unmasked).
- **OTEL collector:** estate-shared — negligible per-customer share.
- **OCI Logging Analytics:** per-GB ingest — includes the EBS Unified Audit
  volume from the MCP audit chain. The per-GB ingest is the explicit trade that
  buys down operator labor (the dominant recurring cost).
- **OCI Streaming:** the CxHub transport (render-only feed).
- **OCI Functions:** invocations behind the OCI→ServiceNow material-events path.
- **Plane B probes:** mostly OCI-native (Monitoring / Health Checks) — low
  marginal infra.
- **Operator labour:** the real recurring cost — the supervision headcount the
  foundation fee funds. Scales with estate size and SLA tier.

> All monitoring figures are **planning estimates** (TDD discipline) — confirm by
> measured ingest volume and live tenancy sizing before any commercial use.
> Self-host is cost-effective at scale or where sovereignty is mandatory; managed
> cloud tiers can be cheaper once operational overhead is included.

## Consumption estimator (.xlsx, anthropic-skills:xlsx)
Per-transaction unit economics (OCR pages + LLM in/out tokens + ECPU + storage) ×
the `volume_tiers`, toggles for **BYOL vs License Included**, model choice, OCR
on/off, Universal-Credits/Support-Rewards discounts → monthly + annual OCI run
cost per tier. Reference figures (AP): ~$6.8K / $26.9K / $120.5K list; ~$2.15K /
$8.3K / $45K BYOL — re-derive per domain/volume.

## Interactive ROI calculator (.html + .xlsx)
Sliders: annual volume · current cost/txn · target STP% · avg value · early-pay
terms & capture · duplicate/error rate · labor rate · BYOL · term. Outputs: net
savings, **payback months**, 1/3-yr cumulative, ROI %, NPV, sensitivity. A
**"my EBS data" mode** is pre-filled by the read-only value-assessment pack.
Reads the same pricing model. The leave-behind that keeps selling.
