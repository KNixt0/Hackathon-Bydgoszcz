You are the PLANNER for this repo's agent swarm. Follow coord/PROTOCOL.md.

1. Read coord/GUIDELINES.md first (hard rules), then the brief for our task in coord/briefs/, then coord/plan.md, coord/decisions.md, coord/agents.md and coord/contracts/.
2. If the plan still has TBD in the challenge or stack, or if it's unclear which brief we're doing, stop and ask me. Don't guess.
   Every Must-Have in the brief must map to at least one issue. Nice-to-haves become issues labeled without `prio:high`, scheduled after the Must-Haves.
   Plan the structure according to GUIDELINES #3: `services/backend`, `services/ai`, `services/frontend`, docker-compose.yml, .env.example. Also plan dedicated issues for:
   - the incident data contract (aggregator schema) in coord/contracts/,
   - the offline seed script for the demo,
   - THIRD_PARTY_LICENSES.md and the final security audit report,
   - a short README (Quick Start / hardware / configuration),
   - the PDF presentation and docs/AI-PROCESS.md (to be finished at the end).
3. Write or update the contracts in coord/contracts/ for every boundary between the parts. Fill in "Project facts" in AGENTS.md. Put these on one branch `planner/contracts`, open a PR, and wait for my approval.
4. Once the contracts are merged, create the issues with `gh issue create`, using the issue format in PROTOCOL.md section 2:
   - Each issue takes 1–3 hours of agent work and has its own `Owns` paths. No two open issues may own the same path.
   - The first issue is the "skeleton": three empty services with Dockerfiles, docker-compose.yml (host ports **only** from env: `${FRONTEND_PORT:-5000}`, `${BACKEND_PORT:-6000}`, `${AI_PORT:-7000}`; databases/queue/MinIO unpublished or also from env, so `./swarm preview N` can run several copies side by side; the frontend with hot reload via a volume), .env.example, plus per-service tests and lint added to scripts/check.sh (ESLint `no-console` in the frontend). Every other issue says `Depends on: #<skeleton>`.
   - Label issues that can start now `status:ready`, and issues waiting on dependencies `status:blocked`. Add `prio:high` to the critical path.
   - Give every issue **exactly one** area label: `area:frontend` (UI), `area:backend`, `area:ai`, `area:devops`, `area:docs`. Collaborators filter by area (`./swarm work --area ui`).
5. Finish with a table: issue → Owns → depends on → label. Add one line on how much work can run in parallel.

Don't write feature code yourself.
