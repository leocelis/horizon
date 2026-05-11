# Privacy Policy

> **Version:** 1.0 · **Effective:** May 11, 2026
>
> This Privacy Policy applies to the Horizon Fidelity Monitor website
> (`horizon.leocelis.com`), the hosted MCP server (`horizon.leocelis.com`), and all
> associated services (collectively, the "Service"). It does **not** apply to
> self-hosted deployments of the Horizon codebase on your own infrastructure — in those
> deployments, you control all data and you are the data controller.
>
> This Policy is provided in compliance with **GDPR Article 13** (information to be
> provided at the time personal data is collected) and **FTC Act Section 5** (privacy
> and confidentiality commitments).

**Data Controller:**
Leo Celis
[leo@leocelis.com](mailto:leo@leocelis.com)
horizon.leocelis.com

*Horizon has not appointed a Data Protection Officer (DPO). The controller contact
above handles all data protection inquiries.*

---

## 1. What Data We Collect and Why

### 1.1 Hosted MCP server — tool call arguments

**What:** Every call to a Horizon MCP tool (`new_conversation`, `process_turn`,
`configure_session`) transmits the arguments you provide. `process_turn` specifically
receives `session_id`, `human_message`, and `agent_response`.

**Why:** To execute the conversation dynamics pipeline and return a `TurnResult`.

**Legal basis (GDPR Art. 6):** Legitimate interests (Art. 6(1)(f)) — processing is
necessary to provide the service you requested. For users in a contractual relationship
with Horizon, performance of a contract (Art. 6(1)(b)).

**Retention of message content:** Raw message text (`human_message`, `agent_response`)
is **not** retained in Horizon's application storage beyond the active request. The
text is used only to compute embeddings and metrics in memory. Once the request
completes, the raw text is discarded.

**Session metadata retained in memory:** `session_id`, turn count, computed embeddings
(not raw text), metric history, and event log are held in process memory for the
duration of the session (until the server restarts or the session is evicted). Server
restarts clear all session state.

**Warning:** Do not transmit personal data (names, emails, health information, or
any data relating to an identified or identifiable person) through `human_message` or
`agent_response` arguments. The hosted server is not designed for personal data
processing. See §7.

### 1.2 PersistentDynamicsStore (if enabled)

If the optional SQLite persistence layer is enabled, the following is written to disk
per turn: `session_id`, `user_id` (as you provide it), `turn_count`, `health_status`,
`events` (JSON blob of signal metadata), `fidelity_score`, `igt_value`,
`divergence_score`, `twr_value`, `consistency_score`.

**Raw message text is never written to the SQLite store.**

**On the hosted server:** Persistent storage is not enabled in the default hosted
deployment. No SQLite data is written for standard hosted-server usage.

**On self-hosted deployments:** If you enable `PersistentDynamicsStore`, you are the
controller for data written to that database. Horizon's Privacy Policy does not apply
to data stored in self-hosted SQLite instances. You are responsible for appropriate
access controls, encryption at rest, retention limits, and GDPR data subject rights
for data stored in your deployment.

### 1.3 API key issuance (GitHub Discussions)

**What:** When you request an API key via a GitHub Discussion, GitHub collects your
GitHub username and the content of your request. Horizon receives: your GitHub username
and any contact information you voluntarily provide.

**Why:** To issue and manage your API key.

**Legal basis (GDPR Art. 6):** Performance of a contract / pre-contractual steps
(Art. 6(1)(b)).

**Retention:** API key records are kept for as long as the key is active. Revoked or
expired keys are deleted from active records within 90 days.

### 1.4 Operational logs and infrastructure metrics

**What:** DigitalOcean App Platform and Redis (Upstash) generate infrastructure logs
as a normal part of operations. These logs may include: timestamps, request sizes,
IP addresses, and error codes. They do **not** include the content of `human_message`
or `agent_response` (tool argument bodies are not logged at the infrastructure level
in the default configuration).

**Why:** Infrastructure reliability, debugging, and security monitoring.

**Legal basis (GDPR Art. 6):** Legitimate interests (Art. 6(1)(f)) — necessary for
secure and reliable operation of the service.

**Retention:** Infrastructure logs are retained according to DigitalOcean and Upstash
policies (typically 30 days).

### 1.5 Website (horizon.leocelis.com)

The Horizon website is a static HTML file served by DigitalOcean App Platform. No
analytics, tracking pixels, cookies, or fingerprinting scripts are included on the
website. The website does not collect any personal data directly.

Your IP address may appear in DigitalOcean's access logs as described in §1.4.

---

## 2. Grounding Hook — Privacy Invariant and Its Limits

Horizon's core pipeline is **privacy by default**: zero external network calls are made
during metric computation. This guarantee holds when no grounding hook is registered.

**If you register a grounding hook via `register_grounding_hook()`:**

The hook receives the raw `human_message` and `agent_draft` text when Horizon's
grounding need estimate exceeds the threshold. If your hook transmits that text to an
external service (e.g., an LLM API, a web search engine, a RAG pipeline), the
privacy-by-default guarantee **no longer applies** for that deployment.

For deployed applications that use a grounding hook:
- You must disclose to end users that their conversation content may be sent to external
  services for grounding purposes
- You must have a lawful basis under GDPR Article 6 (and Art. 9 if sensitive data is
  involved) for each external transmission
- You must ensure that any third-party service receiving the data provides appropriate
  privacy guarantees and, for EU data subjects, appropriate transfer safeguards (SCCs
  or adequacy decision)

Horizon's hosted server does not currently use a grounding hook in the default
configuration. No conversation text is transmitted externally by the hosted server.

---

## 3. How We Use Data

We use the data described above only for:
1. Executing the conversation dynamics pipeline and returning results to you
2. Maintaining session state during an active monitoring session
3. Operating and debugging the hosted server infrastructure
4. Managing API key issuance and access control

We do **not** use your conversation data for:
- Training or fine-tuning any AI or embedding model
- Building behavioral profiles of your end users
- Analytics, advertising, or product research
- Sharing with third parties beyond the sub-processors listed in §4

---

## 4. Sub-processors

| Sub-processor | Country | Role | Privacy documentation |
|---------------|---------|------|-----------------------|
| DigitalOcean, Inc. | United States | Infrastructure hosting, App Platform | <https://www.digitalocean.com/legal/privacy-policy> / <https://www.digitalocean.com/legal/data-processing-agreement> |
| Upstash, Inc. | United States | Redis session storage | <https://upstash.com/trust/privacy.pdf> |

**Note on EU data transfers:** Both sub-processors are US-based. Transmitting personal
data to the hosted server constitutes an international data transfer under GDPR Chapter V
(Articles 44–46). No Standard Contractual Clauses (SCCs) are currently in place between
Horizon and its users. **EU data controllers must not transmit personal data to the hosted
server until SCCs or equivalent safeguards are executed.** Use a self-hosted deployment
for personal data processing.

This is a known compliance gap. Contact [leo@leocelis.com](mailto:leo@leocelis.com) to
initiate an SCC agreement if your organization requires one.

---

## 5. Data Subject Rights (GDPR)

If you are an EU resident and personal data about you has been processed through the
hosted Horizon service, you have the following rights under GDPR:

| Right | Legal basis | How to exercise |
|-------|-------------|-----------------|
| Access (Art. 15) | Right to know what data is held about you | Email [leo@leocelis.com](mailto:leo@leocelis.com) |
| Rectification (Art. 16) | Right to correct inaccurate data | Email [leo@leocelis.com](mailto:leo@leocelis.com) |
| Erasure (Art. 17) | Right to be forgotten | Email [leo@leocelis.com](mailto:leo@leocelis.com) |
| Restriction (Art. 18) | Right to restrict processing | Email [leo@leocelis.com](mailto:leo@leocelis.com) |
| Portability (Art. 20) | Right to receive your data in portable format | Email [leo@leocelis.com](mailto:leo@leocelis.com) |
| Object (Art. 21) | Right to object to legitimate-interests processing | Email [leo@leocelis.com](mailto:leo@leocelis.com) |

**Response time:** We respond to data subject requests within **30 days**. Complex
requests may require an extension; we will notify you if an extension is needed.

**Supervisory authority:** You have the right to lodge a complaint with your national
data protection supervisory authority. A list of EU supervisory authorities is available
at: <https://www.edpb.europa.eu/about-edpb/about-edpb/members_en>

**Note on session-level data:** Because Horizon does not retain raw message text, and
because the default hosted deployment does not use `PersistentDynamicsStore`, there is
typically very little personal data held by the hosted server at rest. Erasure requests
for active session state are handled by clearing the session from memory (effectively
immediate given that sessions are ephemeral and clear on server restart).

---

## 6. CCPA Rights (California)

If you are a California resident, you have the following rights under the California
Consumer Privacy Act (CCPA/CPRA, Cal. Civ. Code § 1798 et seq.):

- **Right to Know** (§ 1798.110) — what personal information is collected, used,
  disclosed, or sold
- **Right to Delete** (§ 1798.105) — request deletion of personal information
- **Right to Opt-Out** (§ 1798.120) — Horizon does not sell or share personal
  information; this right is not applicable
- **Right to Non-Discrimination** — exercising CCPA rights will not result in different
  service treatment

To exercise these rights: email [leo@leocelis.com](mailto:leo@leocelis.com) from the
email address associated with your API key request.

---

## 7. What You Must Not Transmit

The hosted server is not designed for personal data processing. Do not transmit:

- **Personal data** (names, emails, government IDs, IP addresses in message content,
  biometric data, or any data attributable to an identified or identifiable natural person)
- **Sensitive personal data** under GDPR Art. 9 (health, genetic, biometric, political,
  religious, racial/ethnic origin, or sexual orientation data)
- **Protected health information (PHI)** under HIPAA (Horizon is not a HIPAA Business
  Associate and cannot be used in HIPAA-covered workflows)
- **Payment card data (PCI DSS scope)** — Horizon does not process payments but you
  must ensure card data is never included in conversation content
- **Credentials, API keys, tokens, or secrets** of any kind

---

## 8. Security

Horizon implements reasonable security measures for the hosted server:

- All traffic is encrypted in transit (HTTPS/TLS)
- API keys are required for all hosted server access
- Infrastructure is hosted on DigitalOcean App Platform with built-in network isolation
- Session state in Redis is isolated per API key

Despite these measures, no system is completely secure. If you believe there has been
a security incident involving your API key or data transmitted to the hosted server,
contact [leo@leocelis.com](mailto:leo@leocelis.com) immediately and follow the
responsible disclosure process in [`SECURITY.md`](SECURITY.md).

**For self-hosted deployments:** You are responsible for the security of your
Horizon instance, including SQLite file permissions, network access controls, and
backup encryption. See LEGAL.md §7 for specific recommendations.

---

## 9. Changes to This Policy

Material changes to this Policy will be reflected in an updated version number and
effective date at the top of this document, and noted in `CHANGELOG.md`. Continued use
of the hosted server after the effective date constitutes acceptance of the revised Policy.

---

## 10. Contact

For all privacy questions, data subject requests, or SCC/DPA inquiries:

Leo Celis
[leo@leocelis.com](mailto:leo@leocelis.com)
Subject lines: "Privacy Request", "GDPR Request", "CCPA Request", or "DPA Request"

---

*This document is not legal advice. Consult qualified legal counsel before deploying
Horizon in any context involving personal data processing.*
