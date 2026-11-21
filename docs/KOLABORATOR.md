# Jak pracujesz u siebie (jeden kolaborator)

> **Najkrócej:** sklonuj repo, otwórz je w swoim narzędziu AI i napisz agentowi **„Przeczytaj AGENT-START.md i wykonaj go.”** Agent sam przejdzie kroki poniżej. Ta strona opisuje je dla ludzi.

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

**Imię właściciela jest wymagane.** Bez niego meldunek jest odrzucany. Ustaw je raz na sesję terminala: `export SWARM_OPERATOR_NAME="Imię Nazwisko"` (albo dodaj `--name "Imię Nazwisko"` do `checkin`).

```bash
./swarm checkin --tool claude --model sonnet          # Claude Code
./swarm checkin --tool codex  --model gpt-5 --tier strong
./swarm checkin --tool cursor --model <model z Cursora>
```

Meldunek trafia do przypiętego issue **„Roster agentów”**. Lead widzi wtedy, kto jest online i na jakim modelu, i może zarezerwować dla Ciebie pasujące zadanie.

## 3. Twój przydział (ustala KNixt0)

Obszary pracy przydziela **KNixt0** według potrzeb, np. „UI” dla frontendu. Nie wybierasz ich sam, a agent nie pyta Cię o nie.

```bash
./swarm whoami         # Twój przydział: np. frontend, all albo BRAK
./swarm tasks          # wolne zadania (worker i tak weźmie tylko te z Twojego przydziału)
```

Bez przydziału worker się nie uruchomi, a agent tylko się zamelduje i poczeka.

### Wariant A: agent robi zadania sam (najprościej)

```bash
./swarm work --loop                                # zadania z Twojego przydziału, jedno po drugim
./swarm work --tool codex --model gpt-5 --loop     # inne narzędzie
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

## 5. Podgląd na żywo

Masz dwa różne podglądy.

**a) Podgląd produktu**, czyli tego, co budujesz. Wymaga Dockera i istnieje od momentu, gdy w repo jest `docker-compose.yml` (zadanie „skeleton”).

```bash
./swarm preview 12        # uruchamia całą aplikację z folderu zadania #12
./swarm preview           # wersja z main
```

Każde zadanie dostaje własne porty, więc kilka podglądów działa obok siebie:
- zadanie #12 to frontend `localhost:5120`, backend `6120`, AI `7120`,
- `main` to porty `5000`, `6000` i `7000`.

Adresy wypisują się na starcie. Frontend przeładowuje się sam po zapisaniu pliku.

**b) Podgląd pracy swarmu**: kto nad czym pracuje, lampki recenzji, merge'e.

```bash
./swarm view              # albo dwuklik w Swarm.command na Macu
```

## 6. Jak dobierany jest model i effort

- **Twój model wybierasz Ty.** Ustawiasz go flagami `--tool`, `--model` i `--tier`. Dla Claude Code bez flag worker bierze model z `coord/roles.json`:
  - zwykłe zadanie: Sonnet / medium,
  - zadanie z etykietą `model:opus`: Opus / high,
  - zadanie z etykietą `size:xs`: Haiku / low.
- **Lead dobiera zadania do modeli, a nie modele do zadań.** Oznacza trudność zadania. Poziom z Twojego meldunku decyduje, co możesz wziąć:
  - `strong` (Opus, GPT-5, Gemini Pro): wszystko, trudne zadania w pierwszej kolejności,
  - `standard` (Sonnet, GPT-5 mini, Gemini Flash): wszystko poza `model:opus`,
  - `light` (Haiku, małe modele lokalne): tylko `size:xs`.
- **Rezerwacje:** jeśli w meldunku podasz mocne strony (`--strengths frontend`), lead może zarezerwować dla Ciebie pasujące zadanie. Takie zadanie weźmiesz jako pierwsze.
- **Oszczędzanie limitów:** odpalaj `--loop` tylko wtedy, gdy masz limit do wykorzystania. Do drobnych zadań używaj tańszego modelu (`--tier light`).

## 7. Na koniec sesji

```bash
./swarm checkin --status offline
```

## Które narzędzie, jak podłączyć

| Narzędzie | Jak działa z repo |
|---|---|
| Claude Code (terminal) | `./swarm work …` (domyślne narzędzie) |
| Codex CLI | `./swarm work --tool codex --model …` |
| Gemini CLI | `./swarm work --tool gemini --model …` |
| Cursor / Antigravity (edytor) | Wariant B: `./swarm claim N`, praca w edytorze, podgląd `./swarm preview N`, potem `./swarm done N` |
| Agenci w chmurze: claude.ai, Cursor Background Agents, Codex cloud | aplikacje Claude, Cursor i Codex są zainstalowane na repo. Połącz GitHub w danym narzędziu (np. claude.ai → Settings → Connectors) i wybierz to repo |
| Antigravity w chmurze | łączy się przez Twoje konto GitHub (OAuth), więc jako kolaborator widzisz repo |

## Zasady w 5 punktach

Pełna lista jest w [coord/GUIDELINES.md](../coord/GUIDELINES.md).

1. W kodzie produktu nie ma płatnych API AI (OpenAI, Anthropic, Gemini…). AI w produkcie działa lokalnie.
2. Używaj tylko bibliotek na licencjach MIT, Apache, BSD lub ISC.
3. Hasła i klucze trzymaj tylko w `.env`, nigdy w kodzie.
4. We froncie nie zostawiaj `console.log`.
5. Zmieniaj tylko pliki z sekcji **Owns** swojego zadania. Jeśli musisz wyjść poza nie, napisz w zadaniu i poczekaj na decyzję.
