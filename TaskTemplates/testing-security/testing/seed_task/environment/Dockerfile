FROM mcr.microsoft.com/playwright:v1.52.0-jammy

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV TASK_ROOT=/app
ENV PLAYWRIGHT_BROWSERS_PATH=/root/.cache/ms-playwright

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pytest ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY . /tmp/environment-context
COPY skills /tmp/environment-context/skills
COPY skills /root/.codex/skills

RUN mkdir -p /app/workspace /tests /logs/agent /logs/verifier /root/.codex/skills \
    && cp -R /tmp/environment-context/workspace/. /app/workspace/ \
    && mkdir -p /app/workspace/data \
    && cp -R /tmp/environment-context/data/. /app/workspace/data/ \
    && cd /app/workspace \
    && npm ci \
    && npx playwright install chromium \
    && find /app/workspace/server.js /app/workspace/public /app/workspace/package.json /app/workspace/package-lock.json /app/workspace/playwright.config.js -type f -print0 | sort -z | xargs -0 sha256sum > /opt/airport-app.sha256 \
    && find /app/workspace/data -type f -print0 | sort -z | xargs -0 sha256sum > /opt/airport-data.sha256 \
    && rm -rf /tmp/environment-context

RUN printf '#!/bin/bash\n\
set -euo pipefail\n\
if [ \"$#\" -eq 0 ]; then\n\
  exec /bin/bash\n\
elif [ \"$#\" -eq 1 ]; then\n\
  exec /bin/bash -lc \"$1\"\n\
else\n\
  exec \"$@\"\n\
fi\n' > /usr/local/bin/testing-entrypoint \
    && chmod 755 /usr/local/bin/testing-entrypoint

ENTRYPOINT ["/usr/local/bin/testing-entrypoint"]
CMD ["/bin/bash"]
