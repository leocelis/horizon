# Terms of Service

> **Version:** 1.1 · **Effective:** July 19, 2026
>
> These Terms of Service ("Terms") govern your access to and use of the Horizon Fidelity
> Monitor library (`horizon-monitor`), the hosted MCP server at `horizon.leocelis.com`,
> the website at `horizon.leocelis.com`, and the open-source repository at
> github.com/leocelis/horizon (collectively, the "Service").
>
> **By requesting an API key, activating an API key, connecting to the hosted server,
> calling `process_turn()` on any Horizon deployment, or installing the `horizon-monitor`
> package and using it in a commercial context, you agree to be bound by these Terms.**
> If you do not agree, do not use the Service.
>
> For organizations: the person accepting these Terms represents and warrants that they
> have authority to bind the organization, and "you" refers to that organization.

**Provider:** Leo Celis ("Horizon", "we", "us")
**Contact:** [leo@leocelis.com](mailto:leo@leocelis.com)
**Repository:** https://github.com/leocelis/horizon

---

## 1. The Service

Horizon provides a real-time conversation dynamics monitoring library and MCP server.
The Service is available as:

- **Open-source library** — MIT License via github.com/leocelis/horizon (self-hosted
  path; MIT License governs the code, these Terms govern commercial use)
- **Hosted MCP server** — managed MCP server at `horizon.leocelis.com`, accessed with
  a Bearer API key (hosted path; these Terms govern all access)

The hosted server is provided on a best-effort basis. There is no uptime guarantee,
no SLA, and no commitment to minimum availability. See §8.

---

## 2. Eligibility and API Keys

**Age:** You must be at least 18 years old to use the hosted server or request an API key.

**API keys:** Access to the hosted server requires a Bearer token issued by Horizon.
Keys are personal or per-organization — do not share them publicly or commit them to
source control. You are responsible for all activity under your key.

**Identity and accountability:** Key requests must come from an identifiable requester —
a real GitHub account in good standing, and/or a verifiable email address. Horizon may
decline anonymous, throwaway, or unverifiable requests at its sole discretion. Horizon
retains the requester identity supplied at issuance (associated with the key's hash, not
the key itself) for the purpose of abuse response — including revocation and, where
necessary, reporting to the relevant platform (e.g. GitHub) using that issuance record. A
key that cannot be traced back to an accountable requester will not be issued.

**Key security:** If you believe your API key has been compromised, notify
[leo@leocelis.com](mailto:leo@leocelis.com) immediately. Revoke the key if possible and
audit any recent activity performed under it.

**Technical limits (enforced, not just contractual):** The hosted server rate-limits each
key (default 120 requests/minute, burst 20) and caps each key at 50 concurrent sessions,
both configurable server-side and detailed in [SECURITY.md](SECURITY.md#known-security-considerations-for-self-hosted-deployments).
Sessions are isolated per key — one key cannot read or mutate another key's session data
or configuration, including via `configure_session`'s global mode. Exceeding the rate
limit returns HTTP 429; you must back off per the `Retry-After` header rather than retry
immediately.

**Alpha status:** The hosted server is in private alpha. Keys are distributed at Leo
Celis's sole discretion. No right to continued access, no right to a key, and no
commitment to maintain the hosted service beyond reasonable notice of discontinuation.

---

## 3. Acceptable Use

You may use the Service for any lawful purpose consistent with these Terms. You must not:

1. Use the Service to process, transmit, or store **personal data** in violation of
   applicable privacy law, including GDPR and CCPA/CPRA. See §6 and the Privacy Policy.
2. Transmit **personal data, sensitive personal data, trade secrets, credentials, or
   API keys** through hosted-server tool arguments.
3. Enable event types in `active` mode in autonomous agent pipelines in **healthcare,
   legal advice, financial advice, emergency services, or any domain where a wrong
   signal could cause physical, financial, or psychological harm** without domain
   validation and human oversight for every signal. See LEGAL.md §4.
4. Use or distribute Horizon in a way that misrepresents its validation status,
   capabilities, or limitations to third parties, customers, or regulators.
5. Reverse-engineer, decompile, or attempt to extract Horizon's model weights,
   embedding model, or proprietary algorithms beyond what MIT License permits.
6. Use the Service to develop a directly competing conversation dynamics monitoring
   product while misrepresenting that product as unrelated to Horizon.
7. Use the hosted server in volumes that constitute a denial-of-service attack or
   that exceed reasonable use for a single developer or organization without a
   commercial agreement. This is enforced technically, not just contractually —
   see §2's rate limit and session cap.
8. Circumvent any authentication, rate limiting, or access control mechanism —
   including attempting to read or modify another key's session data (see §2).
9. Transmit, generate, or attempt to generate through the Service any content depicting
   child sexual abuse material (CSAM), or content that sexually exploits or endangers a
   minor. See §13.

Violation of this §3 is grounds for immediate termination of your API key and may
expose you to civil liability.

---

## 4. Event Activation — Deployer Responsibility

All 16 Horizon event types ship in **observe mode** by default. Enabling any event in
`active` mode — causing agent controllers to autonomously change behavior based on that
signal — is a deployment decision entirely within your control and entirely at your risk.

**Before activating any event in a production deployment, you must:**

1. Validate that event's precision and recall on a labelled sample from your specific
   domain (general-purpose corpus validation in LEGAL.md §5 is not sufficient for all
   domains)
2. Implement human oversight appropriate to the stakes of your use case
3. Test that agent controller behaviors triggered by the event do not cause harm in
   edge cases

Horizon provides no warranty that any event signal will be accurate in your domain.
The validation numbers reported in the README and LEGAL.md §5 were obtained on a
general-purpose English corpus and do not apply to specialized or high-stakes domains
without independent validation.

---

## 5. Grounding Hook — Privacy Obligation

If you register a grounding hook via `register_grounding_hook()`, you acknowledge that:

1. The hook receives raw `human_message` and `agent_draft` text — the full content of
   the conversation turn
2. Any external call made by that hook transmits that text outside the Horizon pipeline,
   ending the privacy-by-default guarantee
3. You are solely responsible for ensuring that hook transmissions are covered by
   appropriate consent, legal basis, data transfer safeguards (including GDPR Chapter V
   SCCs for EU-to-US transfers), and disclosures to end users
4. Horizon makes no representation about the privacy practices of any third-party
   service your hook calls (OpenAI, Anthropic, Perplexity, etc.)

---

## 6. Privacy and Data Processing

Use of the hosted server is subject to the [Privacy Policy](PRIVACY_POLICY.md).

EU enterprise users who need to transmit personal data through the hosted server must
execute a Data Processing Agreement (GDPR Art. 28) before doing so. Contact
[leo@leocelis.com](mailto:leo@leocelis.com) with subject "DPA Request."

Self-hosted deployments: you are the sole data controller for any data processed by
your Horizon instance. The Privacy Policy does not cover self-hosted deployments.

---

## 7. Intellectual Property

The Service and all its components are protected by copyright and may be protected by
other intellectual property laws. Your use of the Service does not grant you any
ownership interest in the Service beyond the rights expressly granted by the MIT License.

You must not remove, obscure, or alter any copyright, trademark, or legal notices
contained in or displayed by the Service.

---

## 8. Service Availability and Changes

The hosted server is provided on a **best-effort basis**. Horizon may:

- Modify, suspend, or discontinue the hosted server at any time, with or without notice
- Change the features, API behavior, or pricing of the hosted server
- Revoke API keys that violate these Terms without prior notice
- Restart or redeploy the server (which invalidates active MCP sessions — clients must
  handle `SessionNotFoundError` by creating a new session)

Horizon will make reasonable efforts to provide advance notice of material changes to
the hosted server that affect existing users, but this is not guaranteed.

---

## 9. Disclaimer of Warranties

THE SERVICE IS PROVIDED "AS IS" WITHOUT ANY WARRANTY OF ANY KIND, EXPRESS OR IMPLIED.
HORIZON EXPRESSLY DISCLAIMS ALL WARRANTIES INCLUDING, WITHOUT LIMITATION:

- ACCURACY OR RELIABILITY OF FIDELITY SCORES, EVENT SIGNALS, OR TRAJECTORY ESTIMATES
- FITNESS FOR A PARTICULAR PURPOSE, INCLUDING FITNESS FOR USE IN HIGH-STAKES DOMAINS
- NON-INFRINGEMENT OF THIRD-PARTY INTELLECTUAL PROPERTY
- UNINTERRUPTED OR ERROR-FREE OPERATION OF THE HOSTED SERVER
- SECURITY OF DATA TRANSMITTED TO OR STORED BY THE SERVICE

Horizon's validation results (reported in LEGAL.md §5) are evidence that the metrics
work in the tested conditions — they are not a warranty that they will work in your
conditions. See LEGAL.md §3 for known limitations.

---

## 10. Limitation of Liability

TO THE MAXIMUM EXTENT PERMITTED BY APPLICABLE LAW, HORIZON'S TOTAL LIABILITY TO YOU
FOR ALL CLAIMS ARISING OUT OF OR RELATED TO THESE TERMS OR YOUR USE OF THE SERVICE —
WHETHER IN CONTRACT, TORT, OR OTHERWISE — SHALL NOT EXCEED THE GREATER OF: (a) THE
TOTAL FEES ACTUALLY PAID BY YOU TO HORIZON IN THE TWELVE MONTHS PRECEDING THE CLAIM,
OR (b) USD $50. FOR FREE-TIER USERS, THIS CAP IS USD $0.

IN NO EVENT SHALL HORIZON BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL,
CONSEQUENTIAL, OR PUNITIVE DAMAGES, INCLUDING LOSS OF PROFITS, LOSS OF DATA, BUSINESS
INTERRUPTION, HARM TO THIRD PARTIES, OR REGULATORY FINES.

This liability cap applies to contract-based claims. It does not automatically bar tort
claims (negligence, products liability) in all jurisdictions. See LEGAL.md §15.5.

---

## 11. Indemnification

You agree to defend, indemnify, and hold harmless Leo Celis and the Horizon project
from and against any claims, liabilities, damages, costs, and expenses (including legal
fees) arising from: (a) your use of the Service; (b) your violation of these Terms;
(c) any AI system you build using Horizon; (d) any data you transmit through the Service;
(e) your violation of any applicable law; or (f) your misrepresentation of Horizon's
capabilities to any third party.

---

## 12. Governing Law

These Terms are governed by the laws of the **State of Florida, United States**, without
regard to its conflict-of-law provisions.

**EU users:** Nothing in these Terms limits mandatory rights available under EU consumer
protection law, GDPR, or the EU AI Act. EU-resident consumers retain those rights
regardless of the Florida choice-of-law clause.

---

## 13. Illegal Content and Mandatory Reporting

**Prohibition:** You must not use the Service to transmit, generate, request, or attempt
to generate content depicting child sexual abuse material (CSAM), or content that
sexually exploits or endangers a minor, or to facilitate online enticement of a child or
child sex trafficking. This is a zero-tolerance prohibition — see §3(9).

**Mandatory reporting (18 U.S.C. § 2258A, as amended by the REPORT Act of 2024):**
Horizon, as a U.S.-based online service provider, complies with federal law requiring
providers to report apparent violations of this kind to the National Center for Missing
& Exploited Children (NCMEC) CyberTipline upon obtaining actual knowledge of them.
Horizon will report and cooperate with law enforcement to the extent required by
applicable law, and will preserve any information reasonably available at the time a
report is made for the statutory retention period.

**Interaction with Horizon's zero-retention design:** Horizon's core pipeline does not
retain raw message text beyond the active request (see Privacy Policy §1.1) — this is a
deliberate privacy-by-design choice, disclosed here for a specific, honest reason: it
also means Horizon has essentially no practical visibility into transmitted content in
the normal course of operation, and if Horizon does become aware of a violation (e.g.
through a third-party report), only the information available at that moment can be
included in a NCMEC report or preserved — Horizon cannot retroactively produce raw
message content it never stored. Suspected violations, including reports from third
parties, should be sent immediately to
[leo@leocelis.com](mailto:leo@leocelis.com) with subject "URGENT — CSAM report" or
reported directly to NCMEC at <https://report.cybertip.org>.

---

## 14. Dispute Resolution — Binding Arbitration

**Agreement to arbitrate:** Except for the exclusions below, you and Horizon agree that
any dispute, claim, or controversy arising out of or relating to these Terms or the
Service will be resolved by **binding individual arbitration** under the Federal
Arbitration Act, administered by the American Arbitration Association (AAA) under its
Consumer Arbitration Rules, rather than in court, except that either party may bring an
individual action in small claims court.

**Class action waiver:** Disputes must be brought in the parties' individual capacity,
not as a plaintiff or class member in any purported class, collective, or representative
proceeding. The arbitrator may not consolidate more than one person's claims.

**Exclusions:** Either party may seek injunctive or other equitable relief in a court of
competent jurisdiction in **Broward County, Florida** to prevent actual or threatened
infringement, misappropriation, or violation of a party's copyrights, trademarks, trade
secrets, or other intellectual property or confidentiality rights (§13's illegal-content
prohibition is enforceable in any forum by either party or law enforcement, notwithstanding
this arbitration agreement).

**30-day opt-out:** You may opt out of this arbitration agreement by emailing
[leo@leocelis.com](mailto:leo@leocelis.com) with subject "Arbitration Opt-Out" within 30
days of first accepting these Terms, including your name and the API key or account
identifier covered. If you opt out, disputes will instead be resolved exclusively in the
state or federal courts located in Broward County, Florida, and you consent to the
personal jurisdiction and venue of those courts.

**EU users:** Nothing in this section limits mandatory consumer rights available under EU
law. This arbitration agreement applies to the fullest extent permitted by the law
applicable to you; EU-resident consumers retain their statutory right to bring claims
before their local courts regardless of this section.

---

## 15. General Provisions

**Force majeure:** Neither party is liable for any failure or delay in performance
(including hosted server availability) resulting from causes beyond its reasonable
control, including acts of God, natural disaster, war, terrorism, civil unrest,
government action, labor disputes, internet or telecommunications failures, or failures
of third-party infrastructure providers (see §8 of LEGAL.md).

**Severability:** If any provision of these Terms (or of LEGAL.md, the Privacy Policy, or
the DPA) is found unenforceable or invalid, that provision will be limited or eliminated
to the minimum extent necessary so that the remaining provisions remain in full force and
effect. Specifically, the liability cap (§10) and indemnification (§11) are intended to
be severable from each other and from every other provision.

**Entire agreement:** These Terms, together with the Privacy Policy, LEGAL.md, and (where
executed) the Data Processing Agreement, constitute the entire agreement between you and
Horizon regarding the Service, and supersede any prior agreements or understandings,
written or oral, regarding the same subject matter.

**Assignment:** You may not assign or transfer these Terms, by operation of law or
otherwise, without Horizon's prior written consent. Horizon may assign these Terms
without restriction, including in connection with a merger, acquisition, or sale of
assets.

**No waiver:** Horizon's failure to enforce any right or provision of these Terms is not
a waiver of that right or provision. A waiver of any provision on one occasion does not
constitute a waiver on any other occasion.

**Notices:** Horizon may provide notices to you via the email associated with your API
key request or by posting to the repository. You may provide notices to Horizon at
[leo@leocelis.com](mailto:leo@leocelis.com).

**Relationship of the parties:** Nothing in these Terms creates a partnership, joint
venture, agency, or employment relationship between you and Horizon. See LEGAL.md §12
("No Professional Relationship") for the corresponding disclaimer on professional
services relationships.

---

## 16. Changes to These Terms

Horizon may update these Terms at any time. Material changes will be communicated by
updating the version number and effective date at the top of this document and noting
the change in `CHANGELOG.md`. Continued use of the Service after the effective date
constitutes acceptance of the revised Terms.

---

## 17. Contact

Leo Celis
[leo@leocelis.com](mailto:leo@leocelis.com)
https://github.com/leocelis/horizon

---

*These Terms are not legal advice. If you are deploying Horizon in a regulated context,
consult qualified legal counsel.*
