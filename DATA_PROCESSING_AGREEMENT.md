# Data Processing Agreement

> **Version:** 1.0 · **Template effective:** May 11, 2026
>
> This Data Processing Agreement ("DPA") is entered into between Leo Celis ("Horizon",
> "Processor") and the organization identified in the signature block below ("Customer",
> "Controller"). It supplements the Horizon Terms of Service and governs Horizon's
> processing of personal data on the Controller's behalf through the hosted MCP server
> at `horizon.leocelis.com`, as required by GDPR Article 28.
>
> **How to execute:** Email [leo@leocelis.com](mailto:leo@leocelis.com) with subject
> "DPA Request" and your organization details. Horizon will return a countersigned copy.
> Until a signed DPA is in place, **do not transmit personal data through the hosted
> server.**

---

## Parties

**Controller (Customer):**
- Organization name: _______________________________________________
- Address: _______________________________________________
- Contact name: _______________________________________________
- Email: _______________________________________________

**Processor (Horizon):**
- Leo Celis, operating horizon.leocelis.com
- Email: [leo@leocelis.com](mailto:leo@leocelis.com)

---

## 1. Subject Matter and Duration

**1.1 Subject matter:** Horizon processes personal data on behalf of the Controller
solely to provide the hosted MCP server service at `horizon.leocelis.com` — executing
conversation dynamics metrics on `human_message` and `agent_response` text transmitted
through `process_turn()` tool calls — as described in the Terms of Service and this DPA.

**1.2 Duration:** This DPA is effective from the date of last signature below and
continues for as long as Horizon processes personal data on behalf of the Controller,
or until the underlying Terms of Service are terminated, whichever comes first.

---

## 2. Nature and Purpose of Processing

**2.1 Nature:** Computing semantic metrics (embeddings, information gain, divergence
score, token waste ratio, consistency, fidelity score) and event evaluations on
conversation turns. Holding session state (embeddings, metric history, event log) in
memory during the active session.

**2.2 Purpose:** Providing real-time conversation quality monitoring signals to the
Controller's AI agent deployment.

**2.3 No retention of message text:** Raw message text (`human_message`,
`agent_response`) is **not** retained beyond the active request. Embeddings are held
in process memory for session duration but are not human-readable and cannot be
reconstructed into the original text.

**2.4 SQLite persistence:** The default hosted server does not use `PersistentDynamicsStore`.
If the Controller requests a custom deployment with persistence enabled, the DPA will
be amended to describe the additional data retained.

---

## 3. Types of Personal Data

The Controller may transmit the following categories of personal data through
`process_turn()` arguments:

- Conversation content (human messages and AI agent responses that may contain or
  reference personal data of the Controller's end users)
- `user_id` values passed in session configuration (if these values are linked to
  identifiable natural persons)

The Controller agrees **not** to transmit special categories of personal data (GDPR
Art. 9) through the hosted server without a separate amendment to this DPA and
appropriate safeguards.

---

## 4. Categories of Data Subjects

End users of the Controller's AI agent system whose conversation turns are processed
through Horizon.

---

## 5. Processor Obligations (Horizon)

Horizon agrees to:

**5.1 Instructions only.** Process personal data only on documented instructions from
the Controller, including with regard to transfers of personal data to a third country
— unless required to do so by Union or Member State law; in such case, Horizon will
inform the Controller of that legal requirement before processing, unless that law
prohibits such information on important grounds of public interest.

**5.2 Confidentiality.** Ensure that persons authorized to process the personal data
have committed themselves to confidentiality or are under an appropriate statutory
obligation of confidentiality.

**5.3 Security.** Implement appropriate technical and organizational measures (GDPR
Art. 32) to ensure a level of security appropriate to the risk, including:
- Encryption of personal data in transit (HTTPS/TLS)
- Session isolation by API key
- Minimization of data retained (no raw message text written to disk in default configuration)
- Regular assessment of security measures

**5.4 Sub-processors.** Not engage another processor (sub-processor) without prior
specific or general written authorization of the Controller. Current authorized
sub-processors are listed in §6 of this DPA. Horizon will notify the Controller of any
intended changes to sub-processors, giving the Controller the opportunity to object.

**5.5 Data subject rights assistance.** Assist the Controller in responding to requests
from data subjects exercising their GDPR rights (access, rectification, erasure,
restriction, portability, objection). Given that Horizon does not retain raw message
text, assistance will primarily consist of: confirming what session metadata, if any,
is held for a given `user_id`; and deleting or anonymizing that metadata upon Controller
instruction.

**5.6 Deletion/return.** At the choice of the Controller, delete or return all personal
data to the Controller after the end of the provision of services, and delete existing
copies — unless required to retain data by applicable law.

**5.7 Audit assistance.** Make available to the Controller all information necessary to
demonstrate compliance with GDPR Article 28, and allow for and contribute to audits,
including inspections, conducted by the Controller or an auditor mandated by the
Controller. Horizon may charge reasonable fees for audit assistance requests.

**5.8 Breach notification.** Notify the Controller without undue delay (and, where
feasible, within 24 hours) after becoming aware of a personal data breach involving the
Controller's data. Notification will include the information specified in GDPR Art. 33(3)
to the extent available at the time.

---

## 6. Authorized Sub-processors

| Sub-processor | Country | Role | Privacy/DPA link |
|---------------|---------|------|-----------------|
| DigitalOcean, Inc. | United States | Infrastructure hosting | <https://www.digitalocean.com/legal/data-processing-agreement> |
| Upstash, Inc. | United States | Redis session storage | <https://upstash.com/trust/data-processing-addendum.pdf> |

**International transfer notice:** Both sub-processors are US-based. The absence of an
EU adequacy decision for the United States means that personal data transfers to these
sub-processors require appropriate safeguards under GDPR Chapter V. Horizon relies on
Standard Contractual Clauses (Commission Implementing Decision (EU) 2021/914) with
these sub-processors. A copy of applicable SCCs may be provided to the Controller upon
written request.

Until Horizon and the Controller have executed Standard Contractual Clauses for the
Controller-to-Horizon transfer (currently unavailable), the Controller should not
transmit personal data of EU residents through the hosted server.

---

## 7. Controller Obligations

The Controller agrees to:

7.1 Process personal data only in accordance with applicable law, including ensuring
a valid legal basis under GDPR Art. 6 (and Art. 9 for special category data) exists
for all processing instructed to Horizon.

7.2 Ensure that the personal data it transmits to Horizon has been collected lawfully
and that data subjects have received appropriate privacy notices (GDPR Art. 13/14)
disclosing that Horizon will process their data.

7.3 Not transmit special categories of personal data (GDPR Art. 9) to the hosted
server without a separate written amendment and appropriate safeguards.

7.4 Ensure that any grounding hook registered for the Controller's deployment complies
with applicable data protection law, including providing appropriate disclosures to
end users and ensuring lawful basis for any external transmissions.

---

## 8. Governing Law

This DPA is governed by the laws of the **Republic of Ireland** (as the EU reference
jurisdiction) for the purposes of GDPR compliance, and by the laws of the **State of
Florida, United States** for all other purposes.

---

## Signatures

**Controller (Customer):**

Signature: _______________________________________________
Printed name: _______________________________________________
Title: _______________________________________________
Date: _______________________________________________

**Processor (Horizon / Leo Celis):**

Signature: _______________________________________________
Printed name: Leo Celis
Title: Owner
Date: _______________________________________________

---

*This is a template. The executed version governs. Consult qualified legal counsel before
executing this agreement.*
