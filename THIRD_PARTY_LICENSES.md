# Third-party licences

Licence inventory for InvestWatch, generated from `services/backend/LICENSES.md`, `services/ai/LICENSES.md` and `services/frontend/LICENSES.md`, plus container images from `docker-compose.yml` and the Dockerfiles. Versions are those pinned in the source files; `-` means not given.

## Backend (services/backend)

| Package | Version | Licence | Scope |
|---|---|---|---|
| amqp | 5.4.2 | BSD-3-Clause | runtime |
| annotated-doc | 0.0.7 | MIT | runtime |
| annotated-types | 0.8.0 | MIT | runtime |
| anyio | 4.16.0 | MIT | runtime |
| asn1crypto | 1.5.1 | MIT | runtime |
| beautifulsoup4 | 4.15.0 | MIT | runtime |
| bidict | 0.24.1 | MPL-2.0 | runtime |
| billiard | 4.3.2 | BSD-3-Clause | runtime |
| boto3 | 1.44.9 | Apache-2.0 | runtime |
| botocore | 1.44.9 | Apache-2.0 | runtime |
| celery | 5.7.0 | BSD-3-Clause | runtime |
| certifi | 2026.11.20 | MPL-2.0 | runtime |
| click | 8.5.1 | BSD-3-Clause | runtime |
| click-didyoumean | 0.3.1 | MIT | runtime |
| click-plugins | 1.1.1.2 | BSD-3-Clause | runtime |
| click-repl | 0.4.1 | MIT | runtime |
| fastapi | 0.165.0 | MIT | runtime |
| greenlet | 3.5.6 | MIT AND PSF-2.0 | runtime |
| h11 | 0.16.0 | MIT | runtime |
| httpcore | 1.0.9 | BSD-3-Clause | runtime |
| httptools | 0.9.0 | MIT | runtime |
| httpx | 0.28.1 | BSD-3-Clause | runtime |
| idna | 3.20 | BSD-3-Clause | runtime |
| jinja2 | 3.1.6 | BSD-3-Clause | runtime |
| jmespath | 1.1.0 | MIT | runtime |
| kombu | 5.7.0 | BSD-3-Clause | runtime |
| markupsafe | 3.0.4 | BSD-3-Clause | runtime |
| opentelemetry-api | 1.45.2 | Apache-2.0 | runtime |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause | runtime |
| pg8000 | 1.31.6 | BSD-3-Clause | runtime |
| playwright | 1.65.2 | Apache-2.0 | runtime |
| prompt-toolkit | 3.0.53 | BSD-3-Clause | runtime |
| pydantic | 2.14.4 | MIT | runtime |
| pydantic-core | 2.50.5 | MIT | runtime |
| pydantic-settings | 2.16.3 | MIT | runtime |
| python-dateutil | 2.9.0.post0 | Apache-2.0 OR BSD-3-Clause | runtime |
| python-dotenv | 1.2.4 | BSD-3-Clause | runtime |
| python-engineio | 4.15.1 | MIT | runtime |
| python-socketio | 5.18.1 | MIT | runtime |
| pyyaml | 6.0.4 | MIT | runtime |
| redis | 8.1.0 | MIT | runtime |
| s3transfer | 0.19.3 | Apache-2.0 | runtime |
| scramp | 1.5.0 | MIT-0 | runtime |
| simple-websocket | 1.1.0 | MIT | runtime |
| six | 1.17.0 | MIT | runtime |
| soupsieve | 4.1.3 | MIT | runtime |
| sqlalchemy | 2.1.9 | MIT | runtime |
| starlette | 1.10.0 | BSD-3-Clause | runtime |
| typing-extensions | 4.16.0 | PSF-2.0 | runtime |
| typing-inspection | 0.4.5 | MIT | runtime |
| tzdata | 2026.6 | Apache-2.0 | runtime |
| tzlocal | 5.4.5 | MIT | runtime |
| urllib3 | 2.8.0 | MIT | runtime |
| uvicorn | 0.54.0 | BSD-3-Clause | runtime |
| uvloop | 0.23.0 | MIT OR Apache-2.0 | runtime |
| vine | 5.1.0 | BSD-3-Clause | runtime |
| watchfiles | 1.3.0 | MIT | runtime |
| wcwidth | 0.9.4 | MIT | runtime |
| websockets | 17.4 | BSD-3-Clause | runtime |
| wsproto | 1.3.2 | MIT | runtime |
| Chromium (Playwright build) | - | BSD-3-Clause | runtime |
| DejaVu fonts (`fonts-dejavu-core`) | - | Bitstream Vera / public domain (permissive) | runtime |
| pytest | - | MIT | dev |
| ruff | - | MIT | dev |
| pip-audit | - | Apache-2.0 | dev |

## AI (services/ai)

| Package | Version | Licence | Scope |
|---|---|---|---|
| fastapi | 0.165.0 | MIT | runtime |
| starlette | 1.10.0 | BSD-3-Clause | runtime |
| uvicorn | 0.54.0 | BSD-3-Clause | runtime |
| pydantic | 2.14.4 | MIT | runtime |
| pydantic-core | 2.50.5 | MIT | runtime |
| httpx | 0.28.1 | BSD-3-Clause | runtime |
| httpcore | 1.0.9 | BSD-3-Clause | runtime |
| h11 | 0.16.0 | MIT | runtime |
| anyio | 4.16.0 | MIT | runtime |
| idna | 3.20 | BSD-3-Clause | runtime |
| click | 8.5.1 | BSD-3-Clause | runtime |
| annotated-doc | 0.0.7 | MIT | runtime |
| annotated-types | 0.8.0 | MIT | runtime |
| typing-inspection | 0.4.5 | MIT | runtime |
| opentelemetry-api | 1.45.2 | Apache-2.0 | runtime |
| typing-extensions | 4.16.0 | PSF-2.0 | runtime |
| certifi | 2026.11.20 | MPL-2.0 | runtime |
| pytest | 9.0.1 | MIT | dev |
| ruff | 0.14.5 | MIT | dev |
| iniconfig | 2.3.1 | MIT | dev |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause | dev |
| pluggy | 1.7.0 | MIT | dev |
| pygments | 2.21.0 | BSD-2-Clause | dev |

## Frontend (services/frontend)

| Package | Version | Licence | Scope |
|---|---|---|---|
| @fontsource/ibm-plex-sans | 5.3.0 | OFL-1.1 | runtime |
| @radix-ui/react-dialog | 1.3.1 | MIT | runtime |
| @radix-ui/react-dropdown-menu | 2.2.1 | MIT | runtime |
| @radix-ui/react-slider | 1.6.1 | MIT | runtime |
| @radix-ui/react-tabs | 1.2.1 | MIT | runtime |
| cmdk | 1.1.1 | MIT | runtime |
| lucide-react | 1.77.0 | ISC | runtime |
| react | 19.3.1 | MIT | runtime |
| react-dom | 19.3.1 | MIT | runtime |
| react-router-dom | 7.18.6 | MIT | runtime |
| recharts | 3.11.0 | MIT | runtime |
| socket.io-client | 4.8.4 | MIT | runtime |
| @floating-ui/core | 1.8.0 | MIT | runtime |
| @floating-ui/dom | 1.8.0 | MIT | runtime |
| @floating-ui/react-dom | 2.1.9 | MIT | runtime |
| @floating-ui/utils | 0.2.12 | MIT | runtime |
| @radix-ui/number | 1.1.3 | MIT | runtime |
| @radix-ui/primitive | 1.2.0 | MIT | runtime |
| @radix-ui/react-arrow | 1.1.17 | MIT | runtime |
| @radix-ui/react-collection | 1.2.0 | MIT | runtime |
| @radix-ui/react-compose-refs | 1.1.5 | MIT | runtime |
| @radix-ui/react-context | 1.3.0 | MIT | runtime |
| @radix-ui/react-direction | 1.2.0 | MIT | runtime |
| @radix-ui/react-dismissable-layer | 1.2.1 | MIT | runtime |
| @radix-ui/react-focus-guards | 1.2.0 | MIT | runtime |
| @radix-ui/react-focus-scope | 1.3.1 | MIT | runtime |
| @radix-ui/react-id | 1.1.4 | MIT | runtime |
| @radix-ui/react-menu | 2.2.1 | MIT | runtime |
| @radix-ui/react-popper | 1.4.0 | MIT | runtime |
| @radix-ui/react-portal | 1.2.0 | MIT | runtime |
| @radix-ui/react-presence | 1.1.11 | MIT | runtime |
| @radix-ui/react-primitive | 2.2.0 | MIT | runtime |
| @radix-ui/react-roving-focus | 1.2.1 | MIT | runtime |
| @radix-ui/react-slot | 1.5.0 | MIT | runtime |
| @radix-ui/react-use-callback-ref | 1.1.5 | MIT | runtime |
| @radix-ui/react-use-controllable-state | 1.3.0 | MIT | runtime |
| @radix-ui/react-use-effect-event | 0.0.5 | MIT | runtime |
| @radix-ui/react-use-is-hydrated | 0.1.3 | MIT | runtime |
| @radix-ui/react-use-layout-effect | 1.1.4 | MIT | runtime |
| @radix-ui/react-use-rect | 1.1.4 | MIT | runtime |
| @radix-ui/react-use-size | 1.1.5 | MIT | runtime |
| @radix-ui/rect | 1.1.3 | MIT | runtime |
| @reduxjs/toolkit | 2.15.0 | MIT | runtime |
| @socket.io/component-emitter | 3.1.2 | MIT | runtime |
| @standard-schema/spec | 1.1.0 | MIT | runtime |
| @standard-schema/utils | 0.3.0 | MIT | runtime |
| @types/d3-array | 3.2.2 | MIT | runtime |
| @types/d3-color | 3.1.3 | MIT | runtime |
| @types/d3-ease | 3.0.2 | MIT | runtime |
| @types/d3-interpolate | 3.0.4 | MIT | runtime |
| @types/d3-path | 3.1.1 | MIT | runtime |
| @types/d3-scale | 4.0.9 | MIT | runtime |
| @types/d3-shape | 3.2.0 | MIT | runtime |
| @types/d3-time | 3.0.4 | MIT | runtime |
| @types/d3-timer | 3.0.2 | MIT | runtime |
| @types/react | 19.3.0 | MIT | runtime |
| @types/react-dom | 19.3.0 | MIT | runtime |
| @types/use-sync-external-store | 0.0.6 | MIT | runtime |
| aria-hidden | 1.2.6 | MIT | runtime |
| clsx | 2.1.1 | MIT | runtime |
| cookie | 1.1.1 | MIT | runtime |
| csstype | 3.2.4 | MIT | runtime |
| d3-array | 3.2.5 | ISC | runtime |
| d3-color | 3.1.1 | ISC | runtime |
| d3-ease | 3.0.2 | BSD-3-Clause | runtime |
| d3-format | 3.1.3 | ISC | runtime |
| d3-interpolate | 3.0.2 | ISC | runtime |
| d3-path | 3.1.1 | ISC | runtime |
| d3-scale | 4.0.3 | ISC | runtime |
| d3-shape | 3.2.1 | ISC | runtime |
| d3-time | 3.1.1 | ISC | runtime |
| d3-time-format | 4.1.1 | ISC | runtime |
| d3-timer | 3.0.2 | ISC | runtime |
| debug | 4.4.3 | MIT | runtime |
| decimal.js-light | 2.5.1 | MIT | runtime |
| detect-node-es | 1.1.0 | MIT | runtime |
| engine.io-client | 6.6.8 | MIT | runtime |
| engine.io-parser | 5.2.3 | MIT | runtime |
| es-toolkit | 1.53.2 | MIT | runtime |
| eventemitter3 | 5.0.4 | MIT | runtime |
| get-nonce | 1.0.1 | MIT | runtime |
| immer | 11.2.10 | MIT | runtime |
| internmap | 2.0.3 | ISC | runtime |
| ms | 2.1.3 | MIT | runtime |
| react-is | 19.3.1 | MIT | runtime |
| react-redux | 9.3.1 | MIT | runtime |
| react-remove-scroll | 2.7.2 | MIT | runtime |
| react-remove-scroll-bar | 2.3.8 | MIT | runtime |
| react-router | 7.18.6 | MIT | runtime |
| react-style-singleton | 2.2.3 | MIT | runtime |
| redux | 5.0.1 | MIT | runtime |
| redux-thunk | 3.1.0 | MIT | runtime |
| reselect | 5.2.0 | MIT | runtime |
| scheduler | 0.28.0 | MIT | runtime |
| set-cookie-parser | 2.7.3 | MIT | runtime |
| socket.io-parser | 4.2.7 | MIT | runtime |
| tiny-invariant | 1.3.3 | MIT | runtime |
| tslib | 2.9.1 | 0BSD | runtime |
| use-callback-ref | 1.3.3 | MIT | runtime |
| use-sidecar | 1.1.3 | MIT | runtime |
| use-sync-external-store | 1.7.0 | MIT | runtime |
| victory-vendor | 37.4.1 | MIT AND ISC AND BSD-3-Clause | runtime |
| ws | 8.21.3 | MIT | runtime |
| xmlhttprequest-ssl | 2.1.2 | MIT | runtime |
| vite, @vitejs/plugin-react, vitest, jsdom | - | MIT | build/test |
| typescript | - | Apache-2.0 | build/test |
| eslint, @eslint/js, typescript-eslint, eslint-plugin-react-hooks, globals | - | MIT | build/test |
| @testing-library/react, @testing-library/user-event, @testing-library/jest-dom | - | MIT | build/test |
| socket.io (dev mock server only) | - | MIT | build/test |
| @types/* | - | MIT | build/test |

## Container images

| Image | Licence | Use |
|---|---|---|
| postgres:16-alpine | PostgreSQL License | database |
| valkey/valkey:8-alpine | BSD-3-Clause | queue broker |
| chrislusf/seaweedfs:3.80 | Apache-2.0 | S3-compatible object storage |
| python:3.12-slim | PSF | base image, backend and ai |
| node:22-alpine | MIT | frontend build stage only |
| nginxinc/nginx-unprivileged | BSD-2-Clause | frontend runtime (static files) |
| ollama/ollama:0.40.16 | MIT | optional local LLM (profile `llm`) |
| Chromium (installed by Playwright) | BSD-3-Clause | page rendering, screenshots, PDF |

Fonts: DejaVu (`fonts-dejavu-core`, Bitstream Vera / public domain, permissive) is installed in the backend image for Polish glyphs in PDFs.

## Outside the MIT/Apache/BSD/ISC list

None of these is GPL, AGPL or LGPL. Each one is listed with the reason it is present, as stated in the source files.

| Package | Version | Licence | Where | Why |
|---|---|---|---|---|
| bidict | 0.24.1 | MPL-2.0 | Backend | hard dependency of python-socketio; weak file-level copyleft, not GPL-family |
| certifi | 2026.11.20 | MPL-2.0 | AI, Backend | CA bundle, hard dependency of httpx; used unmodified |
| typing-extensions | 4.16.0 | PSF-2.0 | AI, Backend | needed by fastapi and pydantic (not removable) |
| greenlet | 3.5.6 | MIT AND PSF-2.0 | Backend | transitive dependency; permissive |
| scramp | 1.5.0 | MIT-0 | Backend | transitive dependency; permissive (MIT No Attribution) |
| tslib | 2.9.1 | 0BSD | Frontend | transitive runtime dependency of the frontend; permissive (Zero-Clause BSD) |
| @fontsource/ibm-plex-sans | 5.3.0 | OFL-1.1 | Frontend | self-hosted UI typeface, bundled into the build |
| lightningcss | - | MPL-2.0 | Frontend | CSS minifier binary used by Vite at build time; not distributed (build-only) |
| caniuse-lite | - | CC-BY-4.0 | Frontend | browser data used at build time; not distributed |
| minimatch | - | BlueOak-1.0.0 | Frontend | build-time only; not distributed |
| lru-cache | - | BlueOak-1.0.0 | Frontend | build-time only; not distributed |
| DejaVu fonts (`fonts-dejavu-core`) | - | Bitstream Vera / public domain (permissive) | Backend | Polish glyphs in the PDF output |
