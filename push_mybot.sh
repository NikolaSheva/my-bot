#!/bin/bash
set -euo pipefail

# Переменные
IMAGE_NAME="quay.io/nikolasheva/my-bot"
VERSION_TAG="v2"
COMMIT_SHORT=$(git rev-parse --short HEAD)
SHA_TAG="sha-$COMMIT_SHORT"

# Логин (потребует username и токен робота)
echo "Логин в quay.io"
podman login quay.io

# Pуш версии v2
echo "Pushing $IMAGE_NAME:$VERSION_TAG..."
podman push "$IMAGE_NAME:$VERSION_TAG"

# Тег latest и пуш
echo "Tagging as latest and pushing..."
podman tag "$IMAGE_NAME:$VERSION_TAG" "$IMAGE_NAME:latest"
podman push "$IMAGE_NAME:latest"

# Тег sha-<commit> и пуш
echo "Tagging as $SHA_TAG and pushing..."
podman tag "$IMAGE_NAME:$VERSION_TAG" "$IMAGE_NAME:$SHA_TAG"
podman push "$IMAGE_NAME:$SHA_TAG"

echo "Все версии успешно запушены!"
