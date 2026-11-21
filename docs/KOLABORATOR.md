# Jak pracujesz u siebie (jeden kolaborator)

Pracujesz na **swoim laptopie i swoim koncie** (GitHub + narzędzie AI). Nie musisz z nikim się umawiać, bo zadania, blokady i recenzje są w GitHubie.

## 1. Raz na początku (10 minut)

Potrzebujesz:
- `git`, `python3` i GitHub CLI (`gh`),
- jedno narzędzie AI: Claude Code, Codex CLI, Gemini CLI, Cursor albo Antigravity.

Nie pracuj na służbowym laptopie.

```bash
gh auth login                                   # zaloguj swoje konto GitHub
git clone https://github.com/KNixt0/Hackathon-Bydgoszcz
cd Hackathon-Bydgoszcz
./swarm setup                                   # sprawdza narzędzia, pokazuje role
```

Jeśli używasz Claude Code, uruchom raz `claude` w tym folderze i zaakceptuj „trust this folder”.

## 2. Zamelduj się (na początku każdej sesji)

```bash
./swarm checkin --tool claude --model sonnet          # Claude Code
./swarm checkin --tool codex  --model gpt-5 --tier strong
./swarm checkin --tool cursor --model <model z Cursora>
```

Meldunek trafia do przypiętego issue **„Roster agentów”**. Lead widzi wtedy, kto jest online i na jakim modelu, i może zarezerwować dla Ciebie pasujące zadanie.

## 3. Wybierz, co robisz

```bash
./swarm tasks          # wolne zadania: numer, obszar (area:…), trudność
```

Obszary: `ui` (frontend), `api` (backend), `ai`, `devops`, `docs`.

### Wariant A: agent robi zadania sam (najprościej)

```bash
./swarm work --area ui --loop                     # tylko zadania UI, jedno po drugim
./swarm work --area ui,docs                       # jedno zadanie z UI albo docs
./swarm work --tool codex --model gpt-5 --area api --loop   # inne narzędzie
```

Worker sam:
1. bierze zadanie (najpierw te zarezerwowane dla Ciebie, potem pasujące do obszaru i poziomu modelu),
2. blokuje je na Ciebie,
3. tworzy osobny folder roboczy,
4. pracuje, odpala `check.sh` i otwiera PR.

### Wariant B: pracujesz w edytorze (Cursor, Antigravity, VS Code)

```bash
./swarm claim 12                 # zadanie #12 jest Twoje; dostajesz ścieżkę folderu
```

1. Otwórz w edytorze **wypisany folder** (`.worktrees/12`), nie główny katalog repo.
2. Pracuj z AI w edytorze. Zmieniaj tylko pliki z sekcji **Owns** w zadaniu (`gh issue view 12`).
3. Gdy skończysz:

```bash
./swarm done 12 "krótki opis zmian"
```

To polecenie:
1. odpala testy i bramkę reguł,
2. robi commit i push,
3. otwiera PR z blokiem przekazania,
4. przestawia zadanie na `status:review`.

Nie dokończysz? `./swarm unclaim 12 "na czym skończyłem"` oddaje zadanie do puli.

## 4. Co dzieje się z Twoim PR

Twój PR przechodzi kolejno:
1. **CI i bezpieczeństwo:** testy, `guard.sh`, gitleaks, audyt zależności i licencji.
2. **Recenzja Claude:** komentarze i werdykt `APPROVE` albo `CHANGES`.
3. **KNixt0 zatwierdza.** Bez tego PR nie wejdzie do `main`.
4. **Lead merguje.**

Jeśli dostaniesz uwagi, popraw je w tym samym folderze i zrób `git push`. PR zaktualizuje się sam, ale nowy commit wymaga ponownego zatwierdzenia.

## 5. Na koniec sesji

```bash
./swarm checkin --status offline
```

## Które narzędzie, jak podłączyć

| Narzędzie | Jak działa z repo |
|---|---|
| Claude Code (terminal) | `./swarm work …` (domyślne narzędzie) |
| Codex CLI | `./swarm work --tool codex --model …` |
| Gemini CLI | `./swarm work --tool gemini --model …` |
| Cursor / Antigravity (edytor) | Wariant B: `./swarm claim N`, praca w edytorze, `./swarm done N` |
| Agenci w chmurze: claude.ai, Cursor Background Agents, Codex cloud | aplikacje Claude, Cursor i Codex są zainstalowane na repo. Połącz GitHub w danym narzędziu (np. claude.ai → Settings → Connectors) i wybierz to repo |
| Antigravity w chmurze | łączy się przez Twoje konto GitHub (OAuth), więc jako kolaborator widzisz repo |

## Zasady w 5 punktach

Pełna lista jest w [coord/GUIDELINES.md](../coord/GUIDELINES.md).

1. W kodzie produktu nie ma płatnych API AI (OpenAI, Anthropic, Gemini…). AI w produkcie działa lokalnie.
2. Używaj tylko bibliotek na licencjach MIT, Apache, BSD lub ISC.
3. Hasła i klucze trzymaj tylko w `.env`, nigdy w kodzie.
4. We froncie nie zostawiaj `console.log`.
5. Zmieniaj tylko pliki z sekcji **Owns** swojego zadania. Jeśli musisz wyjść poza nie, napisz w zadaniu i poczekaj na decyzję.
