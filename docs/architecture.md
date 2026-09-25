# Architecture and decisions

## Business question

A portfolio reviewer needs to identify forecast cost overruns and understand associated delivery risks. The demonstration returns source-linked explanations while retaining a deterministic path for financial calculations.

## ADR 001 Separate arithmetic from generation

**Decision:** Compute forecast variance in Python before prompting a model. Supply both absolute and percentage variance with each record.

**Reason:** Financial fields should remain consistent across prompts and model versions. An LLM explains evidence; it does not become the system of record. This demonstration uses integer USD amounts. A real financial system should use decimal values and explicit currency conversion rules.

## ADR 002 Use bounded retrieval before generation

**Decision:** Use project IDs, project names, and portfolio keywords to retrieve from four synthetic records. Unknown IDs and unrelated topics return no evidence and skip model calls.

**Tradeoff:** Transparent and easy to inspect, but limited to English keyword matching. This is not semantic retrieval and does not understand arbitrary financial predicates. Demo mode shows matching record summaries rather than interpreting every question. For a larger corpus, evaluate structured filtering or hybrid retrieval against a reviewed dataset.

## ADR 003 Keep observability opt-in

**Decision:** Send LangChain events to Langfuse only when `ENABLE_TRACING=true` and all Langfuse configuration values are present. Do not infer permission from the presence of keys alone.

**Data boundary:** Traces can include the complete prompt, question, source records, and generated answer. The demo uses fictional records. Production systems need data classification, retention policies, masking, access controls, and an approved telemetry destination.

**Metric boundary:** `citation_id_validity` is a narrow mechanical check. Do not label it answer accuracy. Provider usage and Langfuse model-price settings determine available cost estimates.

## ADR 004 Expose a local demonstration API

**Decision:** Serve a static dashboard and synchronous request handlers using FastAPI. Default instructions bind to loopback. Application shutdown flushes queued telemetry.

**Tradeoff:** Easy local setup and a small runtime footprint. No authentication, public ingress, rate limiting, cancellation, persistent storage, or tenant isolation is provided. Do not expose the server publicly as-is. Concurrency capacity and telemetry backpressure need load testing before production.

## Failure behavior

| Condition | Behavior |
|---|---|
| Blank or oversized question | HTTP 422 before inference |
| Missing live model configuration | Startup fails with a clear configuration error |
| No matching records | Abstains without calling the model |
| Missing or fabricated project citation | Answer replaced by abstention |
| Provider exception or timeout | Generic HTTP 502; provider details are not returned |
| Tracing disabled | No Langfuse client or callback created |

Callback export behavior is controlled by the Langfuse SDK; verify connectivity and actual trace arrival in a configured environment. A trace ID is not proof that the telemetry server received the trace. Score submission failures can fail the request; a production implementation should define fail-open behavior and monitor its telemetry queue.

## Security boundaries

The prompt instructs the model to treat source content and questions as data, but prompt instructions are not a complete prompt-injection defense. There are no write tools, arbitrary file reads, or executable model outputs. The browser renders answer strings using `textContent` to avoid interpreting model-generated HTML. Before extending this demo, enforce authorization outside the model and validate all tool inputs.

## Suggested interview walkthrough

1. Run a budget question and show that Cedar Claims is forecast USD 36,000 over budget.
2. Explain why the calculation is outside the model.
3. Ask an unrelated question and show abstention.
4. Show the named LangChain stages and tests for citation rejection.
5. With your own configured account, inspect the Langfuse trace and score.
6. Discuss the gap between a syntactic citation check and factual grounding.
7. Explain how identity, MCP adapters, and production observability would extend the design.
