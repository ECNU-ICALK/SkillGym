FROM mcr.microsoft.com/devcontainers/javascript-node:1-20-bookworm

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV HOME=/root
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

RUN apt-get update -o Acquire::Retries=5 \
    && apt-get install -y --no-install-recommends --fix-missing -o Acquire::Retries=5 \
    ca-certificates \
    curl \
    fonts-dejavu-core \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libglib2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libpango-1.0-0 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    python3-pip \
    ripgrep \
    tini \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /ms-playwright \
    && python3 -m pip install --break-system-packages \
    pytest==8.3.5 \
    playwright==1.52.0 \
    requests==2.32.3 \
    && python3 -m playwright install chromium

WORKDIR /app
COPY . /tmp/environment-context
COPY skills /tmp/environment-context/skills
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
      /app/workspace \
      /tests \
      /root/.claude/skills \
      /root/.codex/skills \
      /root/.opencode/skill \
      /root/.goose/skills \
      /root/.factory/skills \
      /root/.agents/skills \
      /root/.gemini/skills \
      /root/.cache \
      /home/user/.cache \
      /logs/agent/skills \
      /logs/verifier \
    && cp -R /tmp/environment-context/data/. /app/data/ \
    && cp -R /tmp/environment-context/workspace/. /app/workspace/ \
    && cp -R /tmp/environment-context/verifier/. /tests/ \
    && find /app/data -type f -print0 | sort -z | xargs -0 sha256sum > /opt/kanto-atlas-data.sha256 \
    && ln -sfn /ms-playwright /root/.cache/ms-playwright \
    && ln -sfn /ms-playwright /home/user/.cache/ms-playwright \
    && chown -R 1001:1001 /home/user /app/workspace /tests /logs /ms-playwright \
    && chmod a+rx /root /root/.cache /root/.claude /root/.codex /root/.opencode /root/.goose /root/.factory /root/.agents /root/.gemini \
    && chmod -R a+rX \
      /app/data \
      /ms-playwright \
      /root/.claude \
      /root/.codex \
      /root/.opencode \
      /root/.goose \
      /root/.factory \
      /root/.agents \
      /root/.gemini \
      /logs/agent/skills \
      /opt/kanto-atlas-data.sha256 \
    && chmod -R u+rwX,go+rX /app/workspace /tests /logs /home/user \
    && rm -rf /tmp/environment-context

RUN printf '%s\n' '#!/bin/bash' \
    'set -euo pipefail' \
    'if [ "$#" -eq 0 ]; then' \
    '  exec /bin/bash' \
    'elif [ "$#" -eq 1 ]; then' \
    '  exec /bin/bash -lc "$1"' \
    'else' \
    '  exec "$@"' \
    'fi' > /usr/local/bin/gaming-entrypoint \
    && chmod 755 /usr/local/bin/gaming-entrypoint

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/gaming-entrypoint"]
CMD ["/bin/bash"]
