#!/bin/bash
set -euo pipefail

APP_ROOT="${APP_ROOT:-/app}"

cd "$APP_ROOT/workspace/repo"

cat > .github/workflows/verify.yml <<'YAML'
name: Saturn Checkout Verify

on:
  push:
    branches:
      - main
      - develop
    tags-ignore:
      - v*
  pull_request:
    branches:
      - main

jobs:
  verify:
    name: Review Verify Node ${{ matrix.node-version }}
    strategy:
      fail-fast: false
      matrix:
        node-version:
          - 18.x
          - 20.x
    uses: ./.github/workflows/reusable-verify.yml
    with:
      node-version: ${{ matrix.node-version }}
    secrets: inherit
YAML

cat > .github/workflows/reusable-verify.yml <<'YAML'
name: Saturn Reusable Verify

on:
  workflow_call:
    inputs:
      node-version:
        description: Node.js runtime selected by the caller workflow.
        required: true
        type: string
  workflow_dispatch:
    inputs:
      node-version:
        description: Node.js runtime selected for a direct verification rerun.
        required: true
        type: choice
        default: 20.x
        options:
          - 18.x
          - 20.x

jobs:
  verify:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ inputs.node-version }}
          cache: npm
      - run: npm ci
      - run: npm run lint
      - run: npm test
      - run: npm run security-scan
YAML

cat > .github/workflows/release.yml <<'YAML'
name: Saturn Checkout Release

on:
  push:
    branches:
      - main
    tags:
      - v*

permissions:
  contents: read
  packages: write

concurrency:
  group: saturn-checkout-release-${{ github.ref }}
  cancel-in-progress: false

env:
  REGISTRY: ghcr.io
  IMAGE_REPOSITORY: ghcr.io/saturn-labs/saturn-checkout

jobs:
  verify:
    name: Verify Node ${{ matrix.node-version }}
    strategy:
      fail-fast: false
      matrix:
        node-version:
          - 18.x
          - 20.x
    uses: ./.github/workflows/reusable-verify.yml
    with:
      node-version: ${{ matrix.node-version }}
    secrets: inherit

  publish:
    name: Publish Image
    if: github.event_name == 'push'
    needs: verify
    runs-on: ubuntu-latest
    outputs:
      image_ref: ${{ steps.image.outputs.image_ref }}
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.IMAGE_REPOSITORY }}
          tags: |
            type=ref,event=branch
            type=ref,event=pr
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
      - id: build
        uses: docker/build-push-action@v5
        with:
          context: .
          file: ./Dockerfile
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
      - id: image
        env:
          DIGEST: ${{ steps.build.outputs.digest }}
        run: |
          echo "image_ref=${IMAGE_REPOSITORY}@${DIGEST}" >> "$GITHUB_OUTPUT"

  staging:
    name: Staging
    if: github.event_name == 'push'
    needs: publish
    runs-on: ubuntu-latest
    environment:
      name: staging
    concurrency:
      group: saturn-checkout-staging
      cancel-in-progress: false
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.x"
      - uses: actions/setup-node@v4
        with:
          node-version: 20.x
          cache: npm
      - run: npm ci
      - run: python3 -m pip install pyyaml
      - env:
          SATURN_IMAGE_REF: ${{ needs.publish.outputs.image_ref }}
          SATURN_DELIVERY_REF: ${{ github.ref }}
        run: python3 scripts/deploy/render_manifest.py staging
      - run: npm run smoke
      - run: npm run e2e
      - uses: actions/upload-artifact@v4
        with:
          name: staging-delivery
          path: |
            artifacts/staging-manifest-summary.json
            artifacts/staging-manifest.yaml

  production:
    name: Production
    if: github.event_name == 'push' && startsWith(github.ref, 'refs/tags/v')
    needs: staging
    runs-on: ubuntu-latest
    environment:
      name: production
    concurrency:
      group: saturn-checkout-production
      cancel-in-progress: false
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.x"
      - uses: actions/setup-node@v4
        with:
          node-version: 20.x
          cache: npm
      - run: npm ci
      - run: python3 -m pip install pyyaml
      - env:
          SATURN_IMAGE_REF: ${{ needs.publish.outputs.image_ref }}
          SATURN_DELIVERY_REF: ${{ github.ref }}
        run: python3 scripts/deploy/render_manifest.py production
      - run: ./scripts/deploy/run_smoke.sh production
      - run: ./scripts/deploy/run_e2e.sh production
      - uses: actions/upload-artifact@v4
        with:
          name: production-delivery
          path: |
            artifacts/production-manifest-summary.json
            artifacts/production-manifest.yaml

  summary:
    name: Release Summary
    if: github.event_name == 'push' && startsWith(github.ref, 'refs/tags/v')
    needs: production
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.x"
      - run: python3 -m pip install pyyaml
      - run: python3 scripts/release/build_release_bundle.py
      - uses: actions/upload-artifact@v4
        with:
          name: saturn-checkout-release-bundle
          path: artifacts/release_bundle.json
YAML

cat > deploy/rollouts/checkout-production-rollout.yaml <<'YAML'
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: saturn-checkout
  labels:
    app: saturn-checkout
spec:
  replicas: 3
  selector:
    matchLabels:
      app: saturn-checkout
  template:
    metadata:
      labels:
        app: saturn-checkout
    spec:
      containers:
        - name: saturn-checkout
          image: ghcr.io/saturn-labs/saturn-checkout:latest
          ports:
            - containerPort: 8080
          readinessProbe:
            httpGet:
              path: /healthz
              port: 8080
          livenessProbe:
            httpGet:
              path: /healthz
              port: 8080
  strategy:
    canary:
      stableService: saturn-checkout-stable
      canaryService: saturn-checkout-canary
      analysis:
        templates:
          - templateName: saturn-success-rate
          - templateName: saturn-p95-latency
      steps:
        - setWeight: 10
        - pause:
            duration: 5m
        - setWeight: 25
        - pause:
            duration: 5m
        - setWeight: 50
        - pause:
            duration: 10m
        - setWeight: 100
YAML

npm ci
npm run lint
npm test
npm run security-scan
python3 scripts/deploy/render_manifest.py staging
npm run smoke
npm run e2e
python3 scripts/deploy/render_manifest.py production
./scripts/deploy/run_smoke.sh production
./scripts/deploy/run_e2e.sh production
SATURN_REPO_ROOT="$APP_ROOT/workspace/repo" \
SATURN_DATA_ROOT="$APP_ROOT/data" \
python3 scripts/release/build_release_bundle.py
