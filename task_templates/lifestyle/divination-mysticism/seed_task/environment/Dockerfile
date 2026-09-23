FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV ___X_CMD_ROOT_DATA=/root/.x-cmd.root/data
ENV CCAL_ACCESS_LOG=/var/log/ccal/access.log

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    ca-certificates \
    coreutils \
    curl \
    jq \
    nodejs \
    npm \
    ripgrep \
    xz-utils \
    && rm -rf /var/lib/apt/lists/*

COPY . /opt/divination-task-environment
COPY skills /opt/divination-task-environment/skills
COPY skills /root/.codex/skills
COPY skills /logs/agent/skills

RUN mkdir -p /root/environment/data /root/.codex/skills /logs/agent/skills /root/answer /logs/verifier /root/.x-cmd.root/data /var/log/ccal \
    && cp -R /opt/divination-task-environment/data/. /root/environment/data/ \
    && cp -R /opt/divination-task-environment/x-cmd-root-data/. /root/.x-cmd.root/data/ \
    && install -m 755 /opt/divination-task-environment/bin/x /usr/local/bin/x \
    && find /root/environment/data -type f -print0 | sort -z | xargs -0 sha256sum > /opt/divination-data.sha256 \
    && find /root/.x-cmd.root/data -type f -print0 | sort -z | xargs -0 sha256sum > /opt/divination-archive.sha256 \
    && sha256sum /usr/local/bin/x > /opt/divination-tool.sha256 \
    && chmod -R a+rX /root/environment/data /root/.x-cmd.root/data /root/.codex/skills /logs/agent/skills \
    && chmod 777 /var/log/ccal \
    && : > /var/log/ccal/access.log

CMD ["/bin/bash"]
