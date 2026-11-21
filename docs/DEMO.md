# Demo na żywo (3 minuty)

Przed wejściem: `docker compose up` działa, przeglądarka na `http://localhost:3000`, DevTools → Console otwarte i puste, Wi-Fi wyłączone.

| Czas | Co robisz | Co mówisz | Kryterium |
|---|---|---|---|
| 0:00 | Kolejka triage, konsola widoczna | „Jedna komenda, zero internetu, zero płatnych API. Każda sprawa na liście przeszła scraper i lokalny silnik.” | technologia, zgodność |
| 0:25 | Sprawa zielona (XTB) | „Dom maklerski z rejestru KNF, komplet ostrzeżeń. System nie robi alarmu tam, gdzie go nie ma.” | trafność |
| 0:45 | Sprawa pomarańczowa: macierz 18 reguł → graf → forensics → argumenty za i przeciw | „Pięć naruszeń z listy UKNF, każde z cytatem i przepisem. Graf: członek zarządu, agencja PR, influencer. Radca z KIRP nie wykonuje zawodu. Krytyk podważył część tez, dlatego rekomendacja to postępowanie wyjaśniające, nie zawiadomienie.” | unikalność |
| 1:30 | Kliknij cytat → panel źródeł → eksport PDF | „Urzędnik dostaje pakiet dowodowy: URL, czas pobrania, skrót treści, cytaty, przepisy.” | unikalność |
| 1:50 | Menu demo → „Uruchom próbkę” | „Nowa oferta wealth management. Kolejka, scraper, trzy moduły, debata agentów.” Alert pojawia się na górze. „Art. 76, brak w pięciu rejestrach, nieistniejący numer doradcy, farma świeżych kont.” | technologia |
| 2:20 | Kalibracja: przesuń suwak w obie strony | „Próg działa na surowym wyniku. W lewo: więcej wykryć i więcej fałszywych alarmów. W prawo: odwrotnie. Precision i recall liczone na oznaczonym zbiorze.” | technologia |
| 2:40 | Slajd architektury | „Trzy serwisy, kolejka skalowana jedną flagą, moduł czwarty to jeden plik. Proces pracy z AI: kontrakty, bramki, człowiek zatwierdza.” | architektura, proces |

Plan awaryjny: film z tego samego przebiegu (maks. 3 min) i zrzuty ekranu w prezentacji.
