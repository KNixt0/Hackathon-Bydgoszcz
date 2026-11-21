# Wnioski z demo i oszczędzanie tokenów

Stan na 2026-11-21, po wstrzymaniu demo portfolio. Uwagi samych agentów zbiera Roster (#2); dopiszemy je tutaj.

## Co wyszło w demo

| # | Problem | Status |
|---|---|---|
| 1 | Tożsamość dodana w trakcie: agenci pracowali bez imienia właściciela | **naprawione:** `operator_name` jest wymagane. `checkin` i `work` nie ruszą bez niego, a lead nie liczy agentów bez imienia |
| 2 | Uruchomieni agenci nie widzieli zmian reguł | **naprawione:** worker i AGENT-START robią `git pull` przed każdym zadaniem |
| 3 | Agenci pytali ludzi, jaki obszar brać | **naprawione:** obszary przydziela KNixt0 (`./swarm assign <login> ui`, issue #13). Bez przydziału agent tylko się melduje |
| 4 | Komentarze nie były widoczne w podglądzie 2D i nie dało się na nie odpowiadać | **naprawione:** panel „Komentarze” z odpowiedzią (przez Twój `gh`) i licznik nowych komentarzy na kartach |
| 5 | Lead na LLM w pętli co 5 minut zużywał tokeny na rutynę | **naprawione:** `./swarm lead-auto` robi mechanikę za 0 tokenów. Lead z LLM tylko na żądanie |
| 6 | Każdy PR czeka na kliknięcie KNixt0, a to wąskie gardło | **do decyzji:** np. drobne zadania (`size:xs`) merge'owane po zielonym CI i APPROVE weryfikatora, bez Twojego kliknięcia |
| 7 | Bez sekretu `CLAUDE_CODE_OAUTH_TOKEN` recenzja Claude jest pomijana i wygląda na zieloną | **otwarte:** dodaj sekret (instrukcja w SWARM.md). Do tego czasu jedyną recenzją jest Twoje zatwierdzenie |
| 8 | Budowniczowie na Opusie przy drobnych zadaniach | **zalecenie:** Sonnet jako domyślny, Opus tylko dla `model:opus` |
| 9 | Lead nie mógł zapisać `decisions.md` (push na main zablokowany) | **rozwiązane:** lead podaje decyzje w raporcie, a zapisuje je właściciel |
| 10 | Łańcuch zależności: na starcie tylko 2 zadania równolegle | **zalecenie dla planera:** najpierw kontrakty, potem więcej niezależnych zadań (dane, makiety i testy nie muszą czekać na szkielet) |
| 11 | Tarcia przy instalacji: podwójny klon, wolny instalator Claude, pytania `gh auth login` | **złagodzone:** ostrzeżenie w `./swarm setup` i instrukcje w KOLABORATOR.md / AGENT-START.md |

## Oszczędzanie tokenów

### Już wdrożone
- **`./swarm lead-auto`** (0 tokenów): odblokowanie zadań, merge przy wszystkich zielonych bramkach, zwalnianie porzuconych zadań, lista spraw dla człowieka. Lead z LLM nie działa już w pętli. Odpala się na jedną turę, gdy trzeba coś ocenić.
- **Weryfikator raz na PR** (przy otwarciu, nie przy każdym pushu). Małe PR-y (<150 linii) sprawdza Sonnet/medium, duże Opus/high. Ponowną recenzję uruchamia komentarz `@claude review`.
- **Model według trudności:** domyślnie Sonnet/medium, `size:xs` Haiku/low, Opus tylko przy `model:opus`.
- **Przydziały od KNixt0:** agenci nie biorą zadań, które potem oddają, i nie tracą tur na pytania o rolę.
- **Świeży kontekst na zadanie:** worker uruchamia nowego agenta (`claude -p`) dla każdego zadania, więc historia się nie ciągnie.
- **Bramki bez LLM:** `guard.sh`, `security.yml` i CI łapią proste błędy, zanim zobaczy je model.

### Zasady dla ludzi
1. **Jedno zadanie na jedną rozmowę.** Długie sesje za każdym razem wysyłają całą historię. Po zadaniu zacznij od nowa (`/clear` albo nowa sesja).
2. **Sonnet domyślnie.** Opus tylko do zadań z `model:opus` i do planowania.
3. **Nie wklejaj dużych logów ani plików.** Podaj ścieżkę i agent przeczyta tylko potrzebną część.
4. **`--loop` tylko wtedy, gdy masz limit do zużycia.** W przeciwnym razie jedno zadanie i koniec.
5. **Zamykaj nieużywane sesje**, szczególnie te na Opusie.
6. **Stabilne pliki reguł** (`AGENTS.md`, `CLAUDE.md`): narzędzia buforują powtarzalny początek kontekstu, więc częste zmiany tych plików kosztują.

## Do decyzji KNixt0
- Punkt 6: czy drobne zadania mogą być merge'owane bez Twojego kliknięcia?
- Punkt 7: dodać sekret weryfikatora?
- Czy po rozgrzewce zamknąć demo (issues #3–#10, PR-y #11 i #12) i usunąć `demo/`?
