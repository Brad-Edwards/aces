# Security Policy

## Reporting a Vulnerability

Do not report suspected vulnerabilities through public GitHub issues.

Use GitHub private vulnerability reporting for this repository if it is
available. If private reporting is not available, contact the maintainer
privately through the contact path listed on Brad Edwards' GitHub profile and
include `ACES SDL security report` in the subject or first line.

Include enough detail to reproduce and assess the issue:

- affected package, command, schema, or document
- affected version, commit, or branch
- reproduction steps
- expected and actual behavior
- impact
- proof of concept or logs, if available

## Scope

Security reports are most useful for issues in:

- parser and validator behavior
- SDL module resolution and publication
- contract generation and conformance tooling
- CLI behavior
- MCP server behavior
- runtime control-plane code
- repository automation that handles untrusted input

This repository also contains research material and reference ecosystem
material. Reports against archived third-party material may be documented here,
but fixes usually need to happen upstream.

## Response Expectations

ACES SDL is maintained by a sole maintainer. There is no formal security
response SLA. Reports will be reviewed on a best-effort basis, with priority
given to reproducible issues that affect current code, published contracts, or
documented workflows.

Please avoid publishing exploit details until there has been reasonable time to
triage and prepare a fix or mitigation.

## Commit Authorship and Signing

Commits are signed with the maintainer's SSH key (ED25519,
`SHA256:fdBpsrHmMxkK9DikzdhtWINNcTLkhmdsYrHK5cIMa/o`) under the identity
`Brad Edwards <j.bradley.edwards@gmail.com>`.

### Authorship anomaly, 2026-07-01 to 2026-07-05

36 commits in this window were authored as the placeholder identity
`Test <t@example.com>` and appear as **Unverified** on GitHub. They are not
unsigned or forged: each is signed by the maintainer's SSH key above and
verifies locally — `git log --show-signature` reports a good signature for
`j.bradley.edwards@gmail.com`. GitHub withholds the Verified badge only
because `t@example.com` is not a verified email on the account.

**Cause.** A repository-local `[user]` override
(`user.email=t@example.com`, `user.name=Test`) was written into the shared
`.git/config` during a pre-push recovery on 2026-07-01 ~20:15 (recovery
branch `local/prepush-base-damage-20260701-201555`). A history replay in
that recovery re-created ~13 commits in one second at 20:15:53 under the
placeholder identity; the override then shadowed the correct global identity
for subsequent local commits until it was found.

**Scope.** Limited to the author/committer identity fields. No other local
configuration was altered — no `url.*.insteadOf` push redirection, no local
`core.hooksPath`, no `core.sshCommand`, no `credential.helper`.

**Affected commits.** Author `Test <t@example.com>`, from `cf4cdaa`
(2026-07-01 20:15:53) through `a1fb96e` (2026-07-05 06:33:42). Enumerate
with `git log --all --author='t@example.com' --format='%H %cI'`. Merge
commits created by GitHub in this window are separately signed by GitHub's
web-flow key and are Verified; they are not part of this set.

**Remediation.** The local override was removed on 2026-07-05
(`git config --local --remove-section user`); identity now resolves to the
correct global values. History was not rewritten: the affected commits are
merged into shared branches, so the placeholder author remains as the
historical record and this note is the durable explanation.
