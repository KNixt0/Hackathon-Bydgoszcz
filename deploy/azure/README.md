# InvestWatch na Azure (demo online)

Produkt pozostaje on-premise i open source. Azure służy tylko do pokazania tych samych kontenerów online:
jedna maszyna wirtualna z Linuksem uruchamia ten sam `docker compose`. Lokalna konfiguracja się nie zmienia.

## Wymagania
- Azure CLI (`az`), `ssh`, `scp`, `git`, `curl`, `python3`
- zalogowanie: `az login`
- klucz SSH (publiczny, domyślnie `~/.ssh/id_rsa.pub`; jeśli go nie ma, `az` wygeneruje parę kluczy)
- opcjonalnie: `cp deploy/azure/config.example.env deploy/azure/config.env` i zmiana wartości (region, rozmiar VM, `AZ_ALLOW_CIDR`)
- Docker Compose >= 2.24.6 (na VM instaluje się najnowszy z repozytorium Dockera; plik `compose.azure.yml` używa tagów `!reset` i `!override`)

## Wdrożenie (3 polecenia)
```bash
deploy/azure/01-provision.sh   # pokazuje plan i pyta o "yes", potem tworzy VM
deploy/azure/02-deploy.sh      # wysyła git HEAD, generuje hasła na VM, uruchamia stack
deploy/azure/03-status.sh      # stan VM, kontenery, /api/health, dozwolone adresy
```
Skrypt 02 wysyła ostatni commit (`git archive HEAD`); niezatwierdzone zmiany nie trafiają na VM.
Adres: `http://<publiczny IP>/`.

Model lokalny (wolny, na CPU): `ENABLE_LLM=yes deploy/azure/02-deploy.sh` (przy większej VM, np. `AZ_VM_SIZE=Standard_D8s_v5`).

## Dostęp dla innego adresu IP
```bash
deploy/azure/04-allow-ip.sh 203.0.113.7        # albo 203.0.113.0/24
```
Domyślnie porty 22 i 80 są otwarte tylko dla Twojego bieżącego publicznego IP (/32).
Skrypt odmawia `0.0.0.0/0`, chyba że ustawisz `AZ_ALLOW_PUBLIC=yes`.

## Brak pojemności w regionie
Subskrypcje studenckie ("Azure for Students") ograniczają regiony polityką i często nie mają wolnych zasobów. Przy pierwszym uruchomieniu Poland Central, Germany West Central i Italy North odrzucały każdy próbowany rozmiar (`SkuNotAvailable`); pojemność była tylko w Belgium Central dla `Standard_B4s_v2`. Gdy provisioning się nie powiedzie, spróbuj innego dozwolonego regionu lub rozmiaru:
```bash
AZ_LOCATION=belgiumcentral AZ_RESOURCE_GROUP=rg-investwatch-belgia AZ_VM_SIZE=Standard_B4s_v2 deploy/azure/01-provision.sh
```
Te same zmienne przekaż do kolejnych skryptów (lub wpisz je w `config.env`). Listę dozwolonych regionów pokaże `az account list-locations`, a dostępność rozmiaru `az vm list-skus`.

## Usunięcie
```bash
deploy/azure/99-teardown.sh    # pokazuje zasoby i usuwa całą grupę zasobów po potwierdzeniu
```
Usuwa też bazę i zarchiwizowane dowody na VM.

## Koszt
VM jest rozliczana, dopóki działa. Cena zależy od regionu i rozmiaru maszyny; sprawdź ją w kalkulatorze cen Azure
(Azure pricing calculator) przed uruchomieniem. Po pokazie usuń zasoby (`99-teardown.sh`).

## Ograniczenia
- tylko HTTP, bez TLS
- jedna VM, bez wysokiej dostępności
- panel ma logowanie, ale konta demo są publicznie znane, dlatego ograniczenie adresów IP zostaje obowiązkowe (nie ustawiaj `AZ_ALLOW_PUBLIC=yes`); backend i AI nie są publikowane na hoście, na zewnątrz wystawiony jest tylko frontend (port 80)
- model lokalny działa na CPU i jest wolny, dlatego domyślnie jest wyłączony
- pierwsze budowanie może być spowolnione limitami Docker Hub
