# Licences – services/backend

Every package installed from `requirements.txt` (direct and transitive). No GPL / AGPL / LGPL.
PostgreSQL driver: `pg8000` (BSD) instead of psycopg (LGPL). Queue broker: Valkey (BSD) via the MIT `redis` client.

Two transitive packages are MPL-2.0 (`bidict`, `certifi`). They are unmodified, required by the mandated
stack (python-socketio, httpx) and MPL-2.0 is not a GPL-family licence, but it is outside the
MIT/Apache/BSD/ISC list, so it is flagged here for the owner's decision.

| Package | Version | Licence | Use | Note |
|---|---|---|---|---|
| amqp | 5.4.2 | BSD-3-Clause | transitive |  |
| annotated-doc | 0.0.7 | MIT | transitive |  |
| annotated-types | 0.8.0 | MIT | transitive |  |
| anyio | 4.16.0 | MIT | transitive |  |
| argon2-cffi | 25.1.0 | MIT | direct | argon2id password hashes |
| argon2-cffi-bindings | 26.2.0 | MIT | transitive |  |
| asn1crypto | 1.5.1 | MIT | transitive |  |
| beautifulsoup4 | 4.15.0 | MIT | direct |  |
| bidict | 0.24.1 | MPL-2.0 | transitive | weak copyleft (file level), not GPL-family; hard dependency of python-socketio |
| billiard | 4.3.2 | BSD-3-Clause | transitive |  |
| boto3 | 1.44.9 | Apache-2.0 | direct |  |
| botocore | 1.44.9 | Apache-2.0 | transitive |  |
| celery | 5.7.0 | BSD-3-Clause | direct |  |
| certifi | 2026.11.20 | MPL-2.0 | transitive | weak copyleft (file level), not GPL-family; CA bundle data, hard dependency of httpx |
| cffi | 2.1.1 | MIT-0 | transitive | permissive (MIT No Attribution) |
| click | 8.5.1 | BSD-3-Clause | transitive |  |
| click-didyoumean | 0.3.1 | MIT | transitive |  |
| click-plugins | 1.1.1.2 | BSD-3-Clause | transitive |  |
| click-repl | 0.4.1 | MIT | transitive |  |
| fastapi | 0.165.0 | MIT | direct |  |
| greenlet | 3.5.6 | MIT AND PSF-2.0 | transitive | permissive |
| h11 | 0.16.0 | MIT | transitive |  |
| httpcore | 1.0.9 | BSD-3-Clause | transitive |  |
| httptools | 0.9.0 | MIT | transitive |  |
| httpx | 0.28.1 | BSD-3-Clause | direct |  |
| idna | 3.20 | BSD-3-Clause | transitive |  |
| jinja2 | 3.1.6 | BSD-3-Clause | direct |  |
| jmespath | 1.1.0 | MIT | transitive |  |
| kombu | 5.7.0 | BSD-3-Clause | transitive |  |
| markupsafe | 3.0.4 | BSD-3-Clause | transitive |  |
| opentelemetry-api | 1.45.2 | Apache-2.0 | transitive |  |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause | direct | needed by kombu's redis transport |
| pg8000 | 1.31.6 | BSD-3-Clause | direct |  |
| playwright | 1.65.2 | Apache-2.0 | direct |  |
| prompt-toolkit | 3.0.53 | BSD-3-Clause | transitive |  |
| pycparser | 3.12 | BSD-3-Clause | transitive |  |
| pydantic | 2.14.4 | MIT | transitive |  |
| pydantic-core | 2.50.5 | MIT | transitive |  |
| pydantic-settings | 2.16.3 | MIT | direct |  |
| pyjwt | 2.15.1 | MIT | direct | session tokens (HS256) |
| python-dateutil | 2.9.0.post0 | Apache-2.0 OR BSD-3-Clause | transitive |  |
| python-dotenv | 1.2.4 | BSD-3-Clause | transitive |  |
| python-engineio | 4.15.1 | MIT | transitive |  |
| python-socketio | 5.18.1 | MIT | direct |  |
| pyyaml | 6.0.4 | MIT | transitive |  |
| redis | 8.1.0 | MIT | direct |  |
| s3transfer | 0.19.3 | Apache-2.0 | transitive |  |
| scramp | 1.5.0 | MIT-0 | transitive | permissive (MIT No Attribution) |
| simple-websocket | 1.1.0 | MIT | transitive |  |
| six | 1.17.0 | MIT | transitive |  |
| soupsieve | 4.1.3 | MIT | transitive |  |
| sqlalchemy | 2.1.9 | MIT | direct |  |
| starlette | 1.10.0 | BSD-3-Clause | transitive |  |
| typing-extensions | 4.16.0 | PSF-2.0 | transitive | permissive (Python Software Foundation licence) |
| typing-inspection | 0.4.5 | MIT | transitive |  |
| tzdata | 2026.6 | Apache-2.0 | transitive |  |
| tzlocal | 5.4.5 | MIT | transitive |  |
| urllib3 | 2.8.0 | MIT | transitive |  |
| uvicorn | 0.54.0 | BSD-3-Clause | direct |  |
| uvloop | 0.23.0 | MIT OR Apache-2.0 | transitive |  |
| vine | 5.1.0 | BSD-3-Clause | transitive |  |
| watchfiles | 1.3.0 | MIT | transitive |  |
| wcwidth | 0.9.4 | MIT | transitive |  |
| websockets | 17.4 | BSD-3-Clause | transitive |  |
| wsproto | 1.3.2 | MIT | transitive |  |

## Not Python packages

| Component | Licence | Use |
|---|---|---|
| Chromium (Playwright build) | BSD-3-Clause | page rendering, screenshots, PDF |
| Playwright base image `mcr.microsoft.com/playwright/python` | Apache-2.0 | Docker base (Ubuntu 24.04) |
| DejaVu fonts (`fonts-dejavu-core`) | Bitstream Vera / public domain (permissive) | Polish glyphs in the PDF |

Dev only (not in the image): pytest (MIT), ruff (MIT), pip-audit (Apache-2.0).
