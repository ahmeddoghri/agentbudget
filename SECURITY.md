# Security Policy

## Supported versions

This project is pre-1.0. Security fixes land on `main`; track the latest commit.

## Reporting a vulnerability

Please do not open a public issue for security problems. Use GitHub's
[private vulnerability reporting](https://github.com/ahmeddoghri/agentbudget/security/advisories/new)
or email the maintainer. Include a description of the issue and its impact,
steps to reproduce (a minimal proof-of-concept helps), and any suggested fix.

You can expect an acknowledgement within a few days. Once a fix is out you will
be credited unless you would rather stay anonymous.

## Scope notes

agentbudget is a pure-stdlib library with no runtime dependencies and makes no
network calls. It does not call your model or your tools; it only tracks what
you report to it through `record()`. That means it is only as good as your
integration: if a step is not recorded, the guardrail cannot see it. Wire
`record()` and `check()` into every tool call in your loop, not just some of
them, or the limits it enforces will be inaccurate.
