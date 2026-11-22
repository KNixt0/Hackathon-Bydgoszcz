# Lokalny model AI

Uruchom Ollama z zainstalowanym modelem `gemma4:e4b`, a następnie z katalogu repozytorium:

```sh
bash services/ai/start-local.sh
```

Skrypt instaluje przypięte zależności w oddzielnym środowisku, sprawdza obecność modelu
i wymaga rzeczywistej odpowiedzi przed uruchomieniem usługi na `http://127.0.0.1:8001`.
Brak odpowiedzi kończy uruchomienie komunikatem błędu. Skrypt nie pobiera modelu automatycznie.
Własne `OLLAMA_URL`, `OLLAMA_MODEL`, `LLM_TIMEOUT_S` i `AI_PORT` można przekazać jako zmienne środowiskowe.

Po uruchomieniu `/health` powinno pokazywać `llm_enabled: true`, `llm_available: true`
i właściwy model. Odpowiedź `/analyze` musi dodatkowo zawierać `engine.llm_used: true`,
jeżeli zaakceptowano wynik modelu. Sam kod HTTP 200 nie potwierdza udziału modelu.
W razie awarii nadal działa analiza regułowa, a pole `llm_used` pozostaje zgodne z rzeczywistością.

Klient ogranicza liczbę równoległych wywołań modelu do jednego. Oczekiwanie w kolejce
nie zużywa limitu czasu pojedynczego wywołania HTTP. Identyczne poprawne odpowiedzi
są przechowywane przez pięć minut, najwyżej 64 wpisy. Pustych i błędnych odpowiedzi
nie zapisujemy. Każda analiza ponownie sprawdza cytaty modelu w aktualnym źródle.

W Docker Compose lokalny Ollama działa jako usługa z profilu `llm`.
Kontener ma własny katalog modeli; modele z aplikacji Ollama na Macu nie są w nim
automatycznie dostępne. Trzeba pobrać model do właściwej instancji i ustawić
`LLM_ENABLED=true`. Nie należy mylić adresu kontenera `http://ollama:11434`
z natywnym adresem `http://127.0.0.1:11434`.

Test obciążenia uruchamia prawdziwe lokalne wnioskowanie na procesorze w izolowanym
środowisku CI z małym modelem Qwen2.5 0.5B. Nie zastępuje testu Gemma na docelowym Macu.

Przy dwóch równoległych zadaniach backendu ustaw `AI_TIMEOUT_SECONDS` odpowiednio
powyżej łącznego czasu oczekiwania i dwóch odpowiedzi modelu na zadanie. W teście na
procesorze używamy 600 sekund; limit pojedynczego wywołania modelu wynosi 90 sekund.
Natywny skrypt używa 180 sekund dla modelu Gemma. To limity awarii, a nie oczekiwany czas odpowiedzi.
