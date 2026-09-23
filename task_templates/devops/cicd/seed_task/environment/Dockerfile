FROM mcr.microsoft.com/devcontainers/javascript-node:1-20-bookworm

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV HOME=/root

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    jq \
    make \
    python3 \
    python3-pytest \
    python3-yaml \
    ripgrep \
    tini \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /tmp/template-environment
COPY skills /tmp/template-environment/skills
COPY skills /logs/agent/skills
COPY skills /root/.codex/skills

RUN mkdir -p \
      /app/data \
      /app/output \
      /app/workspace \
      /root/.codex/skills \
      /logs/agent/skills \
      /logs/verifier \
    && TASK_ENV_ROOT="/tmp/template-environment" \
    && if [ -d /tmp/template-environment/environment ]; then TASK_ENV_ROOT="/tmp/template-environment/environment"; fi \
    && cp -R "$TASK_ENV_ROOT/data/." /app/data/ \
    && cp -R "$TASK_ENV_ROOT/workspace/." /app/workspace/ \
    && find /app/data -type f -print0 | sort -z | xargs -0 sha256sum | sed 's#  /app/data/#  #' > /opt/cicd-input.sha256 \
    && chmod -R a+rX /app /logs/agent/skills /opt/cicd-input.sha256

RUN printf '%s\n' '#!/bin/bash' \
    'set -euo pipefail' \
    'if [ "$#" -eq 0 ]; then' \
    '  exec /bin/bash' \
    'elif [ "$#" -eq 1 ]; then' \
    '  exec /bin/bash -lc "$1"' \
    'else' \
    '  exec "$@"' \
    'fi' > /usr/local/bin/cicd-entrypoint \
    && chmod 755 /usr/local/bin/cicd-entrypoint

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/cicd-entrypoint"]
CMD ["/bin/bash"]
