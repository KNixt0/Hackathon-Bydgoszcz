# InvestWatch

System on-premise dla UKNF: zbiera reklamy i oferty, a następnie oznacza (1) reklamy firm inwestycyjnych prowadzone przez podmioty trzecie i finfluencerów, (2) niewystarczające informacje o ryzyku względem 18 kryteriów UKNF, (3) nielicencjonowane doradztwo inwestycyjne.

## Szybki start

```sh
cp .env.example .env
docker compose up --build
```

Dashboard: http://localhost:3000. Przy pierwszym starcie próbki z `samples/` są pobierane i oceniane tym samym pipeline'em co dane produkcyjne (ok. minuty).
Skalowanie workerów: `docker compose up --scale worker=3`.

## Wymagania sprzętowe

- Docker z Compose v2.
- Bez modelu lokalnego: 4 CPU, 6 GB RAM, ok. 3 GB miejsca na dysku.
- Z modelem lokalnym (`gemma4:e4b` + `embeddinggemma:300m` przez Ollama): 16 GB RAM, ok. 12 GB miejsca na dysku.
- Po zbudowaniu obrazów system działa offline.

## Serwisy

| Serwis | Technologia | Port / rola |
|---|---|---|
| frontend | React + nginx | `FRONTEND_PORT` (3000) |
| backend | FastAPI + Socket.IO | `BACKEND_PORT` (8000) |
| worker | Celery, scraper httpx + Playwright | kolejka zadań |
| beat | Celery beat | harmonogram (cron) |
| ai | FastAPI | `AI_PORT` (8001): wtyczki modułów 1-3, scoring |
| postgres | PostgreSQL 16 | baza danych |
| valkey | Valkey 8 | kolejka (broker) |
| storage | SeaweedFS | S3 API: archiwum HTML i zrzuty ekranu |
| ollama | Ollama (profil `llm`) | opcjonalny model lokalny |

## Konfiguracja (.env)

Wartości domyślne z `.env.example`.

| Zmienna | Domyślnie | Znaczenie |
|---|---|---|
| `FRONTEND_PORT` | 3000 | port UI na hoście |
| `BACKEND_PORT` | 8000 | port API na hoście |
| `AI_PORT` | 8001 | port usługi ai |
| `POSTGRES_USER` | investwatch | użytkownik bazy |
| `POSTGRES_PASSWORD` | change-me | hasło bazy |
| `POSTGRES_DB` | investwatch | nazwa bazy |
| `S3_ACCESS_KEY` | change-me-access | klucz dostępu do storage |
| `S3_SECRET_KEY` | change-me-secret | sekret storage |
| `S3_BUCKET` | evidence | bucket na archiwum |
| `SAMPLES_HOST_DIR` | ./samples | katalog próbek (montowany tylko do odczytu) |
| `SEED_ON_START` | true | import próbek przy pierwszym starcie |
| `ALERT_THRESHOLD` | 70 | próg wyniku dla alertu |
| `PROXY_URLS` | (puste) | lista proxy dla scrapera |
| `RESCAN_CRON` | `0 */6 * * *` | harmonogram ponownego skanowania |
| `REGISTRY_REFRESH_CRON` | `30 3 * * *` | harmonogram odświeżania rejestrów |
| `DISCOVERY_CRON` | `15 */6 * * *` | harmonogram wyszukiwania źródeł |
| `RESCAN_SAMPLES` | false | ponowne skanowanie próbek |
| `RESPECT_ROBOTS` | true | przestrzeganie robots.txt |
| `WORKER_CONCURRENCY` | 2 | liczba równoległych zadań workera |
| `LOG_LEVEL` | INFO | poziom logów |
| `LLM_ENABLED` | false | włączenie modelu lokalnego |
| `OLLAMA_URL` | http://ollama:11434 | adres serwera Ollama |
| `OLLAMA_MODEL` | gemma4:e4b | model generatywny |
| `EMBEDDINGS_BACKEND` | hash | `hash` lub `ollama` |
| `OLLAMA_EMBED_MODEL` | embeddinggemma:300m | model embeddingów |
| `LLM_TIMEOUT_S` | 60 | limit czasu zapytania do modelu (s) |

## Model lokalny (opcjonalnie)

```sh
docker compose --profile llm up
docker compose exec ollama ollama pull gemma4:e4b
docker compose exec ollama ollama pull embeddinggemma:300m
```

W `.env` ustaw `LLM_ENABLED=true` i `EMBEDDINGS_BACKEND=ollama`. Dla Ollamy działającej na hoście: `OLLAMA_URL=http://host.docker.internal:11434`.
Bez modelu silnik działa na regułach i scoringu statystycznym.

## Próbki z pendrive'a

Ustaw `SAMPLES_HOST_DIR` na katalog na pendrive, a następnie w menu demo dashboardu wybierz "Importuj próbki" (lub `POST /api/samples/import`). Format: `coord/contracts/api.md`.

## Testy

```sh
./scripts/check.sh
```

## Dokumentacja

- `coord/contracts/incident.md`, `coord/contracts/api.md`, `docs/AI-PROCESS.md`, `docs/DEMO.md`, `THIRD_PARTY_LICENSES.md`
- Narzędzia zespołu do pracy z agentami AI (nie są częścią produktu): `SWARM.md`.
