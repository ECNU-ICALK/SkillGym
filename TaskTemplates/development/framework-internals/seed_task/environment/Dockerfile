FROM node:20-bookworm

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV WORKSPACE_ROOT=/environment/workspace

RUN apt-get update \
  && apt-get install -y --no-install-recommends python3 python3-pip bash curl \
  && python3 -m pip install --break-system-packages pytest requests \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /root/environment

COPY . /root/environment
COPY skills /root/environment/skills
COPY skills /root/.codex/skills
COPY skills /logs/agent/skills

RUN mkdir -p /app/workspace /environment /root/.codex/skills /logs/agent/skills /logs/verifier \
  && cp -R /root/environment/workspace/. /app/workspace/ \
  && ln -s /app/workspace /environment/workspace \
  && python3 /root/environment/generate_decoys.py \
  && cd /app/workspace \
  && npm ci

WORKDIR /app/workspace

ENV PORT=3000
ENV NODE_ENV=production
