# Demo na żywo (3 minuty)

Przed wejściem: `docker compose up` działa (api, worker, beat, ai, baza, storage), przeglądarka na `http://localhost:3000`, wylogowana, DevTools → Console otwarte i puste, Wi-Fi wyłączone. Druga karta z `/zglos`. Sprawdź, że worker działa na świeżym obrazie (`docker compose up --build`), inaczej audyt wizualny się nie wykona.

| Czas | Co robisz | Co mówisz | Kryterium |
|---|---|---|---|
| 0:00-0:15 | Strona logowania → „Zaloguj jako analityk (demo)” → kolejka | „Jedna komenda, zero internetu, zero płatnych API. Role analityk i kierownik, każda czynność trafia do dziennika audytu.” | gotowość demo, zgodność |
| 0:15-1:05 | Sprawa pomarańczowa: kryteria z pomiarów → zrzut z ramką („Tekst główny 16 px, ostrzeżenie 10 px”) → graf → debata | „Strona wyrenderowana w trzech rozdzielczościach. Nie zgadujemy: ostrzeżenie ma 10 px przy tekście 16 px, kontrast i miejsce są zmierzone, a ramka pokazuje dowód na zrzucie. Graf: zarząd, agencja PR, influencer. Krytyk podważył część tez, więc rekomendacja to postępowanie wyjaśniające.” | zgodność, atrakcyjność |
| 1:05-1:20 | „Przejmij sprawę” → „Wnioskuj o eskalację” z uzasadnieniem | „Maszyna stanów: zmiana statusu wymaga powodu, a eskalację zatwierdza kierownik.” | architektura, zgodność |
| 1:20-1:50 | Karta `/zglos`: zgłoś adres sprawy z niskim wynikiem; wróć do kolejki | „Obywatel zgłasza bez logowania. Skrót zgłaszającego jest solony, bez fingerprintingu. Niski wynik AI i wiele zgłoszeń to anomalia tłumu: możliwy fałszywy negatyw, który silnik przeoczył.” | atrakcyjność, zgodność |
| 1:50-2:15 | Menu demo → „Uruchom próbkę” (czerwona) → alert WebSocket | „Nowa oferta, kolejka, scraper, trzy moduły, debata agentów. Alert pojawia się sam. Cytaty są dosłownymi fragmentami źródła.” | technologia |
| 2:15-2:35 | Kalibracja: jeden suwak w obie strony, odczytaj zdanie na głos | „W lewo: mniej przeoczonych naruszeń, więcej fałszywych alarmów. W prawo odwrotnie. Zdanie liczy się na oznaczonym zbiorze.” | zgodność, atrakcyjność |
| 2:35-2:50 | Logowanie jako kierownik → zatwierdzenie eskalacji → dziennik audytu (`/audyt`) | „Kierownik zatwierdza, a dziennik tylko dopisuje: kto, co, kiedy, dlaczego.” | architektura, zgodność |
| 2:50-3:00 | Slajd architektury | „Trzy serwisy, jeden obraz backendu, kolejka skalowana flagą, moduł czwarty to jeden plik. Proces: kontrakt przed kodem, rozłączne katalogi, lead weryfikuje na stosie.” | architektura, proces AI |

Plan awaryjny:
- Brak alertu na żywo: odśwież kartę i pokaż sprawę czerwoną z kolejki; opowiedz kroki z slajdu.
- Audyt wizualny nie działa (brak ramki): pokaż zrzut ekranu z przygotowanej sprawy i powiedz to wprost; reguły wracają do analizy statycznej HTML.
- Wszystko inne: film z tego samego przebiegu (maks. 3 min) i zrzuty ekranu w prezentacji.
