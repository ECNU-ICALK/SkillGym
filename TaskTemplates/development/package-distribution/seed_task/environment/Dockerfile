FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates git nodejs npm ripgrep \
    && rm -rf /var/lib/apt/lists/*

RUN python -m pip install --no-cache-dir build mypy pytest virtualenv

WORKDIR /workspace

COPY skills /workspace/skills
COPY skills /root/.codex/skills
COPY skills /logs/agent/skills
COPY workspace/ /workspace/

RUN mkdir -p /workspace/out
