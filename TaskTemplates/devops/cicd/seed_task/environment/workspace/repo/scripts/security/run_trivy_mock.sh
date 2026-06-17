#!/bin/bash
set -euo pipefail

grep -q "^FROM mcr.microsoft.com/devcontainers/javascript-node:1-20-bookworm" Dockerfile
grep -q "^USER node" Dockerfile

echo "security scan contract passed"
