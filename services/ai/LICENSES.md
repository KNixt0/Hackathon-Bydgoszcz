# services/ai: third-party licences

Runtime dependencies (`requirements.txt`, fully pinned; direct ones are listed in `requirements.in`).

| Package | Version | Licence | Why it is here |
|---|---|---|---|
| fastapi | 0.165.0 | MIT | HTTP API |
| starlette | 1.10.0 | BSD-3-Clause | ASGI toolkit under FastAPI |
| uvicorn | 0.54.0 | BSD-3-Clause | ASGI server |
| pydantic | 2.14.4 | MIT | contract schemas |
| pydantic-core | 2.50.5 | MIT | pydantic |
| httpx | 0.28.1 | BSD-3-Clause | optional local Ollama client |
| httpcore | 1.0.9 | BSD-3-Clause | httpx |
| h11 | 0.16.0 | MIT | uvicorn, httpcore |
| anyio | 4.16.0 | MIT | starlette, httpx |
| idna | 3.20 | BSD-3-Clause | httpx, anyio |
| click | 8.5.1 | BSD-3-Clause | uvicorn |
| annotated-doc | 0.0.7 | MIT | fastapi |
| annotated-types | 0.8.0 | MIT | pydantic |
| typing-inspection | 0.4.5 | MIT | pydantic |
| opentelemetry-api | 1.45.2 | Apache-2.0 | fastapi |
| typing-extensions | 4.16.0 | PSF-2.0 | fastapi, pydantic (not removable) |
| certifi | 2026.11.20 | MPL-2.0 | httpx (CA bundle, used unmodified) |

Two transitive packages are outside the MIT / Apache-2.0 / BSD / ISC list of `coord/GUIDELINES.md`:
`typing-extensions` (PSF-2.0, permissive) and `certifi` (MPL-2.0, file-level copyleft; shipped unmodified).
Neither is GPL, AGPL or LGPL. Both come with FastAPI / httpx and need a decision by the team lead.

Development only (`requirements-dev.txt`, not in the image):

| Package | Version | Licence |
|---|---|---|
| pytest | 9.0.1 | MIT |
| ruff | 0.14.5 | MIT |
| iniconfig | 2.3.1 | MIT |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause |
| pluggy | 1.7.0 | MIT |
| pygments | 2.21.0 | BSD-2-Clause |

No model weights, fonts or icons are bundled. The default embedder is implemented in this repository
(`app/preprocess/embed.py`). An Ollama model, if configured, is pulled by the operator and is not part of the image.

## Data

| File | Source | Status |
|---|---|---|
| `data/registries/knf_banks_brokerage.json`, `knf_brokerage_houses.json`, `knf_foreign_branches.json`, `knf_foreign_cross_border.json`, `knf_tfi.json`, `knf_public_warnings.json` | public registers and the public warnings list of the Polish Financial Supervision Authority (knf.gov.pl), fetched with `scripts/fetch_knf_registers.py` | real data, snapshot date inside each file; the warnings list names entities exactly as KNF publishes them and must be refreshed (entries removed by KNF disappear on refresh) |
| `data/registries/knf_investment_advisors.json`, `kirp_legal_advisers.json`, `kidp_tax_advisers.json` | written for the demo | synthetic samples (`"synthetic_sample": true`), invented entries only |
| `data/registries/_demo_overlay.json` | written for the demo | fictional "registered" entities for the demo cases, flagged `synthetic`; disable with `AI_DEMO_OVERLAY=false` |
