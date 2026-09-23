FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PLAYWRIGHT_BROWSERS_PATH=/root/.cache/ms-playwright
ENV CI=1
ENV npm_config_yes=true
ENV TASK_ROOT=/app
ENV WORKSPACE_ROOT=/app/workspace
ENV CURATION_DATA_DIR=/app/data
ENV STATE_DIR=/app/workspace/state

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

RUN npm install -g create-next-app@latest create-vite@latest
RUN python3 -m pip install --break-system-packages playwright==1.54.0 requests==2.32.3
RUN python3 -m playwright install chromium

WORKDIR /app

COPY data /app/data
COPY data_alt /app/data_alt
COPY scripts /app/scripts
COPY skills /app/skills
COPY skills /root/.codex/skills

RUN mkdir -p /app/workspace /logs/verifier \
    && chmod +x /app/scripts/*.sh \
    && find /app/data -maxdepth 1 -type f -print0 | sort -z | xargs -0 sha256sum > /opt/fullstack-template-static-data.sha256

CMD ["/bin/bash"]
