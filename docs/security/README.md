# Raport bezpieczeństwa zależności

Data: 2026-11-21

## Wyniki skanów

| Narzędzie | Zakres | Wynik | Plik wyjściowy |
|---|---|---|---|
| pip-audit | services/backend (requirements.txt) | "No known vulnerabilities found" (0 znanych podatności, 0 krytycznych) | docs/security/pip-audit-backend.txt |
| pip-audit | services/ai (requirements.txt) | "No known vulnerabilities found" (0 znanych podatności, 0 krytycznych) | docs/security/pip-audit-ai.txt |
| npm audit | services/frontend (wszystkie zależności) | "found 0 vulnerabilities" | docs/security/npm-audit-frontend.txt |
| npm audit --omit=dev | services/frontend (tylko produkcja) | total 0, critical 0 | docs/security/npm-audit-frontend-prod.json |
| guard.sh | reguły twarde repo, sekrety w plikach śledzonych | 5/5 ✓ (brak API AI, brak .env, brak oczywistych sekretów, brak console.log, compose obecny) | docs/security/guard.txt |
| gitleaks | pełny skan sekretów | nie uruchomiono (brak instalacji lokalnie) | - |
| Snyk | skan SCA | nie uruchomiono (brak CLI i konfiguracji) | - |

## Zasady

- **Sekrety:** dozwolony jest tylko `.env` (ignorowany przez git) oraz `.env.example` z fałszywymi wartościami. Ochrona: `scripts/guard.sh` lokalnie i w CI oraz gitleaks w CI (`.github/workflows/security.yml`).
- **Licencje:** dozwolone MIT, Apache-2.0, BSD, ISC. Zakaz GPL, AGPL i LGPL. Szczegóły i lista zależności: `THIRD_PARTY_LICENSES.md`.
- Podatności zapisane tutaj nie były naprawiane; zależności nie zostały zmienione.

## Ograniczenia

- Nie uruchomiono gitleaks lokalnie (narzędzie niezainstalowane; nie instalowano). Pełny skan sekretów działa w CI.
- Nie uruchomiono Snyk (brak CLI i konta). Użyto pip-audit i npm audit, zgodnie z treścią zadania.
- Skany pip-audit obejmują tylko pliki `requirements.txt`, nie pliki `requirements.in`.
- Wyniki odzwierciedlają bazy danych narzędzi w dniu skanu (2026-11-21); nowe podatności mogą się pojawić później.
- Nie sprawdzano obrazów kontenerów (np. mcr.microsoft.com/playwright/python:v1.65.2-noble, postgres, valkey).
