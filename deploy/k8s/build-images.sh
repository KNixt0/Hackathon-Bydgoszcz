#!/bin/sh
# Builds the four images used by deploy/k8s. Run from anywhere.
# Optional: REGISTRY=registry.internal/investwatch ./build-images.sh  (tags and pushes there)
# Optional: SAVE=1 ./build-images.sh  (writes investwatch-images.tar for an offline cluster)
set -eu
cd "$(dirname "$0")/../.."
TAG="${TAG:-demo}"

docker build -t "investwatch-backend:$TAG" services/backend
docker build -t "investwatch-ai:$TAG" services/ai
docker build -t "investwatch-frontend:$TAG" services/frontend
docker build -f deploy/k8s/samples.Dockerfile -t "investwatch-samples:$TAG" .

if [ -n "${REGISTRY:-}" ]; then
  for img in backend ai frontend samples; do
    docker tag "investwatch-$img:$TAG" "$REGISTRY/investwatch-$img:$TAG"
    docker push "$REGISTRY/investwatch-$img:$TAG"
  done
fi

if [ -n "${SAVE:-}" ]; then
  docker save -o investwatch-images.tar \
    "investwatch-backend:$TAG" "investwatch-ai:$TAG" "investwatch-frontend:$TAG" "investwatch-samples:$TAG" \
    postgres:16-alpine valkey/valkey:8-alpine chrislusf/seaweedfs:3.80
  echo "investwatch-images.tar written"
fi
