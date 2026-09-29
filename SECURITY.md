# Security policy

The 0.1.x line is a local demonstration and research workbench. It is not a multi-tenant hosted service.

Do not post sensitive vulnerability details, customer data, or credentials in public issues. Once this repository is published, use GitHub's private vulnerability reporting if enabled; otherwise contact a maintainer through their published private contact channel before sharing details.

Report the affected version, minimal reproduction using synthetic data, expected behavior, observed impact, and proposed mitigation. Do not test against systems you do not own.

See `docs/security.md` for the threat model, authorization boundaries, local-only defaults, and deployment limitations. Dependency updates are checked through pip-audit and pnpm audit. There is no guaranteed response SLA for this volunteer project.
