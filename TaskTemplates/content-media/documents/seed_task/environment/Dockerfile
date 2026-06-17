FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV HOME=/root
ENV TASK_ROOT=/app
ENV TASK_BRIEFING_ROOT=/app/briefing
ENV TASK_WORKSPACE_ROOT=/app/workspace
ENV TASK_OUTPUT_ROOT=/app/output

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        coreutils \
        curl \
        findutils \
        git \
        grep \
        libreoffice-core \
        libreoffice-writer \
        nodejs \
        npm \
        pandoc \
        procps \
        ripgrep \
        sed \
        tini \
        unzip \
        zip \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    defusedxml \
    matplotlib \
    pandas \
    pillow \
    python-docx \
    pytest \
    pytest-json-ctrf \
    requests

COPY . /opt/documents-task-env
COPY skills /opt/documents-task-env/skills
COPY skills /root/.codex/skills
COPY skills /root/.claude/skills
COPY skills /etc/claude-code/.claude/skills
COPY skills /logs/agent/skills

RUN mkdir -p /app/briefing /app/workspace /app/output /root/.codex/skills /root/.claude/skills /etc/claude-code/.claude/skills /logs/agent/skills /logs/verifier /opt/task-baselines \
    && cp -R /opt/documents-task-env/briefing/. /app/briefing/ \
    && cp -R /opt/documents-task-env/workspace/. /app/workspace/ \
    && find /app/briefing -type f -print0 | sort -z | xargs -0 sha256sum > /opt/task-baselines/briefing.sha256 \
    && chmod -R a+rwX /app/workspace /app/output /logs \
    && chmod 755 /app/workspace/build_packet.py \
    && chmod 644 /opt/task-baselines/briefing.sha256

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/bin/bash"]
