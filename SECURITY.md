# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| Latest release on `main` | ✓ Security updates |
| Previous releases | No security backports |

---

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Disclosing a vulnerability publicly before a fix is available puts all Horizon users
at risk. Please follow responsible disclosure.

### Preferred: GitHub Security Advisories

Navigate to the [Security tab](https://github.com/leocelis/horizon/security) and click
**"Report a vulnerability."** This creates a private draft advisory visible only to
Leo Celis. GitHub's process keeps the vulnerability private until a fix is coordinated.

### Alternative: Email

Send details to **[leo@leocelis.com](mailto:leo@leocelis.com)** with subject line
**"[SECURITY] Horizon vulnerability report"**.

Encrypt sensitive reports using PGP if possible (key available on request).

---

## What to Include

A good vulnerability report contains:

1. **Description** — what is the vulnerability and what does it allow
2. **Steps to reproduce** — minimal reproducible case (PoC)
3. **Affected versions** — which version(s) you observed the issue in
4. **Impact** — confidentiality, integrity, availability, or data privacy impact
5. **Suggested fix** (optional but appreciated)

---

## Response Commitments

| Stage | Timeline |
|-------|----------|
| Acknowledgment of report | Within **3 business days** |
| Initial triage and severity assessment | Within **7 business days** |
| Fix or mitigation plan communicated to reporter | Within **14 business days** |
| Public disclosure coordination | After fix is available and deployed |

For critical vulnerabilities affecting the hosted server (data exposure, authentication
bypass, denial of service), faster timelines apply — acknowledgment within 1 business
day.

---

## Scope

This policy covers:

- **Horizon Python library** (`src/horizon/`) — all distributed versions
- **Hosted MCP server** (`horizon.leocelis.com`) — authentication, session isolation,
  rate limiting, data exposure
- **MCP server code** (`src/horizon/mcp/`) — tool call validation, injection risks
- **SQLite persistence layer** (`src/horizon/storage/sqlite.py`) — data exposure,
  injection risks
- **Grounding hook interface** (`src/horizon/grounding.py`) — data leakage, SSRF

Out of scope:

- Third-party dependencies (report to maintainers of `sentence-transformers`,
  `mcp`, `geoip2`, etc. directly; open a Dependabot alert for transitive dependency
  CVEs)
- DigitalOcean or Upstash infrastructure (report to those providers directly)
- Security issues in forks or derivative works not maintained by Leo Celis

---

## Known Security Considerations for Self-Hosted Deployments

**SQLite file permissions.** The `horizon.db` file (or custom path) is created with
default OS permissions. Restrict access to the database file to the process user only:
```bash
chmod 600 /path/to/horizon.db
```

**SQLite is not encrypted at rest.** If your deployment stores sensitive user_id values
or high-sensitivity conversation metadata in `PersistentDynamicsStore`, consider using
SQLCipher or encrypting the database at the filesystem layer. See LEGAL.md §7.

**API key protection.** Never commit API keys, tokens, or `.env` files to source
control. The `.gitignore` in this repository excludes `.env` and `horizon.db` — verify
this exclusion is carried into any fork or downstream project.

**Grounding hook.** Any callable registered via `register_grounding_hook()` receives
raw conversation text. Only register hooks that you trust completely. A malicious or
compromised hook can exfiltrate all conversation content passing through Horizon.
See LEGAL.md §3.4.

**Hosted server restart data loss.** The hosted MCP server is stateless between
restarts. All in-memory session state (embeddings, history, events) is lost on restart.
Client applications must handle `SessionNotFoundError` gracefully by creating a new
session rather than retrying with a stale session_id.

---

## Personal Data Breach — Hosted Server

If you suspect a personal data breach involving data transmitted to the Horizon hosted
server (e.g., suspected unauthorized access to sessions or API keys), contact
[leo@leocelis.com](mailto:leo@leocelis.com) immediately.

**For EU data controllers:** Do not wait for Horizon's response before beginning your
own assessment. GDPR Article 33 requires you to notify your supervisory authority
within **72 hours** of becoming aware of a breach. Start your notification process
immediately using the information available to you.

**For Florida-resident data subjects:** Florida FIPA (§ 501.171) requires notification
within 30 days of discovery; contact [leo@leocelis.com](mailto:leo@leocelis.com) for
assistance scoping a potential Florida notification obligation.

---

## Dependency Management

Dependencies with known CVEs are tracked via Dependabot. Security-relevant dependency
updates are prioritized and released promptly. To check for known vulnerabilities in
your installed version:

```bash
pip install pip-audit
pip-audit -r requirements.txt
```

---

## Attribution

Reporters who identify and responsibly disclose valid security vulnerabilities will be
acknowledged in the security advisory (unless anonymity is requested). We do not
currently have a bug bounty program.

---

*Thank you for helping keep Horizon and its users safe.*
