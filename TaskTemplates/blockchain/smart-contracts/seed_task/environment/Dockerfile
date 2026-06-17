FROM python:3.12-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /root

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    ca-certificates \
    curl \
    findutils \
    git \
    jq \
    tini \
    && rm -rf /var/lib/apt/lists/*

RUN ln -sf /bin/bash /bin/sh \
    && chmod 755 /bin/sh /bin/bash /usr/bin/tini

RUN pip install --no-cache-dir \
    pandas==2.2.3 \
    pytest==8.3.5

RUN mkdir -p /root/environment/data /root/environment/protocol /root/environment/pipeline /root/environment/skills \
    /root/.codex/skills /root/answer /logs/agent/skills /logs/verifier

COPY data /root/environment/data
COPY protocol /root/environment/protocol
COPY pipeline /root/environment/pipeline
COPY skills /root/environment/skills
COPY skills /root/.codex/skills
COPY skills /logs/agent/skills

RUN find /root/environment/data -type f -print0 | sort -z | xargs -0 sha256sum > /opt/token-review-data.sha256 \
    && chmod -R a+rX /root/environment /root/.codex/skills /logs/agent/skills \
    && chmod -R a+rwX /root/answer /logs
