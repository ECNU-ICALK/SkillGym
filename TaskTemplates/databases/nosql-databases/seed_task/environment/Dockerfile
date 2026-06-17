FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        python3-venv \
        curl \
        jq \
        git \
        ripgrep \
        ca-certificates \
        nodejs \
        npm \
        redis-server \
        redis-tools \
    && python3 -m pip install --break-system-packages redis==5.0.8 \
    && rm -rf /var/lib/apt/lists/*

COPY workspace /app/workspace
COPY . /tmp/task-environment
COPY skills /tmp/task-environment/skills
COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills
COPY skills /home/user/.codex/skills
COPY skills /logs/agent/skills

RUN chmod +x /app/workspace/bin/*.sh \
    && mkdir -p \
        /app/output \
        /logs/agent \
        /logs/agent/skills \
        /var/lib/redis \
        /var/log/redis \
        /root/.claude/skills \
        /root/.codex/skills \
        /root/.opencode/skill \
        /root/.goose/skills \
        /root/.factory/skills \
        /root/.agents/skills \
        /root/.gemini/skills \
        /home/user/.codex/skills

RUN printf '%s\n' \
    '#!/bin/bash' \
    'set -euo pipefail' \
    'if ! redis-cli -h 127.0.0.1 -p 6379 ping >/dev/null 2>&1; then' \
    '  redis-server --save "" --appendonly no --bind 127.0.0.1 --port 6379 --daemonize yes --dir /var/lib/redis >/tmp/redis-start.log 2>&1' \
    '  for _ in $(seq 1 40); do' \
    '    if redis-cli -h 127.0.0.1 -p 6379 ping >/dev/null 2>&1; then' \
    '      break' \
    '    fi' \
    '    sleep 0.25' \
    '  done' \
    'fi' \
    'cd /app/workspace' \
    'if [ "$#" -eq 0 ]; then' \
    '  exec /bin/bash' \
    'elif [ "$#" -eq 1 ]; then' \
    '  exec /bin/bash -lc "$1"' \
    'else' \
    '  exec "$@"' \
    'fi' \
    > /usr/local/bin/nosql-template-entrypoint \
    && chmod 755 /usr/local/bin/nosql-template-entrypoint

ENTRYPOINT ["/usr/local/bin/nosql-template-entrypoint"]
CMD ["/bin/bash"]
