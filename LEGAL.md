# Legal Notices and Disclaimers

> **Version:** 1.0 · **Effective:** May 11, 2026
>
> This document applies to the Horizon Fidelity Monitor library (`horizon-monitor`),
> the hosted MCP server at `horizon.leocelis.com`, the open-source repository at
> github.com/leocelis/horizon, and any self-hosted deployment of the same codebase.
>
> **This document is not legal advice.** It describes how Horizon is designed, what it
> does and does not do, and what responsibilities remain with the deployer. If you are
> deploying Horizon in a regulated context, consult qualified legal counsel before
> proceeding.
>
> **Related documents** (all incorporated into these notices by reference):
> - [TERMS_OF_SERVICE.md](TERMS_OF_SERVICE.md) — binding terms of use; governs API key
>   acceptance and hosted server access
> - [PRIVACY_POLICY.md](PRIVACY_POLICY.md) — GDPR Art. 13 compliant privacy notice;
>   what data is collected, why, and your rights
> - [DATA_PROCESSING_AGREEMENT.md](DATA_PROCESSING_AGREEMENT.md) — GDPR Art. 28 DPA
>   template for EU enterprise users processing personal data through the hosted server
> - [SECURITY.md](SECURITY.md) — vulnerability disclosure process
>
> **Acceptance:** By requesting an API key, activating an API key, connecting to the
> hosted server, or calling `process_turn()` on any deployment of Horizon, you are
> accepting the Terms of Service. Free and open-source use of the codebase is governed
> by the MIT License; hosted server use additionally requires ToS acceptance.

---

## 1. What Horizon Is — and Is Not

Horizon Fidelity Monitor is a **real-time conversation dynamics library and optional MCP
server** that computes structural metrics on multi-turn AI agent conversations. It is:

- A local Python library that runs on your infrastructure (zero LLM calls, zero external
  network calls by default)
- A collection of MCP tools accessible to AI coding agents (`new_conversation`,
  `process_turn`, `configure_session`)
- An open-source project (MIT License) with an optional hosted server component
- A monitoring and signalling library — it emits signals that **you or your agent
  controller choose how to act on**

Horizon is **not**:

- A certified AI system under Regulation (EU) 2024/1689 (EU AI Act) or any other
  regulatory scheme
- A hallucination prevention system, content safety filter, or output correctness
  guarantor — it monitors conversation structure, not factual accuracy
- A **manipulation, sycophancy, or human-influence detector** — it measures conversation
  *dynamics* (drift, coherence, velocity, temporal desync), not whether the agent is steering,
  flattering, or exploiting the user. High fidelity scores and convergence can be **false comfort**
  during influence attempts. Pair Horizon with agent-faithfulness and human-protection policies
  for those risks.
- A substitute for human review, professional judgment, or domain-specific AI safety
  evaluation
- A guarantee that its signals are accurate, timely, or fit for your specific use case
- A professional service or consulting engagement (see §13)
- **Safe for autonomous use in healthcare, legal advice, financial advice, emergency
  services, or any context where a wrong signal could cause physical, financial, or
  legal harm** — see §4

**Classification note (EU AI Act):** Horizon uses a locally-run sentence-transformer
model (`all-MiniLM-L6-v2`) to produce embeddings and compute semantic metrics. Under the
EU AI Act Article 3(1) definition — a system that "infers...outputs such as predictions,
content, recommendations, or decisions" — Horizon likely qualifies as an **AI system**.
Under guidance current at the effective date of this document, Horizon does not appear
to meet Annex III high-risk criteria in isolation; however, when Horizon is deployed
*within* a high-risk AI pipeline (Annex III: employment screening, credit scoring,
medical diagnosis, critical infrastructure, law enforcement, migration control, justice),
its signals become part of that pipeline and the high-risk obligations fall on **you**
as the deployer of the overall system. This classification is not legally certified, is
not binding on any competent authority, and may be subject to regulatory reinterpretation.

If you are placing Horizon on the EU market as part of a product or service, you are
responsible for conducting your own EU AI Act classification assessment.

Official text: <https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=OJ:L_202401689>

---

## 2. Intellectual Property and Copyright

Copyright © 2025–2026 Leo Celis. All rights reserved except as licensed below.

The Horizon Fidelity Monitor, including but not limited to the Trans-Horizon
Communication Protocol (THCP) theoretical framework, all metric algorithms (IGT, D_JS
proxy, TWR, bipredictability, epsilon_t, causal reachability), all event evaluators,
all MCP tool implementations, and all associated documentation, is the intellectual
property of Leo Celis.

**License:** The source code is licensed under the MIT License (see `LICENSE`). The MIT
License grants you permission to use, copy, modify, merge, publish, distribute,
sublicense, and sell copies of the software. It does **not** transfer ownership of the
underlying IP, trademarks, or methodology; nor does it grant the right to represent
third-party implementations or derivatives as the official Horizon Fidelity Monitor.

**Outputs generated by the library:** Fidelity scores, event signals, trajectory
projections, and other outputs computed by Horizon when operating on your conversations
are derived works that you control in your deployment. Horizon makes no claim to
monitoring outputs you generate using the library.

**Names and branding:** "Horizon," "Horizon Fidelity Monitor," "Trans-Horizon
Communication Protocol," and "THCP" are common law marks under continuous use by Leo
Celis. Unauthorized use of these names in competing products, services, or marketing
materials is not permitted.

> ~ inferred: USPTO and EUIPO trademark registration for "THCP" and "Trans-Horizon
> Communication Protocol" is under consideration. Until registered marks are in place,
> protection is limited to the geographic areas of actual commercial use. Common law
> rights exist but are harder to enforce internationally than a registered mark.

**Open-source dependencies:** Horizon depends on Apache 2.0-licensed libraries
(`sentence-transformers`, `geoip2`, and others). Redistribution of Horizon in binary or
packaged form requires inclusion of applicable NOTICE files from those dependencies per
Apache License Version 2.0 Section 4(c)-(d).

---

## 3. Inherent Limitations of Horizon's Metric System

Horizon's signals are computed from proxy metrics that approximate conversation quality.
The following limitations are architectural properties of the current design — not bugs
that will be fixed in an upcoming release. **Each of these limitations is your risk to
manage in your deployment.**

### 3.1 Proxy Metrics Are Not Ground Truth

Horizon's fidelity score is a composite of proxy metrics (IGT, D_JS, TWR,
bipredictability, epsilon_t) validated against a human quality rating corpus. Validation
results for v0.2.0 on a 5,602-record labelled corpus show per-turn ρ = 0.659 and
per-conversation ρ = 0.685. This means the fidelity score explains approximately 43%
of the variance in human quality ratings at the turn level. The remaining 57% is
unaccounted for.

**Horizon's signals can be wrong.** A high fidelity score does not mean the conversation
is high quality; a low score does not mean it is low quality. The signal is a probabilistic
indicator, not a factual determination.

### 3.2 Embedding Model Truncation at 512 Tokens

The embedding model (`all-MiniLM-L6-v2`) silently truncates input at 512 tokens. For
agent responses longer than approximately 400 words, Horizon computes all metrics on
the truncated text only. This truncation is not flagged in the `TurnResult` output.
In domains with long responses (code generation, legal analysis, detailed explanations),
Horizon's metrics may systematically underrepresent response quality.

### 3.3 Event Signals Require Domain Validation Before Active Use

Horizon ships with **16 event types**, all in `observe` mode by default. Event signals
have been validated on a general-purpose labelled corpus (≥ 0.70 precision and recall
for all 16 events). However, **precision and recall for your specific domain may differ
substantially** — particularly in specialized domains (legal, medical, code review,
financial analysis) where the embedding model is less calibrated.

**Before enabling any event type in `active` mode in a production deployment, you must
validate its precision and recall on a labelled sample from your specific domain and use
case.** Operating an active event without domain validation is at your own risk.

### 3.4 Grounding Hook Breaks the Privacy Invariant

Horizon's core pipeline makes zero external network calls by default. This privacy
invariant is broken the moment a grounding hook is registered via
`register_grounding_hook()`. A registered hook receives raw `human_message` and
`agent_draft` text whenever Horizon's grounding need estimate exceeds the threshold.
If that hook calls an external service (an LLM API, a web search engine, a RAG
system), the raw conversation text is transmitted externally.

**Registering a grounding hook ends the privacy-by-default guarantee.** Any grounding
hook that transmits data to an external service makes you responsible for ensuring that
transmission is covered by appropriate consent, legal basis, and data transfer
safeguards under GDPR, CCPA, and applicable privacy law.

### 3.5 T* (Estimated Optimal Length) Is a Statistical Estimate Only

`estimated_t_star` in the trajectory Resource is computed from IGT trend extrapolation.
At shallow negative IGT trends, this estimate can produce unreliably large values (e.g.,
50,000+ turns). No upper bound or confidence interval is currently attached to T*.
Agent controllers that rely on T* to make continuation decisions should apply their own
sanity bounds and treat T* as a weak heuristic, not a precise forecast.

### 3.6 Spacetime Coefficients Are Uncalibrated

The spacetime interval ds² and `interval_class` (`timelike`/`spacelike`/`lightlike`)
classifications use default coefficients (α = β = γ = δ = 1.0) that have not been
calibrated against human-rated conversation outcome data. These signals are currently
in observe-only mode and should be interpreted as theoretical projections pending
calibration validation.

### 3.7 Circadian Model Applies a Single Chronotype

The circadian cognitive load factor κ(t) models a single "average" chronotype.
Individual users with atypical sleep patterns, users in non-local timezones, or users
working night shifts will receive circadian penalties that do not reflect their actual
cognitive state. The `chronotype_offset` parameter allows manual correction but requires
the deployer to know the user's offset.

---

## 4. High-Stakes Domain Warning

**Horizon must not be used in active/automated mode in any context where an incorrect
signal could cause physical, financial, legal, or psychological harm without human
review of every signal before action.**

Specifically, do NOT enable event types in `active` mode and configure agent controllers
to autonomously act on those events without domain validation and human oversight if
Horizon is deployed in:

- **Healthcare:** medical diagnosis, treatment recommendations, medication dosing,
  clinical decision support, mental health counseling
- **Legal:** legal advice, contract analysis, court filings, compliance determinations
- **Financial:** investment advice, credit decisions, insurance underwriting, financial
  planning
- **Emergency services:** crisis lines, emergency dispatch, safety-critical communications
- **Education:** automated grading, admissions screening, disciplinary processes

In these domains, every Horizon event should be treated as an advisory signal for human
review — not as a trigger for autonomous agent action. The deployer is solely responsible
for implementing appropriate human oversight consistent with EU AI Act Article 14,
NIST AI RMF, and applicable sector-specific regulation.

The $50 / fees paid liability cap in §16 does **not** limit Leo Celis's potential
exposure to tort claims (negligence, products liability) in jurisdictions where such
caps are unenforceable in consumer or harm contexts. Get product liability insurance
before deploying Horizon in any of the above domains.

---

## 5. Performance Claims — Scope and Substantiation

Horizon's public materials reference the following quantified claims. The scope and
evidentiary basis for each is disclosed here:

| Claim | Source | Scope | Limitation |
|-------|--------|-------|------------|
| "+15.7% composite quality lift" | A/B evaluation, 4 synthetic scenarios, 200 turns | Controlled lab conditions using reference agent controllers with optimized event handlers | Not validated in production deployments or with real users |
| "87% fewer hallucination events" | A/B evaluation, 4 synthetic scenarios | Applies when `signal.grounding_required` was activated and the reference hook was invoked | Requires the grounding hook to be configured; passive monitoring alone does not produce this result |
| "39% accuracy degradation after 5 turns" | [Laban et al., ICLR 2026 Best Paper](https://iclr.cc/virtual/2026/poster/10009146) | Multi-turn evaluation across 15 models (Microsoft Research) | Horizon did not conduct this research; cite the original paper for compliance purposes |
| "ρ = 0.685 (per-conversation), ρ = 0.659 (per-turn)" | V0.2.0 validation corpus (5,602 labelled records) | General-purpose English conversation corpus | Domain-specific results will vary; see §3.3 |
| "All 16 events ≥ 0.70 precision / recall" | V0.2.0 validation corpus | General-purpose corpus only | Domain-specific validation required before activating events in production |
| "+202.4% rho lift over heuristic baseline" | V0.2.0 heuristic baseline comparison | General-purpose corpus | Not validated across all deployment contexts |

Full evidence: [`docs/reviews/V0_2_0_EVIDENCE.md`](docs/reviews/V0_2_0_EVIDENCE.md)

The FTC has stated that AI product claims must be substantiated before use in marketing.
Horizon does not guarantee that the figures above will replicate in your specific domain,
model, or deployment configuration. Do not represent these figures as applicable to your
system without conducting your own evaluation.

**Source:** <https://www.ftc.gov/business-guidance/blog/2023/02/keep-your-ai-claims-check>
**Source:** <https://www.ftc.gov/news-events/news/press-releases/2024/09/ftc-announces-crackdown-deceptive-ai-claims-schemes>

---

## 6. Hosted Server — Data Transmission and Privacy

When you use the hosted Horizon MCP server at `horizon.leocelis.com`:

### 6.1 What is transmitted

`new_conversation()` transmits your metadata dict and configuration. `process_turn()`
transmits `session_id`, `human_message`, and `agent_response` over HTTPS. This content
is processed to execute the metrics pipeline and return a `TurnResult`.

**The core library does not retain raw message text beyond the active request.** Embeddings
computed from the messages may be temporarily held in memory as part of session state.
If `PersistentDynamicsStore` is enabled, per-turn metadata (scores, event types,
health status) is written to SQLite — **not** the raw message text.

**Warning:** If a grounding hook is registered and calls an external service, raw message
text is transmitted to that service. See §3.4.

### 6.2 Where it is processed

The hosted server runs on **DigitalOcean App Platform (US East region)**. Session state
is Redis-backed. Embedding computation uses the locally bundled `all-MiniLM-L6-v2`
model — no OpenAI or third-party embedding API is called by the hosted server.

**If you are in the European Union:** Transmitting personal data through tool arguments
constitutes an international data transfer from the EU to the United States under GDPR
Chapter V (Articles 44–46). No Standard Contractual Clauses (SCCs) or Data Processing
Agreement between Horizon and its users currently exists. **EU controllers must not
transmit personal data through hosted-server tool arguments until SCCs or equivalent
safeguards are in place.** Use a self-hosted deployment for any processing involving
personal data of EU residents.

**Source:** <https://www.edpb.europa.eu/sme-data-protection-guide/international-data-transfers_en>

### 6.3 Controller/processor roles

For the purposes of GDPR Article 28: Horizon operates the hosted server as a
**processor** of any personal data you transmit. You remain the **controller** for that
data. A signed Data Processing Agreement is required before EU enterprise customers may
transmit personal data. Contact [leo@leocelis.com](mailto:leo@leocelis.com) to request a DPA.

### 6.4 Sub-processors

| Sub-processor | Role | DPA |
|---------------|------|-----|
| DigitalOcean, Inc. | Infrastructure hosting | <https://www.digitalocean.com/legal/data-processing-agreement> |
| Upstash, Inc. | Redis session storage | <https://upstash.com/trust/data-processing-addendum.pdf> |

### 6.5 What you must not transmit

Do not transmit the following through hosted-server tool arguments:

- **Personal data** (names, emails, government IDs, health data, or any data relating
  to an identified or identifiable person) — no SCC or DPA is in place for EU transfers
- **Sensitive personal data** — health, genetic, biometric, political, religious, racial,
  or sexual orientation data — prohibited without Art. 9 legal basis
- **Trade secrets, credentials, API keys, or confidential business information**

### 6.6 Self-hosted alternative

All processing remains on your infrastructure in a self-hosted deployment. Self-hosting
instructions: [`deploy/`](deploy/) directory and [`CONTRIBUTING.md`](CONTRIBUTING.md).

---

## 7. PersistentDynamicsStore — Data Handling Warning

The optional `PersistentDynamicsStore` (SQLite-backed) records the following per turn:
`session_id`, `user_id`, `turn_count`, `health_status`, `events` (JSON blob),
`fidelity_score`, `igt_value`, `divergence_score`, `twr_value`, `consistency_score`.

**If `user_id` correlates to a real person's identity**, this stored data is **personal
data** under GDPR Article 4(1) and California Civil Code § 1798.140(v). As the deployer:

- You are the data **controller** for data stored in your SQLite instance
- You must implement a legal basis under GDPR Article 6 for that processing
- You must be able to fulfill data subject rights (GDPR Art. 15 access, Art. 17 erasure,
  Art. 18 restriction) — `PersistentDynamicsStore` includes `delete_user_data(user_id)`
  (removes all sessions and turn snapshots for a user) and `anonymize_session(session_id)`
  (nullifies the user_id link while retaining aggregate analytics). Use these methods to
  fulfill erasure requests. Verify that no residual data remains in any backup or replica
- You must protect the database file with appropriate permissions (recommended: `0o600`)
  and encryption at rest — the library does not encrypt the SQLite file by default
- If the database file is breached: GDPR Art. 33 requires you to notify the supervisory
  authority within 72 hours; Florida FIPA § 501.171 requires notification within 30
  days if 500+ Florida residents are affected

**Pseudonymize `user_id` by default.** Pass a hashed or randomly generated identifier
rather than an email, name, or real account ID.

---

## 8. Third-Party Services and Service Availability

### 8.1 Third-party service disclaimer

The hosted server depends on DigitalOcean App Platform and Redis (Upstash). Horizon has
no control over the availability, terms, pricing, regulatory status, or data handling
of these providers. Horizon is not liable for any interruption, data loss, or legal
development attributable to third-party providers.

### 8.2 MaxMind GeoIP2 (optional spatial signals)

Spatial signals (`location_class`, `spatial_constraint`) require the optional `geoip2`
dependency and a MaxMind database file. MaxMind GeoLite2 is subject to the Creative
Commons Attribution-ShareAlike 4.0 license. MaxMind GeoIP2 commercial databases require
a separate commercial license from MaxMind. Horizon makes no representation that any
particular license tier is included. You are responsible for complying with MaxMind's
End User License Agreement for the database tier you use.

MaxMind EULA: <https://www.maxmind.com/en/end-user-license-agreement>

### 8.3 No uptime guarantee

The hosted server is provided on a best-effort basis. There is no SLA, no uptime
guarantee, and no planned maintenance window commitment. The self-hosted path is
recommended for any workflow that requires guaranteed availability.

---

## 9. Your Responsibilities as a Deployer

When you use Horizon to build AI-powered systems, you are the **deployer** of those
systems. Horizon's role as a library does not transfer, share, or reduce your legal
obligations.

### 9.1 EU AI Act (Regulation (EU) 2024/1689)

If you deploy Horizon as part of an Annex III high-risk AI system, your system bears
the full obligations of Articles 9–16 regardless of which libraries it uses. Horizon's
signals can be part of your Article 13 (transparency) documentation only if you have
validated their accuracy in your specific domain (see §3.3).

High-risk AI obligations apply as of **August 2, 2026**.

**Source:** <https://artificialintelligenceact.eu/article/25/>

### 9.2 GDPR (Regulation (EU) 2016/679)

If your AI system processes personal data of EU residents using Horizon's conversation
monitoring, you are the data controller. Horizon's privacy invariant (zero external
calls by default) helps with GDPR Article 25 (data protection by design) — but only in
the absence of a grounding hook and only in self-hosted deployments.

### 9.3 CCPA/CPRA (Cal. Civ. Code §§ 1798.100–1798.199.100)

If your business meets CCPA applicability thresholds and Horizon's `PersistentDynamicsStore`
stores data linked to California consumers, your CCPA obligations apply. Horizon provides
no CCPA compliance tooling.

### 9.4 Colorado AI Act (Colo. Rev. Stat. § 6-1-1701)

Effective June 30, 2026, Colorado requires developers and deployers of high-risk AI
systems making consequential decisions (employment, housing, financial, insurance,
education, healthcare, legal) to conduct discrimination impact assessments and provide
consumers the right to appeal. These obligations apply to you if your deployment affects
Colorado residents.

---

## 10. Academic Citations and Theoretical Framework

The THCP theoretical framework (design motivation documented in [`docs/product/THCP_FIDELITY_MONITOR_PRD.md`](docs/product/THCP_FIDELITY_MONITOR_PRD.md))
draws on a large bibliography in product appendices and discusses
self-reference / no-go results as **background motivation only** — not as mathematical proof
that LLMs cannot self-monitor. Horizon's product positioning is empirical: external measurement
because introspection is limited and unreliable, not because of an impossibility theorem.
All citations represent the authors' characterization of those works at the time of writing and
have not been independently audited for accuracy.

If you intend to cite the THCP framework in commercial materials, peer review, or
regulatory documentation, verify every citation against the original source before use.
Horizon does not guarantee that cited papers say exactly what they are characterized
as saying, that preprints have not been retracted, or that all cited theorems have
survived peer review.

---

## 11. Sensitive Data and Version Control

Private planning and research documents are maintained outside this repository.
The `.gitignore` excludes `*.sqlite` and `horizon.db` by default. These
protections do not automatically transfer when you fork or clone the repository into a
new project. Verify that your SQLite database and any private configuration files are
excluded from source control in every repository that contains a Horizon deployment.

---

## 12. No Professional Relationship

Use of Horizon — whether hosted or self-hosted, free or paid, under any licensing
arrangement — does not create a professional services relationship of any kind between
you and Leo Celis or the Horizon project. In particular:

- No attorney-client relationship, legal advisory relationship, or privileged
  communication arises from using Horizon or reading any Horizon documentation
- No engineering consulting, systems integration, or professional IT services
  relationship arises from using Horizon in your development workflow
- No fiduciary duty, duty of care, or advisory duty attaches to Horizon's role as a
  library publisher

If you require professional advice — legal, compliance, engineering, or otherwise —
engage a qualified professional independently.

---

## 13. Indemnification

**To the maximum extent permitted by applicable law**, you agree to defend, indemnify,
and hold harmless Leo Celis, the Horizon project, its contributors, and its maintainers
from and against any and all claims, damages, obligations, losses, liabilities, costs,
or expenses (including reasonable legal fees) arising from:

1. Your use of Horizon or the hosted server in any manner
2. Any AI system, workflow, product, or service you build using Horizon
3. Your decision to enable any event type in `active` mode and any agent behavior that
   results from Horizon signals, regardless of whether the signal was accurate
4. Your registration and use of any grounding hook, including data transmitted by that
   hook to external services
5. Your use of `PersistentDynamicsStore` with personal data, including any failure to
   fulfill data subject rights obligations
6. Your violation of any applicable law in connection with your use of Horizon, including
   GDPR, CCPA/CPRA, EU AI Act, or the FTC Act
7. Any claim by a third party that your AI system caused harm or violated rights
8. Your misrepresentation of Horizon's capabilities, validation status, or coverage to
   any third party, customer, regulator, or auditor

This indemnification obligation survives termination or discontinuation of your use of Horizon.

---

## 14. No Warranty

THE HORIZON FIDELITY MONITOR LIBRARY, HOSTED MCP SERVER, MCP TOOLS, EVENT EVALUATORS,
METRIC ALGORITHMS, SPACETIME SIGNALS, AND ALL ASSOCIATED MATERIALS ARE PROVIDED "AS IS,"
WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO:

- WARRANTIES OF MERCHANTABILITY OR FITNESS FOR A PARTICULAR PURPOSE
- ACCURACY, COMPLETENESS, OR RELIABILITY OF FIDELITY SCORES, EVENT SIGNALS, OR
  TRAJECTORY ESTIMATES
- THAT SIGNALS WILL BE ACCURATE IN YOUR SPECIFIC DOMAIN, MODEL, OR DEPLOYMENT
  CONFIGURATION
- THAT ACTIVATING EVENTS WILL IMPROVE CONVERSATION QUALITY IN YOUR USE CASE
- REGULATORY COMPLIANCE READINESS, CONFORMITY ASSESSMENT ADEQUACY, OR AUDIT TRAIL
  SUFFICIENCY
- UPTIME, AVAILABILITY, OR UNINTERRUPTED SERVICE
- SECURITY AGAINST UNAUTHORIZED ACCESS OR DATA BREACH OF THE SQLITE STORE
- NON-INFRINGEMENT OF THIRD-PARTY INTELLECTUAL PROPERTY RIGHTS

**USE OF HORIZON DOES NOT GUARANTEE THAT YOUR AI SYSTEM WILL COMPLY WITH ANY LAW,
REGULATION, OR STANDARD**, INCLUDING BUT NOT LIMITED TO THE EU AI ACT, GDPR, CCPA/CPRA,
NIS2, THE CYBER RESILIENCE ACT, OR ANY SECTOR-SPECIFIC REGULATION.

**ALL USES OF HORIZON — INCLUDING USES AND RISKS NOT INDIVIDUALLY ENUMERATED IN THIS
DOCUMENT — ARE AT YOUR OWN RISK.** This document identifies known and foreseeable risks;
it is not an exhaustive enumeration of all risks you may encounter.

---

## 15. Limitation of Liability

TO THE MAXIMUM EXTENT PERMITTED BY APPLICABLE LAW:

**15.1** IN NO EVENT SHALL LEO CELIS, THE HORIZON PROJECT, ITS CONTRIBUTORS, OR ITS
MAINTAINERS BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE
DAMAGES — INCLUDING BUT NOT LIMITED TO LOSS OF DATA, LOSS OF PROFITS, LOSS OF BUSINESS
OPPORTUNITY, REGULATORY FINES OR PENALTIES, BUSINESS INTERRUPTION, REPUTATIONAL HARM,
OR HARM CAUSED TO END USERS OF YOUR AI SYSTEM — ARISING OUT OF OR IN CONNECTION WITH
YOUR USE OF HORIZON, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGES.

**15.2 AGGREGATE LIABILITY CAP:** HORIZON'S TOTAL AGGREGATE LIABILITY TO YOU FOR ALL
CLAIMS ARISING OUT OF OR RELATED TO YOUR USE OF HORIZON — INCLUDING DIRECT DAMAGES —
SHALL NOT EXCEED THE GREATER OF (a) THE TOTAL FEES ACTUALLY PAID BY YOU TO HORIZON IN
THE TWELVE MONTHS IMMEDIATELY PRECEDING THE CLAIM, OR (b) USD $50. FOR USERS WHO HAVE
PAID NOTHING (INCLUDING ALL FREE-TIER AND OPEN-SOURCE USERS), THIS CAP IS USD $0.

**15.3** NOTHING IN THIS SECTION LIMITS LIABILITY FOR FRAUD OR INTENTIONAL MISCONDUCT
ON THE PART OF LEO CELIS.

**15.4** SOME JURISDICTIONS DO NOT ALLOW THE EXCLUSION OF CERTAIN WARRANTIES OR THE
LIMITATION OF CERTAIN TYPES OF DAMAGES. WHERE SUCH RESTRICTIONS APPLY, THE EXCLUSIONS
AND LIMITATIONS ABOVE APPLY TO THE FULLEST EXTENT PERMITTED BY APPLICABLE LAW.

**15.5 TORT CLAIMS:** The liability cap in §15.2 applies to contract-based claims. It
does not automatically bar negligence or products liability tort claims in jurisdictions
where such caps are unenforceable in consumer contracts or where harm is foreseeable.
Deployers who activate Horizon events in high-stakes domains without adequate human
oversight should obtain product liability insurance independently.

---

## 16. Governing Law and Jurisdiction

This document and all disputes arising from your use of Horizon are governed by the
laws of the **State of Florida, United States**, without regard to its conflict-of-law
provisions.

Any legal action or proceeding must be brought exclusively in the state or federal courts
located in **Broward County, Florida, United States.** You irrevocably consent to the
personal jurisdiction and venue of those courts.

**EU users note:** Nothing in this section limits mandatory consumer or data-subject
rights available under EU law, including rights under GDPR, the EU AI Act, or applicable
EU consumer protection law. EU-resident users retain those rights regardless of this
choice-of-law clause.

---

## 17. Security Vulnerabilities

To report a security vulnerability in Horizon (including the hosted server), follow the
responsible disclosure process in [`SECURITY.md`](SECURITY.md). Do not open a public
GitHub issue for security vulnerabilities.

For potential personal data breaches involving the hosted server or a self-hosted
SQLite store, contact [leo@leocelis.com](mailto:leo@leocelis.com) immediately. If you
are an EU controller and the breach triggers GDPR Article 33 obligations, do not wait
for Horizon's response — begin your 72-hour supervisory authority notification process
immediately using the information available to you.

**Full legal document set:**

| Document | Purpose |
|----------|---------|
| [TERMS_OF_SERVICE.md](TERMS_OF_SERVICE.md) | Binding terms of use and acceptance |
| [PRIVACY_POLICY.md](PRIVACY_POLICY.md) | GDPR Art. 13 privacy notice |
| [DATA_PROCESSING_AGREEMENT.md](DATA_PROCESSING_AGREEMENT.md) | GDPR Art. 28 DPA (request for EU enterprise) |
| [SECURITY.md](SECURITY.md) | Vulnerability disclosure process |
| [LICENSE](LICENSE) | MIT License (open-source code) |

---

## 18. Changes to This Document

The version number and effective date at the top of this file reflect the last revision.
Changes are tracked in `CHANGELOG.md`. If you rely on this document for compliance
purposes, monitor the repository for changes or periodically review the effective date.

---

## 19. Reference Index

| Source | Official URL | Verified |
|--------|-------------|---------|
| EU AI Act (Regulation 2024/1689) — full text | <https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=OJ:L_202401689> | 2026-05-11 |
| EU AI Act — Article 3 (definitions) | <https://artificialintelligenceact.eu/article/3/> | 2026-05-11 |
| EU AI Act — Article 14 (human oversight) | <https://artificialintelligenceact.eu/article/14/> | 2026-05-11 |
| EU AI Act — Article 25 (deployer responsibilities) | <https://artificialintelligenceact.eu/article/25/> | 2026-05-11 |
| EU AI Act — Annex III (high-risk categories) | <https://artificialintelligenceact.eu/annex/3/> | 2026-05-11 |
| EU Product Liability Directive 2024/2853 | <https://eur-lex.europa.eu/eli/dir/2024/2853/oj> | 2026-05-11 |
| GDPR — full text (EUR-Lex) | <https://eur-lex.europa.eu/eli/reg/2016/679/oj> | 2026-05-11 |
| GDPR Article 17 — Right to Erasure | <https://gdpr-info.eu/art-17-gdpr/> | 2026-05-11 |
| GDPR Article 33 — Breach Notification | <https://gdpr.eu/article-33-notification-of-a-personal-data-breach/> | 2026-05-11 |
| GDPR Chapter V — International Transfers (EDPB) | <https://www.edpb.europa.eu/sme-data-protection-guide/international-data-transfers_en> | 2026-05-11 |
| Standard Contractual Clauses (European Commission) | <https://commission.europa.eu/law/law-topic/data-protection/international-dimension-data-protection/standard-contractual-clauses-scc_en> | 2026-05-11 |
| FTC Act § 45 (15 U.S.C.) | <https://www.ftc.gov/legal-library/browse/statutes/federal-trade-commission-act> | 2026-05-11 |
| FTC — "Keep Your AI Claims in Check" (Feb 2023) | <https://www.ftc.gov/business-guidance/blog/2023/02/keep-your-ai-claims-check> | 2026-05-11 |
| FTC Operation AI Comply (Sept 2024) | <https://www.ftc.gov/news-events/news/press-releases/2024/09/ftc-announces-crackdown-deceptive-ai-claims-schemes> | 2026-05-11 |
| FDUTPA (Florida Statutes Ch. 501, Part II) | <http://www.leg.state.fl.us/Statutes/index.cfm?App_mode=Display_Statute&StatuteYear=2024&Title=-%3E2024-%3EChapter+501-%3EPart+II> | 2026-05-11 |
| Florida FIPA (Fla. Stat. § 501.171) | <http://www.leg.state.fl.us/Statutes/index.cfm?App_mode=Display_Statute&URL=0500-0599/0501/Sections/0501.171.html> | 2026-05-11 |
| CCPA/CPRA statute | <https://cppa.ca.gov/regulations/pdf/ccpa_statute.pdf> | 2026-05-11 |
| Colorado SB 24-205 | <https://leg.colorado.gov/bills/SB24-205> | 2026-05-11 |
| MaxMind End User License Agreement | <https://www.maxmind.com/en/end-user-license-agreement> | 2026-05-11 |
| Apache License 2.0 | <https://www.apache.org/licenses/LICENSE-2.0> | 2026-05-11 |
| NIST AI RMF 1.0 | <https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-1.pdf> | 2026-05-11 |

---

*Version 1.0 — Initial release.*

*This document is not legal advice. Consult qualified legal counsel before making
compliance or legal decisions based on this text.*
