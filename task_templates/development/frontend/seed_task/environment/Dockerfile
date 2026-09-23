FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    python3 \
    python3-pip \
    xz-utils \
    lsof \
    psmisc \
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

WORKDIR /services/energy-api
COPY energy-api/ /services/energy-api/
RUN npm ci

WORKDIR /data
COPY data/ /data/

WORKDIR /app
COPY app/ /app/
RUN npm ci

COPY scripts/ /scripts/
RUN chmod +x /scripts/*.sh

COPY skills/frontend-patterns /app/.claude/skills/frontend-patterns
COPY skills/frontend-patterns /app/.codex/skills/frontend-patterns
COPY skills/frontend-patterns /app/.opencode/skills/frontend-patterns
COPY skills/frontend-patterns /app/.goose/skills/frontend-patterns
COPY skills/frontend-patterns /app/.factory/skills/frontend-patterns
COPY skills/frontend-patterns /app/.agents/skills/frontend-patterns
COPY skills/frontend-patterns /app/.cursor/skills/frontend-patterns
COPY skills/frontend-patterns /root/.gemini/skills/frontend-patterns
COPY skills /app/skills

ENV VITE_API_BASE_URL=http://localhost:3001
ENV PLAYWRIGHT_BROWSERS_PATH=/root/.cache/ms-playwright

CMD ["/bin/bash"]
