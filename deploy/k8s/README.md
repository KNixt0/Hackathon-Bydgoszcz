# InvestWatch na Kubernetes

Manifesty YAML dla tego samego stosu co `docker-compose.yml`: frontend, backend (api), worker, beat, ai, postgres, valkey, storage (SeaweedFS). Opcjonalnie ollama.

## Uruchomienie

Wymagania: Kubernetes 1.27+ z CNI obsługującym NetworkPolicy (Calico, Cilium), `kubectl` 1.27+ (ma wbudowany kustomize), Docker do zbudowania obrazów, domyślna StorageClass (3 PVC: 5 + 10 + 1 GiB).

```sh
./deploy/k8s/build-images.sh                       # 4 obrazy z tagiem :demo
cp deploy/k8s/secrets.env.example deploy/k8s/secrets.env   # zmień wartości (openssl rand -hex 32)
kubectl apply -k deploy/k8s
kubectl -n investwatch rollout status deploy/backend --timeout=10m
kubectl -n investwatch port-forward svc/frontend 3000:8080
```

Potem http://localhost:3000, logowanie przyciskami demo (analityk / kierownik). Formularz obywatela: http://localhost:3000/zglos. Pierwszy start importuje prawdziwe próbki z `samples/real/` (ok. minuty).

Klaster bez rejestru: `SAVE=1 ./deploy/k8s/build-images.sh` zapisuje `investwatch-images.tar`; załaduj go do węzłów (`kind load image-archive`, `k3s ctr images import`, `minikube image load`). Własny rejestr: `REGISTRY=rejestr.local/investwatch ./deploy/k8s/build-images.sh` i ustaw `newName` w `kustomization.yaml`.

## Bezpieczeństwo

- Namespace wymusza Pod Security Standard `restricted`: każdy kontener jako użytkownik nie-root, bez eskalacji uprawnień, bez capabilities, seccomp `RuntimeDefault`, system plików tylko do odczytu (zapis wyłącznie do wolumenów).
- NetworkPolicy: domyślnie wszystko zablokowane. Z zewnątrz dostępny jest tylko frontend (8080); bazy, kolejka, storage i ai przyjmują ruch wyłącznie od api/worker/beat. Żaden pod nie ma dostępu do internetu.
- Brak tokenów ServiceAccount w podach, brak Service typu NodePort/LoadBalancer.
- Sekrety tylko w `secrets.env` (ignorowany przez git) → Secret generowany przez kustomize.
- Bez internetu system działa na próbkach z `samples/real/` (publiczne strony i filmy instytucji finansowych). Odświeżanie rejestrów KNF i skanowanie nowych stron wymagają włączenia `optional/worker-internet.yaml` (tylko HTTP/HTTPS, bez adresów prywatnych).

## Konfiguracja

Ustawienia niejawne: `config.yaml` (te same zmienne co w `.env.example`, opis w głównym README). Po zmianie: `kubectl apply -k deploy/k8s` i `kubectl -n investwatch rollout restart deploy`.

- Skalowanie workerów: `kubectl -n investwatch scale deploy/worker --replicas=3`. `beat` i `backend` muszą mieć 1 replikę (harmonogram cron, limity zgłoszeń w pamięci).
- Model lokalny: `optional/ollama.yaml` (instrukcja w pliku; 16 GB RAM).
- Ingress: brak w zestawie; skieruj swój kontroler na Service `frontend:8080` (NetworkPolicy już na to pozwala).

## Zasoby

Requesty łącznie ok. 1,25 CPU / 2,4 GiB, limity ok. 9,5 CPU / 10,3 GiB (bez ollamy). Worker z Chromium ma limit 3 GiB i `/dev/shm` 1 GiB.

## Usunięcie

```sh
kubectl delete namespace investwatch
```
