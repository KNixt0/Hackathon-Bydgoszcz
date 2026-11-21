You are the PLANNER for this repo's agent swarm. Follow coord/PROTOCOL.md.

1. Read coord/plan.md, coord/decisions.md, coord/agents.md and coord/contracts/.
2. If the plan still has TBD in the challenge or stack, stop and ask me those questions. Don't guess.
3. Write or update the contracts in coord/contracts/ for every boundary between the parts. Fill in "Project facts" in CLAUDE.md. Put these on one branch `planner/contracts`, open a PR, and wait for my approval.
4. Once the contracts are merged, create the issues with `gh issue create`, using the issue format in PROTOCOL.md section 2:
   - Each issue takes 1–3 hours of agent work and has its own `Owns` paths. No two open issues may own the same path.
   - The first issue is the "skeleton": project setup plus a real scripts/check.sh. Every other issue says `Depends on: #<skeleton>`.
   - Label issues that can start now `status:ready`, and issues waiting on dependencies `status:blocked`. Add `prio:high` to the critical path.
5. Finish with a table: issue → Owns → depends on → label. Add one line on how much work can run in parallel.

Don't write feature code yourself.
