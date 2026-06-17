FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV HOME=/root
ENV TASK_ROOT=/app
ENV TASK_BRIEF_ROOT=/app/power_brief
ENV TASK_WORKSPACE_ROOT=/app/workspace
ENV TASK_OUTPUT_ROOT=/app/output
ENV PLAYWRIGHT_BROWSERS_PATH=/root/.cache/ms-playwright

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libasound2 \
        libatk-bridge2.0-0 \
        libatk1.0-0 \
        bash \
        ca-certificates \
        coreutils \
        libcups2 \
        findutils \
        fonts-dejavu-core \
        fonts-liberation \
        grep \
        libdrm2 \
        libgbm1 \
        libgtk-3-0 \
        libnspr4 \
        libnss3 \
        libx11-6 \
        libx11-xcb1 \
        libxcb1 \
        libxcomposite1 \
        libxdamage1 \
        libxext6 \
        libxfixes3 \
        libxkbcommon0 \
        libxrandr2 \
        procps \
        ripgrep \
        sed \
        tini \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    beautifulsoup4 \
    playwright==1.52.0 \
    pytest \
    pytest-json-ctrf

RUN mkdir -p /root/.cache/ms-playwright \
    && python -m playwright install chromium

COPY power_brief /app/power_brief
COPY workspace /app/workspace
COPY skills /app/workspace/skills
COPY skills /root/.codex/skills

RUN mkdir -p \
        /app/output \
        /root/.codex/skills \
        /logs/verifier \
        /opt/task-baselines \
        /root/.cache/ms-playwright \
    && if [ -d /app/power_brief ]; then cd /app/power_brief && find . -type f -print0 | sort -z | xargs -0 sha256sum > /opt/task-baselines/power-brief.sha256; else printf '' > /opt/task-baselines/power-brief.sha256; fi \
    && chmod -R a+rwX /app/workspace /app/output /logs /root/.codex /root/.cache \
    && if [ -f /app/workspace/build_site.py ]; then chmod 755 /app/workspace/build_site.py; fi \
    && chmod 644 /opt/task-baselines/power-brief.sha256

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/bin/bash"]
