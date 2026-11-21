# Contracts

Interfaces between parts of the system: API shapes, data formats, events, component props. Workers build against these, so they rarely need to talk to each other.

- One file per boundary, for example `api.md`, `data-model.md`, `events.md`.
- Each file has a version line at the top: `version: 1`.
- Contracts change only through a PR a human has approved. Log the change in `../decisions.md` and bump the version.

Example (`api.md`):

```markdown
version: 1

## POST /api/score
request:  { "userId": string, "points": number }
response: { "total": number }
errors:   400 invalid body · 404 unknown user
```
