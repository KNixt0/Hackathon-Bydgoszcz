# Proces wytwarzania z asystentami AI

Kod powstaje z pomocą agentów Claude Code, ale każdą zmianę sprawdzają automaty i zatwierdza człowiek. AI służy do pisania kodu. Decyzje i odpowiedzialność należą do zespołu.

## 1. Reguły i kontekst dla agentów

| Plik | Rola |
|---|---|
| [CLAUDE.md](../CLAUDE.md) | Instrukcje ładowane przez każdego agenta: twarde reguły, sposób pracy |
| [coord/GUIDELINES.md](../coord/GUIDELINES.md) | Wymogi z briefu: on-premise, licencje, sekrety, separacja serwisów |
| [coord/PROTOCOL.md](../coord/PROTOCOL.md) | Cykl zadania, format przekazania pracy (blok YAML), zasady gałęzi |
| [coord/contracts/](../coord/contracts/) | Kontrakty między serwisami. Ich zmiana wymaga decyzji człowieka |
| [coord/prompts/](../coord/prompts/) | Wersjonowane prompty ról: planer, budowniczy, lead |

Każde zadanie (issue) ma listę plików, które agent może zmienić (`Owns`). Agent nie wychodzi poza nią. Gdy reguła blokuje zadanie, oznacza je `needs-decision` i czeka na człowieka.

## 2. Podział ról: człowiek i AI

| Rola | Kto | Model / effort |
|---|---|---|
| Decyzje produktowe, architektura, kontrakty, zatwierdzenie merge | **Człowiek** | — |
| Planer: dzieli plan na zadania 1–3 h | AI | Opus / high |
| Budowniczy: implementacja jednego zadania | AI | Sonnet / medium (Opus lub Haiku zależnie od trudności) |
| Weryfikator: niezależna recenzja PR | AI | Opus / high, inny model niż autor |
| Lead: deleguje i merguje, nie pisze kodu | AI | Sonnet / medium |

Konfiguracja jest w [coord/roles.json](../coord/roles.json), a uzasadnienie w [coord/roles.md](../coord/roles.md).

## 3. Human-in-the-loop: bramki przed `main`

Każdy PR przechodzi przez te same bramki, zanim trafi do `main`:

1. **Testy i lint** (`scripts/check.sh` w CI).
2. **Bramka reguł** (`scripts/guard.sh`): brak płatnych API AI, brak `.env` i sekretów, brak `console.log`, osobny Dockerfile dla każdego serwisu.
3. **Bramka bezpieczeństwa** (`.github/workflows/security.yml`):
   - `gitleaks` szuka sekretów,
   - `pip-audit` i `npm audit` szukają podatności,
   - skan licencji blokuje GPL, AGPL i LGPL.
4. **Recenzja AI**: weryfikator z innym modelem zostawia werdykt `APPROVE` albo `CHANGES`.
5. **Zatwierdzenie przez człowieka**: właściciel repo zatwierdza ostatni commit każdego PR od innych osób. Bez tego check `owner-approval` jest czerwony.
6. **Merge** robi lead, dopiero gdy wszystkie bramki są zielone. Jeśli coś ominie bramki, `main-guard` otwiera zgłoszenie.

## 4. Ślad pracy (wkład człowieka)

- Commity tworzone z udziałem AI mają linię `Co-Authored-By: Claude …`.
- Decyzje ludzi (architektura, zakres, odpowiedzi mentorów) trafiają do [coord/decisions.md](../coord/decisions.md).
- Historia issue i PR pokazuje, kto zlecił zadanie, kto je zrecenzował i kto zatwierdził.

## 5. Narzędzia

Claude Code (agenci), GitHub Issues/PR (koordynacja), GitHub Actions (CI, bezpieczeństwo, recenzja). Postęp na żywo widać na animowanym podglądzie: `./swarm view`.

AI jest wyłącznie narzędziem deweloperskim. Produkt działa w 100% lokalnie na modelach open source.
