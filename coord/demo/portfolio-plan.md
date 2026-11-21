# Demo plan: short portfolio site

A warm-up run of the swarm before the real hackathon task. Goal: test the whole flow (plan → claim → build → PR → review → owner approval → merge) on something small. All of it lives in `demo/portfolio/`, and the issues carry the `demo` label, so it can be deleted afterwards.

## What we build
A single-page portfolio for a fictional developer, "Ola Nowak, frontend developer, Bydgoszcz": hero, about + skills, project grid (data from JSON), contact form with validation, nav + footer.

## Stack
Static HTML/CSS/JS with **no dependencies and no build step**. Each section is a Web Component in its own file, so tasks never touch the same file. Run locally:
```bash
python3 -m http.server 8080 --directory demo/portfolio
```

## Tasks

| # | Task | Area | Difficulty | Owns | Depends on |
|---|---|---|---|---|---|
| 1 | Skeleton: index.html, tokens, README | frontend | standard, prio:high | `index.html`, `styles/**`, `README.md` | none |
| 2 | Nav + footer | frontend | size:xs | `components/site-nav.js`, `components/site-footer.js` | 1 |
| 3 | Hero | frontend | standard | `components/site-hero.js` | 1 |
| 4 | About + skills | frontend | size:xs | `components/site-about.js` | 1 |
| 5 | Project data (JSON) | docs | size:xs | `data/projects.json` | none (contract only) |
| 6 | Project grid with tag filter | frontend | standard | `components/project-grid.js` | 1, 5 |
| 7 | Contact form with validation | frontend | standard | `components/contact-form.js` | 1 |
| 8 | QA: accessibility, responsiveness, console | devops | model:opus | `demo/portfolio/QA.md` + fixes reported as comments | 2, 3, 4, 6, 7 |

All paths are relative to `demo/portfolio/`. The contract is in [coord/contracts/portfolio.md](../contracts/portfolio.md).

Parallelism: tasks 1 and 5 start immediately. After 1, five tasks (2, 3, 4, 6, 7) run in parallel. Task 8 runs last.
