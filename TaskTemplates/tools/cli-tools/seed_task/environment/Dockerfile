FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8
ENV HOME=/root

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        build-essential \
        ca-certificates \
        coreutils \
        curl \
        findutils \
        git \
        gzip \
        make \
        nodejs \
        npm \
        ripgrep \
        tar \
        tini \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . /tmp/template-environment
COPY skills /tmp/template-environment/skills
COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills
COPY skills /logs/agent/skills

RUN mkdir -p \
        /app/data \
        /app/output/release \
        /app/workspace \
        /root/.claude/skills \
        /root/.codex/skills \
        /root/.opencode/skill \
        /root/.goose/skills \
        /root/.factory/skills \
        /root/.agents/skills \
        /root/.gemini/skills \
        /logs/agent/skills \
        /logs/verifier \
    && : > /logs/agent/command.log \
    && cp -R /tmp/template-environment/data/. /app/data/ \
    && cp -R /tmp/template-environment/repo/. /app/workspace/airdesk/ \
    && chmod -R a+rX /app /logs/agent/skills

ENV HARBOR_LOG_AGENT_CMDS=1

RUN mv /usr/bin/make /usr/bin/make.real \
    && printf '%s\n' \
    '#!/bin/bash' \
    'set -euo pipefail' \
    'if [ "${HARBOR_LOG_AGENT_CMDS:-1}" != "0" ]; then' \
    '  printf "%s\\tmake %s\\n" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" >> /logs/agent/command.log' \
    'fi' \
    'exec /usr/bin/make.real "$@"' > /usr/bin/make \
    && chmod 755 /usr/bin/make \
    && ln -sf /usr/bin/make /usr/local/bin/make

RUN printf '%s\n' '#!/bin/bash' \
    'set -euo pipefail' \
    'if [ "$#" -eq 0 ]; then' \
    '  exec /bin/bash' \
    'elif [ "$#" -eq 1 ]; then' \
    '  exec /bin/bash -lc "$1"' \
    'else' \
    '  exec "$@"' \
    'fi' > /usr/local/bin/cli-tools-entrypoint \
    && chmod 755 /usr/local/bin/cli-tools-entrypoint

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/cli-tools-entrypoint"]
CMD ["/bin/bash"]
