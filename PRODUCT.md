# PRODUCT.md: InvestWatch dashboard

Product context for design and copy decisions. Facts come from `README.md`, `coord/plan.md` and `docs/design/proposals.html` (chosen direction: proposal 1 "Urzędowy"). Visual spec: `DESIGN.md`.

## What it is
InvestWatch is an on-premise system for UKNF (Komisja Nadzoru Finansowego's office, the Polish Financial Supervision Authority). It collects advertisements and offers from the web and social media and flags three kinds of problem: (1) investment-firm ads run by third parties and finfluencers (module 1), (2) insufficient risk information against the 18 UKNF criteria (module 2), (3) unlicensed investment advice, "shadow advisory" (module 3). Each case gets a risk score; Compliance Score is 100 minus risk. Levels follow thresholds: flagged from 20, critical from 70 (configurable). It runs offline after the images are built.

## Users
- **Analyst**: works the queue every day.
- **Supervisor**: everything the analyst does, plus approving escalations, saving global thresholds and reading the audit log (`/audyt`).

## Jobs to be done
1. **Triage**: scan the queue, filter by level, open the cases that matter first.
2. **Read a verdict with evidence**: what was found, which criteria, how sure, which registers say what, what the source looked like.
3. **Decide and record the next step**: accept or change the recommendation, set the case status, escalate, export the evidence package (PDF, CSV).
4. **Tune the threshold**: move one slider and read one sentence: how many cases the system flags, how many false alarms and missed violations that gives, with precision and recall as secondary figures. Details for analysts sit behind a closed disclosure. Two thresholds exist (flag, default 20; critical, default 70, both on risk 0–100); everyone can preview, only the supervisor saves them globally.

## Surface mode
A task tool used for long sessions on large monitors and tablets. Scanability, consistency and precision outrank expression. The interface should feel calm and trustworthy, not exciting. Numbers are instruments to read, not decoration. Density stays high where analysts compare rows (queue rows about 40 px, 14 px text). The look is ruled and square, in the manner of a public register: structure comes from 1 px rules, tabs with counts, key–value case data and tables, not from cards, radii or shadows.

## Tone of voice
- Plain official Polish. Sentence case everywhere (titles, buttons, table headers).
- Verdict first, in one sentence, then the number. Say what was found, then how much.
- Verb-first actions: "Przekaż do postępowania", "Eksportuj CSV", "Zmień zalecenie". No "OK", "Submit", "Proceed".
- No marketing language, no exclamation marks, no emoji, no humour.
- Errors never blame the user: say what happened and what can be done next ("Nie udało się wczytać kolejki. Spróbuj ponownie.").
- Dates as `21.11.2026`, registers always with a "stan na" date. Say "brak wpisu", not "nie znaleziono".

## Brand constraints
Inspired by the principles of government design systems, chiefly DSFR (France: square, ruled, table-first), plus gov.pl (Poland) for underlined links and plain wording. Principles only. No state logos, emblems or reserved typefaces (Marianne; the product uses Public Sans, OFL). The product must not be mistaken for an official state service: it is an analytical tool, labelled as such. All fonts self-hosted (no external requests at runtime).

## Accessibility floor
- WCAG 2.1 AA: text 4.5:1, graphical markers and control edges 3:1.
- Status is never carried by colour alone: every level has its own icon shape and a word.
- Visible focus on every interactive element; full keyboard access, including the threshold slider (arrows change it by 1).
- Targets: 40 px for buttons and fields, 44 px for tabs and the threshold slider controls (24 px is the AA minimum).
- Respect `prefers-reduced-motion`. Every control has a visible label (placeholders only for format hints).

## Anti-references
Generic SaaS dashboard: trios of KPI tiles, gauges and semicircle meters, bento grids, pastel pill overload, decorative gradients, glassmorphism, drop shadows as hierarchy, coloured card fills per status, round icon buttons, photos of people, illustrated empty states.
