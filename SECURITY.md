# Security policy

## Reporting a vulnerability

Open a private security advisory on the GitHub repo, or email the maintainers (address listed in the repo's `MAINTAINERS` file once one exists). Do not file a public issue for security-sensitive reports.

## Scope

Praxis is a build-time CLI: it reads an OpenClaw project and writes a Hermes project. It does **not** run as a daemon and does **not** execute the workflows it analyzes. Reasonable threats in scope:

- Malicious input projects causing crashes, infinite loops, or path traversal during analysis.
- Generated Hermes output that exposes secrets that should have been redacted (Praxis must never inline `${env.X}` values; it only references their names).
- Tampering with the LLM cache (post-v0.1) to influence generated prose.

Out of scope:

- Vulnerabilities in OpenClaw or Hermes themselves.
- Misuse of the migrated Hermes project at runtime.

## Disclosure

Once a fix is in `main`, a `SECURITY-ADVISORY-<id>.md` is published under `docs/advisories/` describing the issue, the affected versions, and the workaround.
