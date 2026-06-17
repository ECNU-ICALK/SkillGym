FROM node:20-bookworm

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \

WORKDIR /root

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    ca-certificates \
    findutils \
    curl \
    git \
    jq \
    python3 \
    python3-pytest \
    python3-yaml \
    python-is-python3 \
    tini \
    && rm -rf /var/lib/apt/lists/*

RUN ln -sf /bin/bash /bin/sh \
    && chmod 755 /bin/sh /bin/bash /usr/bin/tini

RUN mkdir -p /opt/task-env/spec /opt/task-env/workspace /opt/task-env/skills \
    /root/workspace /root/.codex/skills /root/workspace/out /logs/agent/skills /logs/verifier

COPY data/spec /opt/task-env/spec
COPY workspace /opt/task-env/workspace
COPY skills /opt/task-env/skills
COPY skills /root/.codex/skills
COPY skills /logs/agent/skills

RUN cp -R /opt/task-env/spec /root/workspace/spec \
    && cp -R /opt/task-env/workspace/. /root/workspace/ \
    && cd /root/workspace \
    && npm install \
    && find /root/workspace/spec -type f -print0 | sort -z | xargs -0 sha256sum > /opt/defi-spec.sha256 \
    && chmod -R a+rX /root/workspace /root/.codex/skills /logs/agent/skills \
    && chmod -R a+rwX /root/workspace/out /logs
