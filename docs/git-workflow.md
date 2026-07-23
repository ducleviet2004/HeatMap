# Git workflow

Create short-lived branches named `feat/issue-summary`, `fix/issue-summary`, or
`chore/issue-summary`. Rebase or merge current `main` before review according to team convention;
never force-push shared branches. Prefer small conventional commits such as `feat(api): add trip
ingestion acknowledgement`.

One issue should normally represent one vertical slice. Open a draft PR early, record dependencies,
and merge prerequisite schema/contracts before consumers. Require green CI, one peer approval, and
resolved conversations. Use feature flags or backward-compatible sequencing for incomplete
multi-PR work. Roll back code through a revert; database changes require an explicit forward-fix or
safe downgrade plan.

