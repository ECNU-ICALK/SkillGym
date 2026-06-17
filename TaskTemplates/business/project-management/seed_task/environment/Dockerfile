FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV PROJECT_PLANNING_PORT=8137

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    coreutils \
    curl \
    nodejs \
    npm \
    ripgrep \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir pyyaml

COPY . /opt/project-planning-env

RUN mkdir -p /services/project-planning /root/.codex/skills /logs/agent/skills /root/output /logs/verifier /var/log/project-planning \
    && cp -R /opt/project-planning-env/data /root/data \
    && cp -R /opt/project-planning-env/hidden-service-src/. /services/project-planning/ \
    && if [ -d /opt/project-planning-env/skills ]; then cp -R /opt/project-planning-env/skills/. /root/.codex/skills/; fi \
    && if [ -d /opt/project-planning-env/skills ]; then cp -R /opt/project-planning-env/skills/. /logs/agent/skills/; fi \
    && find /root/data -type f -print0 | sort -z | xargs -0 sha256sum > /opt/project-planning-data.sha256 \
    && find /services/project-planning -type f -print0 | sort -z | xargs -0 sha256sum > /opt/project-planning-service.sha256 \
    && chmod -R 755 /services/project-planning \
    && chmod 644 /opt/project-planning-data.sha256 /opt/project-planning-service.sha256 \
    && chmod 777 /var/log/project-planning

RUN printf '#!/bin/bash\n\
set -euo pipefail\n\
\n\
if ! python3 -c '"'"'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8137/health", timeout=1).read()'"'"' >/dev/null 2>&1; then\n\
  nohup python3 /services/project-planning/server.py >/tmp/project-planning.log 2>&1 &\n\
  for i in $(seq 1 60); do\n\
    if python3 -c '"'"'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8137/health", timeout=1).read()'"'"' >/dev/null 2>&1; then\n\
      break\n\
    fi\n\
    sleep 0.5\n\
  done\n\
fi\n\
\n\
python3 -c '"'"'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8137/health", timeout=1).read()'"'"' >/dev/null 2>&1 || {\n\
  echo \"project planning service failed to start\" >&2\n\
  [ -f /tmp/project-planning.log ] && cat /tmp/project-planning.log >&2 || true\n\
  exit 1\n\
}\n' > /usr/local/bin/start-project-planning \
    && chmod 755 /usr/local/bin/start-project-planning

RUN printf '#!/bin/bash\n\
set -euo pipefail\n\
/usr/local/bin/start-project-planning\n\
if [ "$#" -eq 0 ]; then\n\
  exec /bin/bash\n\
elif [ "$#" -eq 1 ]; then\n\
  exec /bin/bash -lc "$1"\n\
else\n\
  exec "$@"\n\
fi\n' > /usr/local/bin/project-planning-entrypoint \
    && chmod 755 /usr/local/bin/project-planning-entrypoint

ENTRYPOINT ["/usr/local/bin/project-planning-entrypoint"]
CMD ["/bin/bash"]
