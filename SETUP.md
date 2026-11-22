# Instrukcja uruchomienia (dla jury)

Całość uruchamia się lokalnie jedną komendą. Nie są potrzebne konta, klucze API ani internet po zbudowaniu obrazów.

## 1. Wymagania

- Docker Desktop (lub Docker Engine) z Compose v2: `docker compose version`
- 4 CPU, 6 GB RAM wolne dla Dockera, ok. 3 GB miejsca na dysku
- Wolne porty: 3000 (UI), 8000 (API), 8001 (AI)

## 2. Pobranie repozytorium

```sh
git clone https://github.com/KNixt0/Hackathon-Bydgoszcz.git
cd Hackathon-Bydgoszcz
```

## 3. Konfiguracja

```sh
cp .env.example .env
```

Wartości domyślne wystarczają do demo. Nic nie trzeba zmieniać.

## 4. Start

```sh
docker compose up --build
```

Pierwsze budowanie obrazów trwa kilka minut. Potem backend sam importuje próbki z `samples/` i ocenia je tym samym pipeline'em co dane produkcyjne (ok. minuty).

## 5. Otwarcie aplikacji

1. Wejdź na http://localhost:3000
2. Kliknij „Zaloguj jako analityk (demo)” lub „Zaloguj jako kierownik (demo)”
3. Kolejka pokazuje prawdziwe dane z `samples/real/`. Tylko kierownik zatwierdza eskalacje, zmienia progi globalne i widzi dziennik audytu (`/audyt`).

Przebieg prezentacji krok po kroku: `docs/DEMO.md`.

## 6. Opcjonalnie

- Więcej workerów: `docker compose up --scale worker=3`
- Lokalny model AI (Ollama, wymaga 16 GB RAM): sekcja „Model lokalny” w `README.md`
- Własne próbki (np. z pendrive'a): ustaw `SAMPLES_HOST_DIR` w `.env` na ten katalog i w menu demo wybierz „Importuj próbki”
- Kubernetes: `deploy/k8s/README.md`
- Testy: `./scripts/check.sh`

## 7. Problemy

| Objaw | Rozwiązanie |
|---|---|
| `port is already allocated` | zmień `FRONTEND_PORT` / `BACKEND_PORT` / `AI_PORT` w `.env` |
| pusta kolejka zaraz po starcie | poczekaj ok. minuty na import próbek, odśwież stronę |
| chcesz zacząć od zera | `docker compose down -v`, potem znowu `docker compose up --build` |

## 8. Zatrzymanie

```sh
docker compose down
```
