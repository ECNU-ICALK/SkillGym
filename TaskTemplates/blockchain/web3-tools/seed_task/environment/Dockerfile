FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV TASK_APP_ROOT=/app
ENV TASK_DATA_ROOT=/app/data
ENV TASK_WORKSPACE_ROOT=/app/workspace/marketwatch
ENV TASK_OUTPUT_ROOT=/app/output/surveillance
ENV MARKETDATA_HOST=127.0.0.1
ENV MARKETDATA_PORT=8155
ENV MARKETDATA_FIXTURE_PATH=/app/data/service_fixtures/market_data.json
ENV MARKETDATA_ACCESS_LOG=/var/log/marketdata/access.log
ENV TASK_HEALTH_URL=http://127.0.0.1:8155/health

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    ca-certificates \
    curl \
    jq \
    nodejs \
    npm \
    procps \
    ripgrep \
    tini \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir openpyxl pytest-json-ctrf

COPY . /opt/web3-task-env
COPY skills /opt/web3-task-env/skills
COPY skills /root/.codex/skills
COPY skills /logs/agent/skills

RUN mkdir -p /app/data /app/workspace/marketwatch /app/output/surveillance /root/.codex/skills /logs/agent/skills /logs/verifier /services/marketdata /opt/task-baselines /var/log/marketdata \
    && cp -R /opt/web3-task-env/data/. /app/data/ \
    && cp -R /opt/web3-task-env/workspace/marketwatch/. /app/workspace/marketwatch/ \
    && cp -R /opt/web3-task-env/hidden-service-src/. /services/marketdata/ \
    && find /app/data -type f -print0 | sort -z | xargs -0 sha256sum > /opt/task-baselines/data.sha256 \
    && find /services/marketdata -type f ! -path '*/__pycache__/*' -print0 | sort -z | xargs -0 sha256sum > /opt/task-baselines/service.sha256 \
    && chmod -R a+rwX /app/workspace /app/output /logs /var/log/marketdata \
    && chmod 644 /opt/task-baselines/data.sha256 /opt/task-baselines/service.sha256

RUN printf '#!/bin/bash\n\
set -euo pipefail\n\
\n\
if ! python3 -c '"'"'import urllib.request; urllib.request.urlopen(\"http://127.0.0.1:8155/health\", timeout=1).read()'"'"' >/dev/null 2>&1; then\n\
  nohup python3 /services/marketdata/server.py >/tmp/marketdata.log 2>&1 &\n\
  for i in $(seq 1 60); do\n\
    if python3 -c '"'"'import urllib.request; urllib.request.urlopen(\"http://127.0.0.1:8155/health\", timeout=1).read()'"'"' >/dev/null 2>&1; then\n\
      break\n\
    fi\n\
    sleep 0.5\n\
  done\n\
fi\n\
\n\
python3 -c '"'"'import urllib.request; urllib.request.urlopen(\"http://127.0.0.1:8155/health\", timeout=1).read()'"'"' >/dev/null 2>&1 || {\n\
  echo \"marketdata service failed to start\" >&2\n\
  [ -f /tmp/marketdata.log ] && cat /tmp/marketdata.log >&2 || true\n\
  exit 1\n\
}\n' > /usr/local/bin/start-marketdata \
    && chmod 755 /usr/local/bin/start-marketdata

RUN printf '#!/bin/bash\n\
if command -v start-marketdata >/dev/null 2>&1; then\n\
  start-marketdata >/tmp/marketdata-profile.log 2>&1 || true\n\
fi\n' > /etc/profile.d/marketdata.sh \
    && chmod 644 /etc/profile.d/marketdata.sh

RUN printf '#!/bin/bash\n\
set -euo pipefail\n\
/usr/local/bin/start-marketdata\n\
if [ \"$#\" -eq 0 ]; then\n\
  exec /bin/bash\n\
elif [ \"$#\" -eq 1 ]; then\n\
  exec /bin/bash -lc \"$1\"\n\
else\n\
  exec \"$@\"\n\
fi\n' > /usr/local/bin/web3-tools-entrypoint \
    && chmod 755 /usr/local/bin/web3-tools-entrypoint

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/web3-tools-entrypoint"]
CMD ["/bin/bash"]
