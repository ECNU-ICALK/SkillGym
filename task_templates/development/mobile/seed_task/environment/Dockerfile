FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    bash \
    curl \
    ca-certificates \
    python3 \
    python3-pip \
    xz-utils \
    psmisc \
    lsof \
    libasound2t64 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

RUN ARCH=$(dpkg --print-architecture) && \
    if [ "$ARCH" = "amd64" ]; then NODE_ARCH="x64"; else NODE_ARCH="$ARCH"; fi && \
    curl -fsSL "https://nodejs.org/dist/v20.18.1/node-v20.18.1-linux-${NODE_ARCH}.tar.xz" | tar -xJ -C /usr/local --strip-components=1

RUN python3 -m pip install --break-system-packages playwright==1.54.0
RUN python3 -m playwright install chromium

RUN mkdir -p \
    /app/workspace/app \
    /app/workspace/data \
    /app/workspace/artifacts \
    /app/workspace/scripts \
    /services/citibike-api \
    /opt/task-skills \
    /root/.codex/skills \
    /app/workspace/app/.codex/skills \
    /app/workspace/app/.claude/skills \
    /app/workspace/app/.agents/skills \
    /app/workspace/app/.cursor/skills \
    /root/.gemini/skills \
    /logs/verifier \
    /var/log/citibike-api

WORKDIR /services/citibike-api
COPY services/bike-api/ /services/citibike-api/
RUN npm ci

WORKDIR /app/workspace/data
COPY data/ /app/workspace/data/

WORKDIR /app/workspace/app
COPY app/ /app/workspace/app/
RUN npm ci

COPY scripts/ /app/workspace/scripts/
RUN chmod +x /app/workspace/scripts/*.sh

COPY skills /app/workspace/app/skills
COPY skills/ /opt/task-skills/
RUN bash /app/workspace/scripts/install_skills.sh /opt/task-skills

RUN find /app/workspace/data -type f -print0 | sort -z | xargs -0 sha256sum > /opt/citibike-data.sha256 && \
    find /services/citibike-api -type f -print0 | sort -z | xargs -0 sha256sum > /opt/citibike-api.sha256

ENV VITE_API_BASE_URL=http://localhost:3001
ENV CITIBIKE_DATA_DIR=/app/workspace/data
ENV PLAYWRIGHT_BROWSERS_PATH=/root/.cache/ms-playwright

RUN printf '#!/bin/bash\n\
set -euo pipefail\n\
if ! curl -fsS http://127.0.0.1:3001/health >/dev/null 2>&1; then\n\
  nohup bash /app/workspace/scripts/start_api.sh >/tmp/citibike-api.log 2>&1 &\n\
  for i in $(seq 1 60); do\n\
    if curl -fsS http://127.0.0.1:3001/health >/dev/null 2>&1; then\n\
      break\n\
    fi\n\
    sleep 0.5\n\
  done\n\
fi\n\
curl -fsS http://127.0.0.1:3001/health >/dev/null 2>&1 || {\n\
  echo \"citibike-api failed to start\" >&2\n\
  [ -f /tmp/citibike-api.log ] && cat /tmp/citibike-api.log >&2 || true\n\
  exit 1\n\
}\n' > /usr/local/bin/start-citibike-api && chmod 755 /usr/local/bin/start-citibike-api

CMD ["/bin/bash"]
