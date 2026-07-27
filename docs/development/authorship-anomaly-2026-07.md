# Commit authorship anomaly from 2026-07-01 to 2026-07-05

This developer record explains a historical commit identity issue. It is not
part of the public security reporting policy.

Commits are signed with the maintainer's SSH key under the identity
`Brad Edwards <j.bradley.edwards@gmail.com>`.

Thirty-six commits in this window were authored as the placeholder identity
`Test <t@example.com>` and appear as unverified on GitHub. They are not
unsigned or forged. Local signature checks report a good signature for the
maintainer's email.

## Cause

A repository-local user override set `user.email=t@example.com` and
`user.name=Test` during a pre-push recovery on 2026-07-01. A history replay
re-created commits under that identity. The override then shadowed the global
identity until it was found.

## Scope

The issue was limited to author and committer identity fields. No push
redirection, hooks path, SSH command, or credential helper changed.

The affected range starts at `cf4cdaa` and ends at `a1fb96e`. Use
`git log --all --author='t@example.com' --format='%H %cI'` to list it.
GitHub-created merge commits in that window are separate.

## Resolution

The local override was removed on 2026-07-05. Shared history was not rewritten,
so the placeholder author remains in the historical record.
