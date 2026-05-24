# Security policy

## Reporting a vulnerability

Open a **private security advisory** at https://github.com/ikatyal2110/openclaw-to-hermes/security/advisories/new. Do not file a public issue for security-sensitive reports.

We'll acknowledge within 5 business days and aim to ship a fix within 30 days for high-severity issues. The reporter is credited in the advisory unless they request anonymity.

## Scope

Praxis is a build-time CLI: it reads an OpenClaw project and writes a Hermes project. It does **not** run as a daemon and does **not** execute the workflows it analyzes. Reasonable threats in scope:

- Malicious input projects causing crashes, infinite loops, or path traversal during analysis.
- Generated Hermes output that exposes secrets that should have been redacted (Praxis must never inline `${env.X}` values; it only references their names).
- Tampering with the LLM cache (post-v0.10) to influence generated prose.
- Secret-pattern false negatives in the env classifier (a credential-like name slipping through unflagged).

Out of scope:

- Vulnerabilities in OpenClaw or Hermes themselves.
- Misuse of the migrated Hermes project at runtime.

## Disclosure

Once a fix is in `main`, a `SECURITY-ADVISORY-<id>.md` is published under `docs/advisories/` describing the issue, the affected versions, and the workaround.
