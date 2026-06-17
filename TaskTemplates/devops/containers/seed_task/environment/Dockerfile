FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV HELM_VERSION=v3.16.3

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    ca-certificates \
    curl \
    git \
    jq \
    nodejs \
    npm \
    python3 \
    python3-pip \
    python-is-python3 \
    tar \
    gzip \
    tini \
    && rm -rf /var/lib/apt/lists/*

RUN ARCH=amd64 && \
    curl -fsSL "https://get.helm.sh/helm-${HELM_VERSION}-linux-${ARCH}.tar.gz" -o /tmp/helm.tgz && \
    tar -xzf /tmp/helm.tgz -C /tmp && \
    mv /tmp/linux-${ARCH}/helm /usr/local/bin/helm && \
    chmod +x /usr/local/bin/helm && \
    rm -rf /tmp/helm.tgz /tmp/linux-${ARCH}

RUN pip3 install --break-system-packages --no-cache-dir \
    pytest==8.3.4 \
    pyyaml==6.0.2

WORKDIR /app

COPY . /tmp/task_environment
COPY skills /app/environment/skills
COPY skills /logs/agent/skills
COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills

RUN mkdir -p \
      /app/data \
      /app/workspace \
      /app/environment/skills \
      /logs/agent/skills \
      /root/.claude/skills \
      /root/.codex/skills \
      /root/.opencode/skill \
      /root/.goose/skills \
      /root/.factory/skills \
      /root/.agents/skills \
      /root/.gemini/skills && \
    cp -R /tmp/task_environment/data/. /app/data/ && \
    cp -R /tmp/task_environment/workspace/. /app/workspace/ && \
    chmod -R a+rX /app /logs/agent /root/.claude /root/.codex /root/.opencode /root/.goose /root/.factory /root/.agents /root/.gemini && \
    rm -rf /tmp/task_environment

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/bin/bash"]
