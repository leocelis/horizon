# Changelog

All notable changes to `horizon-monitor` are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Artifact ingestion — capture that does not depend on remembering.**
  `ingest_artifacts(store, adapter, *, item_id)` turns an adapter's records into
  `ARTIFACT` events. The adapters and their interface already shipped, but nothing
  consumed them; this is the missing half. Ingestion is idempotent (dedupe on the
  source's own `(source_system, native_id)`, never a payload hash) and incremental
  (`since` defaults to the newest artifact already recorded), so it is safe to run
  on a schedule — which matters, because a capture path that is unsafe to re-run
  will not be automated, and one that is not automated depends on somebody
  remembering. `scripts/ingest_artifacts.py` is the operator/cron entry point.
  Deliberately **not** an MCP tool: subscribing to a source is a standing
  arrangement, not a conversational act.
  The mission link stays a caller's decision — `item_id` is required and no
  adapter can supply one, by construction.
- **Setup discoverability.** `clock_status` now returns `setup_guidance`, naming the
  next concrete call while the store has no root horizon or no mission, and going
  quiet once one exists. An unconfigured plane and a broken one previously both
  returned an empty report with no way to tell them apart, and the setup steps
  lived only in a document. The guidance never proposes a horizon date — that is
  the operator's to choose.
- **Resource `horizon://memento/agent-rules`** serves the canonical agent-rules
  block from the installed package, so a host can read it rather than copy it from
  the repository. A drift test pins it to the published §3 block.
- `MementoStore.known_artifact_ids()` / `latest_artifact_time()` — the provenance
  lookups ingestion needs for dedupe and incremental pulls.

### Changed
- `MementoStore.erase_all()` takes `mark_tenant_erased` (default `True`).
  Destroying a tenant's data and recording that the tenant *exercised erasure*
  are different events; conflating them left maintenance and test cleanup
  labelling live tenants as `erased`. The default is unchanged, so the
  right-to-erasure path behaves exactly as before.

- **Durable, multi-tenant mission stores.** The mission plane can now persist to
  **MySQL 8** as well as SQLite, so it survives on platforms with an ephemeral
  filesystem — where a file-backed store silently resets on every deploy and reports a
  confidently wrong clock afterwards. Install with `pip install horizon-monitor[mysql]`
  and set `HORIZON_MEMENTO_STORE_DSN=mysql://user:pass@host:port/db` (it takes
  precedence over `HORIZON_MEMENTO_STORE_PATH`). SQLite remains the zero-dependency
  default and its behaviour is unchanged.
  - **TLS verification is mandatory** for the MySQL backend: it refuses to connect
    without a CA, supplied as `HORIZON_MYSQL_SSL_CA` (path) or `HORIZON_MYSQL_SSL_CA_B64`
    (base64 PEM, materialised at startup for hosts with no persistent disk).
  - **Connection liveness**: managed servers close idle connections, and mission traffic
    is sparse by design, so the store pings and reconnects with backoff at every
    transaction and read boundary (never mid-transaction, where a reconnect would drop
    the open transaction's state). Permanent failures — bad credentials, unknown
    database, failed TLS trust — fail fast instead of retrying for minutes.
- **Tenancy.** A `MementoStore` is now a tenant scope, defaulting to `local` so every
  existing single-operator install and API is unchanged. `store.scoped(tenant_id)`
  returns a view over the same connection, and every statement carries the scope's
  tenant, so cross-tenant reads and writes cannot be expressed. Two new tables,
  `horizon_tenants` and `horizon_api_keys`, map an API key's **full** SHA-256 to an
  **assigned** tenant id — so rotating a key preserves that tenant's history, which
  deriving the identity from the key would have destroyed. Unknown or revoked keys fail
  closed with a typed `TenantResolutionError`; tenants are provisioned out of band by
  the operator (`scripts/provision_tenant.py`) and never auto-created by an inbound
  request. Provisioning is deliberately not exposed as an MCP tool.
- **`MementoStore.erase_all()`** — the right-to-erasure path, destroying a tenant's
  items, event log and signal state and returning per-table counts so an erasure is
  recorded rather than merely performed. It is all-or-nothing within the tenant: no
  selective row delete exists, because `mm_events` is append-only precisely so a reported
  figure traces back to a recorded fact, and a per-row delete would be a history-editing
  tool wearing a privacy label. Also deliberately not an MCP tool — erasure is an
  operator action, so no turn of conversation can talk an agent into destroying a
  history. See `PRIVACY_POLICY.md` §1.6.

### Changed
- Mission stores are **schema v2**. Existing v1 SQLite stores migrate automatically and
  additively on first open — a file backup is taken first, row counts are asserted
  unchanged, and the migration is gated so re-running is a no-op. Primary keys are not
  rebuilt (the one step that could lose data); a migrated store keeps its v1 keys, which
  is correct because SQLite stores are single-tenant.

### Fixed
- `MementoStore.redact_person_display_name()` raised `TypeError` instead of the typed
  `StoreCorruptionError` when given an unknown `item_id`, because the error was
  constructed with the wrong arity.

- **Memento Mori — the mission plane** (`horizon_monitor.memento`, optional and inert
  until a store is configured). A second measurement plane whose unit of analysis is the
  *mission* — a goal with a clock — persisted across sessions, processes and agents.
  Where the conversation plane measures dialogue health turn by turn, this one measures
  elapsed **calendar** time against outcomes: item ages, TTL state, deferral expiry,
  days-since-progress with a recording-path check that never conflates *no work* with
  *no records*, per-entity latency (slowest entity and, separately, the entity currently
  blocking), horizon share, and — only when the operator declares a rate and amounts —
  cost-of-delay and break-even dates. Twelve edge-triggered signals ride the existing
  `process_turn` contract for sessions bound via `associate_mission`; every event carries
  a `plane` tag and mission signals are surfaced to the operator rather than applied
  silently. Six MCP tools (`clock_register`, `clock_progress`, `clock_status`,
  `clock_propose`, `clock_ack`, `associate_mission`) register **only** when a store path
  is set. Docs: [`docs/product/MEMENTO_MORI_PRD.md`](docs/product/MEMENTO_MORI_PRD.md),
  [`docs/spec/MEMENTO_MORI_TECH_SPEC.md`](docs/spec/MEMENTO_MORI_TECH_SPEC.md),
  [`docs/integrations/MEMENTO_MORI_AGENTS.md`](docs/integrations/MEMENTO_MORI_AGENTS.md);
  runnable example `examples/memento_mori_mission_clock.py`.
  The plane performs elapsed-time **accounting**, never estimation: it invents no
  duration, date or amount; refuses NPV/IRR/DCF, currency conversion, forecasts and
  counterfactuals with typed errors; emits no p-values or confidence intervals on path
  comparisons; reports entity latency on functional **slots** rather than as a score on
  any person; and degrades by omission with an explanatory field rather than
  substituting a value. Identical store + identical evaluation instant yields a
  byte-identical report.

- **Illegal-content prohibition and 18 U.S.C. § 2258A mandatory-reporting compliance**
  (`TERMS_OF_SERVICE.md` new §13, cross-referenced from `LEGAL.md` §17): explicit CSAM
  prohibition (§3(9)), Horizon's compliance posture as a U.S.-based provider under the
  REPORT Act of 2024, and an honest disclosure of how the zero-retention design (§1.1 of
  the Privacy Policy) limits what can practically be preserved if Horizon ever becomes
  aware of a violation — Horizon cannot retroactively produce message content it never
  stored.
- **Binding arbitration + class action waiver** (`TERMS_OF_SERVICE.md` new §14), with
  carve-outs for small claims court, injunctive relief on IP/confidentiality, and the
  §13 illegal-content prohibition (enforceable in any forum). Includes a 30-day opt-out
  window (a standard enforceability-strengthening practice) and preserves the existing
  EU-consumer mandatory-rights carve-out. §12 (Governing Law) split from dispute
  resolution, which now lives in §14. `LEGAL.md` §16 updated to reference the new
  mechanism rather than duplicate it.
- **General contract provisions** (`TERMS_OF_SERVICE.md` new §15): force majeure,
  severability (explicitly protecting the liability cap and indemnification clauses from
  an all-or-nothing enforceability failure), entire agreement, assignment, no-waiver,
  notices, and relationship-of-the-parties — standard SaaS ToS boilerplate that was
  previously entirely absent from the document set.
- **Other U.S. state privacy laws** (`PRIVACY_POLICY.md` new §7): a general-purpose
  clause acknowledging the growing state comprehensive-privacy-law landscape (Colorado,
  Connecticut, Virginia, Utah, and others) and honoring the same access/deletion/
  correction rights regardless of which state law would otherwise apply, rather than an
  enumerated 19-state matrix that would need updating every legislative session.

### Changed
- **Agent instructions now route `active_events` by `plane`.** Every instruction surface
  (the MCP server's own `_INSTRUCTIONS`, the Claude Code / Claude Desktop / Cursor
  integration docs, and `docs/cursor-rules/horizon-monitor.mdc`) previously told agents to
  apply `suggested_behavior` silently with no plane qualifier. That wording predates the
  mission plane and would have caused mission signals — an expired deadline, a stalled
  mission — to be silently absorbed. Conversation-plane events remain invisible by
  contract; mission-plane events are surfaced with their numbers. The invisibility
  contract now states which plane it governs.
- Bumped `LEGAL.md`, `TERMS_OF_SERVICE.md`, `PRIVACY_POLICY.md`, and
  `DATA_PROCESSING_AGREEMENT.md` to version 1.1 (from 1.0), effective 2026-07-19.
- `PRIVACY_POLICY.md` sections renumbered (§7 onward shift by one) to accommodate the new
  §7 state-privacy-law section; internal cross-references updated accordingly.

## [0.2.3] - 2026-07-19

### Added
- **Per-key rate limiting** on the hosted MCP server (`mcp/auth.py::RateLimiter`) — in-process
  token bucket, default 120 req/min, burst 20, both env-configurable
  (`HORIZON_RATE_LIMIT_PER_MINUTE` / `HORIZON_RATE_LIMIT_BURST`). Exceeding the limit returns
  HTTP 429 with `Retry-After` and the IETF draft `RateLimit`/`RateLimit-Policy` headers. Only
  authenticated requests are limited (unauthenticated attempts fail at 401 before reaching the
  limiter). `/health` remains exempt.
- **Per-key session isolation and caps** on the hosted MCP server (`mcp/session_registry.py`,
  new module). Closes two real gaps: (1) any authenticated key could previously read
  (`get_trajectory`/`get_events`) or continue (`process_turn`) ANY session_id, including one
  created by a different key; (2) `configure_session(session_id=None)` previously looped over
  **every live session on the shared server**, so any authenticated key could silently mutate
  every other tenant's thresholds/event-modes with no session_id needed at all. Sessions are
  now owned by the key that created them, capped at 50 concurrent sessions per key
  (`HORIZON_MAX_SESSIONS_PER_KEY`, LRU-evicted — a key's own volume never costs another key a
  session), and `configure_session`'s "global" mode is reinterpreted per-key as "every session
  I own." Local/stdio callers (no API key — single-tenant by construction) keep the original
  unrestricted behavior, since there is no other tenant to protect. A denied cross-tenant
  access returns the same error shape as an unknown session_id, so a caller cannot distinguish
  "not yours" from "never existed."
- **`FidelityMonitor.session_count`** public property (was previously only accessible via the
  private `_sessions` dict).

### Fixed
- **Health endpoint and docs falsely claimed Redis-backed session resumability.** `REDIS_URL`
  is checked in exactly two places in the entire codebase (a health-status flag and a startup
  print) and is never actually passed to any session/event store — sessions have always been
  in-process memory only, lost on every restart. Fixed `/health`'s `resumable` field to always
  report `false` instead of `bool(os.environ.get("REDIS_URL"))`, and corrected the same claim
  in `README.md`, `LEGAL.md` §6.2/§6.4/§8.1, `PRIVACY_POLICY.md` §8, `DATA_PROCESSING_AGREEMENT.md`
  §6, and `docs/integrations/CURSOR.md`. Upstash remains listed as a sub-processor (the Redis
  instance is genuinely provisioned in the hosted deployment) but is now accurately described
  as infrastructure capacity that session logic does not currently use.
- **`SECURITY.md` scope referenced stale `src/horizon/` paths** from before the `horizon` ->
  `horizon_monitor` rename (0.2.1).

### Changed
- **`TERMS_OF_SERVICE.md` §2:** API key requests must now come from an identifiable requester
  (a real GitHub account and/or verifiable email); anonymous/throwaway requests may be
  declined. Documents the enforced (not just contractual) rate limit and session cap.
- **`PRIVACY_POLICY.md` §1.3:** clarifies that the requester identity retained at key issuance
  is used for abuse accountability (revocation, platform reporting), not only key management.

## [0.2.2] - 2026-07-19

### Fixed
- **Dependency bound too loose:** core `transformers<5` allowed fresh installs to resolve
  `transformers` far past the validated stack (observed: 4.57.6, incompatible with older
  pinned `torch` such as 2.2.x). Tightened to `transformers>=4.34,<4.41` — matches
  `sentence-transformers`' own floor and caps just above the CI-validated 4.40.2, so a
  fresh `pip install horizon-monitor` now resolves the exact tested version. Found while
  installing into a host project with `torch==2.2.2` already pinned.

## [0.2.1] - 2026-07-18

### Changed
- **BREAKING — import renamed `horizon` → `horizon_monitor`:** the import name now matches
  the distribution name (`pip install horizon-monitor` / `import horizon_monitor`) and no
  longer collides with OpenStack Horizon's top-level `horizon` package. The PyPI name, CLI
  commands (`horizon`, `horizon-validate`), env vars (`HORIZON_*`), and MCP resource URIs
  (`horizon://…`) are unchanged. No compatibility shim is shipped — the package predates
  its first PyPI release.
- **MCP auth now fails closed:** when `HORIZON_API_KEYS` is unset and
  `HORIZON_AUTH_DISABLED` is not set, requests are rejected with a configuration error
  instead of being allowed with a warning. Key comparison is constant-time
  (`hmac.compare_digest`).
- **`FidelityMonitor.end_conversation(session_id)` / `delete_session(session_id)`:** new
  session-cleanup API for long-running servers (session state no longer grows unboundedly).
- **CLI:** `--preload` is now a paired flag (`--preload/--no-preload`) so preloading can
  actually be disabled.

### Fixed
- **Version sync:** `pyproject.toml` bumped `0.2.0` → `0.2.1` to match `server.json` and the
  live hosted MCP server/registry entry, which were already at `0.2.1`.
- **Irreversible-loss units bug:** context-window eviction now reports evicted **tokens**
  (was: evicted turn count) so `min_eviction_threshold` (a token count) is compared
  unit-consistently and the `irreversible_loss` degradation channel can actually fire.
- **Timestamp parsing:** `process_turn` accepts `Z`-suffixed ISO 8601 timestamps on
  Python 3.10 and normalizes naive timestamps to UTC; malformed timestamps raise a
  documented `TimestampParseError` instead of an arbitrary crash.
- **Integrations no longer swallow errors silently:** OpenAI/LangChain wrappers log a
  warning (with traceback) when monitoring fails; monitoring failures still never break
  the wrapped LLM call. `HorizonCallback` now subclasses LangChain's
  `BaseCallbackHandler` when `langchain-core` is installed.
- **`__version__` reads from package metadata** (single-sourced from `pyproject.toml`)
  instead of a hand-duplicated string.

## [0.2.1] - 2026-07-17

### Changed
- **Public docs scope:** full internal PRD, research essays, and session handoffs removed
  from this repo — the OSS tree ships product overview, spec, integrations, validation
  evidence, and public content only.
- **Embedding engine defaults to CPU** on Apple Silicon (avoids MPS per-call sync cost);
  one batched `encode` per turn (`embedding.py`, `monitor.py`, `twr.py`).
- **Red-team remediation (Fix 1 + 2):** empirical necessity framing, physics as labeled
  metaphor, observability-first positioning; +15.7% caveated in user-facing surfaces.
- **`horizon_intent.yaml`:** `export_to` moved to `interface.tools:` (YAML parse fix);
  narrative fields reframed (`constraints:` untouched).
- **`process_turn` response contract:** healthy sessions return `{"ok": true, "turn": N}`;
  action required returns `{"ok": false, "health_status", "active_events"}` — full metrics
  via trajectory/events resources ([design-flaw/silent-agent-response]).

### Added
- **`docs/cursor-rules/horizon-monitor.mdc`** — canonical Cursor rule (synced with MCP
  `_INSTRUCTIONS`).
- **`requirements-dev.txt`** — dev/test install (`[dev,mcp]` + ML pins + `pyarrow`).
- **Fix 3/4 tooling:** `leading_indicator.py`, `interventional_ab.py`, validation scripts
  (`build_validation_corpus.py`, `adapt_external_corpus.py`, CLIs), regression tests
  (`test_no_overclaims`, `test_leading_indicator`, `test_validation_tooling`,
  `test_v6_ood_external`, `test_cursor_rules_alignment`, `test_remediation_regression`).
- **Validation artifacts:** `docs/reviews/leading_indicator.json`,
  `docs/reviews/interventional_ab_demo.json`.
- **Remediation gaps doc:** `docs/reviews/DESIGN_FIXES_redteam_remediation.md`.
- **Hosted MCP** at `https://horizon.leocelis.com` (DO App Platform, SSE, Redis-backed
  sessions); Bearer auth via `HORIZON_API_KEYS`; `/health` unauthenticated.
- **Deploy:** `deploy/Procfile`, `deploy/build.sh`, `deploy/runtime.txt`, `deploy/wsgi.py`.

### Documentation
- README: three getting-started paths (hosted MCP, pip install, source); ICLR 2026 demand
  citation; content pieces cross-linked; LEGAL manipulation/sycophancy scope disclaimer.
- Integrations: hosted endpoint options in Cursor, Claude Desktop, Claude Code guides.
- Landing pages (`docs/index.html`, `docs/site/index.html`) synced; performance caveats in
  footer; research nav → ICLR 2026 poster.
- `docs/README.md` — full public docs index and folder layout.
- `docs/reviews/E2E_REVIEW.md` — refreshed test snapshot and provenance chain.
- MCP `process_turn` tool description — deferred recording (previous turn at start of turn).
- Cursor integration — Pattern C points to shipped `horizon-monitor.mdc` (no inline duplicate).

## [0.2.0] - 2026-04-25

### Headline
All four validation gates (V1, V2, V3, V5) now pass on a 5,602-record
labelled corpus generated by the validation corpus builder.
v0.1 only met V3-rho; the remaining three gates were either skipped (no
labelled data) or under-thresholded.

| Gate | Constraint | v0.2.0 measurement | Headroom |
| --- | --- | --- | --- |
| V1 — proxy correlation | per-conv ρ ≥ 0.6, per-turn ρ ≥ 0.5 | **0.685 / 0.659** | +14% / +32% |
| V2 — per-event P/R   | every event P ≥ 0.7 AND R ≥ 0.7 (320 labels each) | **all 16 events ≥ 1.00 / 1.00** on spot check; full gate green | +43% |
| V3 — beats heuristics | rho lift > 25%, structural P ≥ 0.6 | **+202.4% lift, P=1.00 R=1.00** | massive |
| V5 — cross-domain | per-turn ρ ≥ 0.4 AND per-conv ρ ≥ 0.48 across 5 held-out domains | **min 0.517 / 0.718** | +29% / +50% |

### Added
- **Real GeoIP2 integration tests.** `tests/integration/test_geoip_real.py`
  drives `infer_location_class` against the canonical MaxMind reference
  test databases (`GeoIP2-City-Test.mmdb`,
  `GeoIP2-Anonymous-IP-Test.mmdb`, both shipped under
  `tests/integration/fixtures/`). 14 assertions cover real high-precision
  inference (London / Milton / Linköping), real low-precision rejection
  (radius > 100 km, Bhutan / US country-block / Philippines), real
  Anonymous-IP suppression (VPN, hosting, Tor exit, anonymous proxy),
  fail-soft on missing addresses, and end-to-end propagation through
  `FidelityMonitor.process_turn` into `result.location_class` /
  `result.spatial_constraint`. No mocks of the `geoip2` library, no fake
  readers — the real binary `.mmdb` files are queried.
- **`geoip_anonymous_db_path` client-context option.** When supplied
  alongside `geoip_db_path`, an IP that the Anonymous-IP DB flags as
  VPN / hosting / Tor / anonymous proxy is mapped to `"unknown"` even if
  the City-DB lookup would have succeeded. The free `GeoLite2-City`
  tier does not carry these flags, so an Anonymous-IP DB is the only
  way to get them with real data; this option makes that wiring
  explicit and keeps it opt-in.
- **Real spacetime-composition integration tests.**
  `tests/integration/test_spacetime_real.py` exercises the *full* 4D
  stack — temporal gap, circadian κ, retention, conversation velocity,
  ds² spacetime interval, light-cone reachability, and deictic
  resolution — composing through `FidelityMonitor.process_turn` on
  realistic multi-turn conversations with real ISO-8601 timestamps
  spanning seconds → days, real timezones (UTC nadir/peak/decline),
  and (in the headline test) real MaxMind GeoIP lookups. Asserts
  cross-feature invariants: retention monotonically falls with the
  gap; κ at 04:00 < κ at 11:00; velocity scales inversely with the
  gap; ds² flips sign as the gap grows; long-gap turns emit
  `signal.temporal_desync` and `signal.light_cone_collapse` from the
  *composed* signal (not from any single kernel called in isolation).
  Where `tests/unit/test_spacetime.py` pins the math kernel,
  `test_spacetime_real.py` pins the composition.
- **Coherence-gated IGT.** `_on_topic_igt(igt, consistency)` multiplies
  raw novelty by the bipredictability score so off-topic / hallucinated
  novelty no longer inflates fidelity. (`horizon/engines/fidelity.py`,
  closes V1 over-rewarding loophole.)
- **Hinge-loss coherence penalty (`eta`).** `_coherence_drop(consistency,
  floor=0.6)` adds a direct fidelity penalty when consistency falls below
  the floor — clean turns pay nothing, drift turns pay proportionally.
- **`ClaimTracker` engine.** New `horizon/engines/claim_consistency.py`
  detects numeric / named-claim contradictions (e.g. "2x faster" vs
  "4x faster" vs "no speedup") that embedding-only coherence misses.
  Powers a precision-1.00 `alert.contradiction` with no coherence
  fallback when `contradiction_method = "claim_tracker"` (the new
  default).
- **Per-sentence TWR.** `compute_twr` now compares each new sentence
  against per-sentence embeddings stored on prior `TurnState` records
  (not just whole-turn embeddings). Catches verbatim repeats inside
  multi-sentence agent replies.
- **Convergence health includes the current turn.** `compute_health`
  takes a new `current_igt` argument so a brand-new topic on the
  current turn immediately disqualifies "converged".
- New configuration knobs (all in `horizon/config.py`):
  `eta`, `coherence_floor`, `contradiction_method`,
  `contradiction_relative_tolerance`, `comprehension_trend_threshold`,
  `comprehension_igt_ceiling`, `horizon_widening_ratio`,
  `horizon_widening_floor`, `optimal_length_decay`,
  `convergence_igt_ceiling`.
- New `agent_sentence_embeddings` field on `TurnState`.
- Synthetic validation corpus builder
  (`scripts/build_validation_corpus.py`) with
  event-aware seeds (`_seed_low_igt_convergent`,
  `_seed_long_history_for_reference`, `_seed_for_eviction`,
  `_seed_for_pace_shift`) and per-event `_setup_turns` so every
  positive label lands in a context where the event can actually fire.
  Produces 222 V1 conversations, 5,120 V2 labels, 60 V3 conversations,
  200 V5 conversations across 5 held-out domains.
- **Cross-embedding stability benchmark
  (`scripts/measure_embedding_stability.py`).** Re-runs the V1 gate
  across an arbitrary list of sentence-transformer backends and reports
  per-backend ρ_conv / ρ_turn plus an aggregate "STABLE / UNSTABLE"
  verdict (gate met by every backend AND spread ≤ 0.15). Default
  comparison: `all-MiniLM-L6-v2` (22 M, 384-d) vs `all-MiniLM-L12-v2`
  (33 M, 384-d) vs `all-mpnet-base-v2` (110 M, 768-d). Result on the
  v0.2.0 corpus: ρ_conv = 0.685 / 0.659 / 0.683 (spread 0.026),
  ρ_turn = 0.659 / 0.642 / 0.651 (spread 0.018) — every backend
  clears V1, the 5×-larger model does not move ρ. Closes the
  "embedding-model lock-in unvalidated" audit caveat.
- **Single-process throughput benchmark
  (`scripts/measure_throughput.py`).** Two scenarios — single session
  with growing 50-turn history, and 16 sessions × 25 turns rotated
  round-robin — each excluding a configurable warmup. Reports
  turns/sec, latency p50 / p95 / p99 / max, and peak resident memory.
  Result on Apple Silicon (M-series, 8 P-cores): 11.5 turns/sec
  sustained, p99 = 121 ms, RSS = 609 MB; throughput is flat across
  scenarios so there is no per-session-history scaling cliff up to
  50 turns × 16 active sessions. Closes the "high-QPS scaling
  unvalidated" audit caveat for the single-process unit.
- **Per-event heuristic baseline benchmark
  (`scripts/measure_heuristic_baseline.py`).** Hand-rolled regex /
  threshold detector for every one of the 16 V2 event types, scored
  against the same V2 labels Horizon's engines see. Supports balanced
  per-event sampling (`--per-event-limit N`) so a statistically
  meaningful run finishes in minutes instead of an hour. Result with
  N=60 (960 conversations, ~5,000 turns): Horizon strictly beats the
  baseline on 10 / 16 events, ties on 6 / 16, loses on 0 / 16; macro
  Horizon = 1.00 / 1.00 vs baseline = 0.41 / 0.44. The 9 events with
  baseline 0 / 0 (clarification, comprehension, verbosity,
  convergence, optimal_length, horizon_widening, session_reset,
  broken_reference, light_cone_collapse) are exactly the ones a
  regex cannot recover. Closes the "no per-event competitive
  benchmark" audit caveat.

### Changed
- **Convergence detection rewritten.** `convergence_threshold` now only
  governs IGT slope; the new `convergence_igt_ceiling` (default 0.35)
  governs the absolute IGT requirement. v0.1 reused 0.1 for both,
  which never fired on real conversations.
- **`signal.optimal_length` rewritten.** v0.1 used a t-star projection
  that demanded pathological decay. v0.2 fires when current IGT has
  dropped to ≤ `optimal_length_decay` of the running peak.
- **`checkpoint.comprehension` and `signal.horizon_widening` thresholds
  tightened** so they no longer fire on routine micro-shifts (V2 false
  positives went from 8/8 → 0/8 on the spot check).
- **`signal.session_reset`** now also fires on `degradation_type ==
  "both"` (eviction co-occurring with recoverable drift), not just the
  pure `irreversible_loss` label.
- **`pace_shift_threshold`** lowered from 0.3 → 0.1 — calibrated against
  the V2 corpus where genuine pace inversions land at ~0.12 and noise
  floor sits around 0.01.
- **V5 test harness** now uses real per-turn ratings when the corpus
  provides them, falling back to broadcast conversation-level ratings
  only when absent — eliminating the rank-tie artifact that previously
  collapsed per-turn rho.

### Fixed
- `compute_health` no longer reports "converged" when a new topic
  reappears on the current turn (current IGT is now part of the window).
- `alert.drift` regression in v0.1 where a single off-topic turn after
  a healthy seed could not satisfy monotone-decline (the V2 builder now
  emits 3 progressively-degrading setup turns before any positive
  drift label).
- `signal.session_reset` regression where `degradation_type == "both"`
  silenced the event.
- `alert.contradiction` no longer falls back to coherence when
  `contradiction_method == "claim_tracker"` is active — eliminating
  false positives on negative turns that simply have low consistency.

## [0.1.1] - 2026-04-24

### Added
- `configure()` now accepts the intent's compound parameters
  (`fidelity_weights`, `temporal_weights`, `spacetime_coefficients`) and
  flattens them onto the corresponding `Config` fields per Tech Spec §2.1.
- `configure(embedding_model=...)` now resolves the intent's logical values
  (`local-sentence-transformer`, `openai-text-embedding-3-small`, `custom`)
  to concrete model slugs.
- `export_to(target="arize")` is now implemented — logs per-turn Horizon
  metrics to Arize AX via `arize.pandas.logger` (requires `space_id`,
  `api_key`, `model_id` in the connection dict).
- `pyproject.toml` optional-dependency extras for export adapters:
  `[langsmith]`, `[langfuse]`, `[otel]`, `[arize]`; `[full]` now includes
  all export backends.
- 7 new regression tests covering compound-param flattening, logical
  embedding-model resolution, and the Arize export dispatch.
- `LICENSE` (MIT) at repository root.
- `CHANGELOG.md` (this file).
- `CONTRIBUTING.md` with development setup and test instructions.
- `.gitignore` covering Python, build, virtualenv, and runtime artifacts.
- `docs/README.md` as an entry point to all documentation.

### Changed
- Adopted PyPA-recommended `src/` layout; package source now lives under `src/horizon/`.
- Moved Docker assets to `deploy/docker/`.
- Moved integration guides (Cursor, Claude Desktop, GitHub Copilot) from
  `examples/integrations/` to `docs/integrations/`.
- Moved `E2E_REVIEW.md` to `docs/reviews/E2E_REVIEW.md`.
- Consolidated Horizon documentation under `docs/` (product, spec, reviews).
- `horizon_intent.yaml::export_to.target` now lists all five supported
  targets (`json | langsmith | langfuse | otel | arize`) to match the
  implementation and Tech Spec §13.
- Tech Spec §12 package tree updated to reflect the `src/` layout with
  `deploy/docker/` at the repo root and the `docs/*` subtree.
- Renamed `tests/integration/test_export.py::test_export_json_end_to_end`
  to `test_json_export` to match the intent's verbatim test reference.

### Fixed
- Removed a dead `dataclasses.fields(Config).__class__.__name__` check in
  `FidelityMonitor.new_conversation` metadata filter (behaviour was masked
  by the adjacent correct clause, but the line was a no-op).
- `[mcp]` extra now includes `uvicorn` and `starlette`, so
  `horizon serve --transport sse` works after `pip install horizon-monitor[mcp]`
  (was previously silently broken for the SSE code path).
- `deploy/docker/Dockerfile` now installs Horizon from the local repository
  instead of from PyPI, so `docker compose -f deploy/docker/docker-compose.yml up`
  builds cleanly before an initial PyPI publish.

## [0.1.0] - 2026-04-23

### Added
- First end-to-end release of the Horizon Fidelity Monitor.
- 4D spacetime signal engine (fidelity, temporal, spatial, causal reachability).
- Event system with configurable thresholds (`signal.drift`, `signal.broken_reference`,
  `signal.light_cone_collapse`, `signal.convergence`, etc.).
- Agent framework integrations: OpenAI SDK, Anthropic SDK, LangChain callback,
  OpenAI Agents SDK, MCP server (Cursor / Claude Desktop).
- Export adapters (optional): LangSmith, Langfuse, OpenTelemetry, Arize.
- Comprehensive test suite: unit, integration, performance, validation gates, E2E.
