FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV HF_PLANNER_PORT=8137
ENV HF_PLANNER_SEED_DIR=/opt/health-fitness-planner/seed

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    tini \
    ca-certificates \
    curl \
    nodejs \
    npm \
    ripgrep \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /services/health-fitness-planner \
    /opt/health-fitness-planner/seed \
    /root/data \
    /root/output \
    /root/.codex/skills \
    /logs/agent/skills \
    /logs/verifier \
    /var/log/health-fitness-planner

COPY data /root/data
COPY service_seed /opt/health-fitness-planner/seed
COPY hidden-service-src/server.py /services/health-fitness-planner/server.py
COPY skills /tmp/skills

RUN if [ -d /tmp/skills ]; then \
      cp -R /tmp/skills/. /root/.codex/skills/; \
      cp -R /tmp/skills/. /logs/agent/skills/; \
    fi \
    && rm -rf /tmp/skills \
    && find /services/health-fitness-planner -type f -name '*.py' -print0 | sort -z | xargs -0 sha256sum > /opt/health-fitness-service.sha256 \
    && find /root/data -type f -print0 | sort -z | xargs -0 sha256sum > /opt/health-fitness-data.sha256 \
    && find /opt/health-fitness-planner/seed -type f -print0 | sort -z | xargs -0 sha256sum > /opt/health-fitness-seed.sha256 \
    && chmod 755 /services/health-fitness-planner/server.py \
    && chmod -R a+rX /root/data /opt/health-fitness-planner/seed /root/.codex/skills /logs/agent/skills \
    && chmod 777 /root/output /var/log/health-fitness-planner

RUN printf '#!/bin/bash\n\
set -euo pipefail\n\
if ! python3 -c '"'"'import urllib.request; urllib.request.urlopen(\"http://127.0.0.1:8137/health\", timeout=1).read()'"'"' >/dev/null 2>&1; then\n\
  nohup python3 /services/health-fitness-planner/server.py >/tmp/health-fitness-planner.log 2>&1 &\n\
  for i in $(seq 1 60); do\n\
    if python3 -c '"'"'import urllib.request; urllib.request.urlopen(\"http://127.0.0.1:8137/health\", timeout=1).read()'"'"' >/dev/null 2>&1; then\n\
      break\n\
    fi\n\
    sleep 0.5\n\
  done\n\
fi\n\
python3 -c '"'"'import urllib.request; urllib.request.urlopen(\"http://127.0.0.1:8137/health\", timeout=1).read()'"'"' >/dev/null 2>&1 || {\n\
  echo \"health-fitness planner service failed to start\" >&2\n\
  [ -f /tmp/health-fitness-planner.log ] && cat /tmp/health-fitness-planner.log >&2 || true\n\
  exit 1\n\
}\n' > /usr/local/bin/start-health-fitness-planner \
    && chmod 755 /usr/local/bin/start-health-fitness-planner

RUN printf '#!/bin/bash\n\
set -euo pipefail\n\
/usr/local/bin/start-health-fitness-planner\n\
if [ \"$#\" -eq 0 ]; then\n\
  exec /bin/bash\n\
elif [ \"$#\" -eq 1 ]; then\n\
  exec /bin/bash -lc \"$1\"\n\
else\n\
  exec \"$@\"\n\
fi\n' > /usr/local/bin/health-fitness-entrypoint \
    && chmod 755 /usr/local/bin/health-fitness-entrypoint

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/health-fitness-entrypoint"]
CMD ["/bin/bash"]
