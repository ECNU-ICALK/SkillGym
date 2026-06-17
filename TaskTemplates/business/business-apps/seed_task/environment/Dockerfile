FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV REVOPS_SERVICE_PORT=8144

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    coreutils \
    curl \
    jq \
    nodejs \
    npm \
    ripgrep \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir pyyaml

COPY . /opt/revops-task-env

RUN mkdir -p /services/revops /root/.codex/skills /logs/agent/skills /logs/verifier /var/log/revops /root/output \
    && cp -R /opt/revops-task-env/data /root/data \
    && if [ -d /opt/revops-task-env/skills ]; then cp -R /opt/revops-task-env/skills/. /root/.codex/skills/; fi \
    && if [ -d /opt/revops-task-env/skills ]; then cp -R /opt/revops-task-env/skills/. /logs/agent/skills/; fi \
    && python3 /opt/revops-task-env/hidden-service-src/build_runtime_service.py \
    && find /root/data -type f -print0 | sort -z | xargs -0 sha256sum > /opt/revops-data.sha256 \
    && find /services/revops -type f -print0 | sort -z | xargs -0 sha256sum > /opt/revops-service.sha256 \
    && if [ -d /root/.codex/skills ] && find /root/.codex/skills -type f | grep -q .; then find /root/.codex/skills -type f -print0 | sort -z | xargs -0 sha256sum > /opt/revops-skills.sha256; fi \
    && chmod -R 755 /services/revops \
    && chmod 644 /opt/revops-data.sha256 /opt/revops-service.sha256 \
    && if [ -f /opt/revops-skills.sha256 ]; then chmod 644 /opt/revops-skills.sha256; fi \
    && chmod 777 /var/log/revops

RUN printf '#!/bin/bash\n\
set -euo pipefail\n\
\n\
if ! python3 -c '"'"'import urllib.request; urllib.request.urlopen(\"http://127.0.0.1:8144/health\", timeout=1).read()'"'"' >/dev/null 2>&1; then\n\
  nohup python3 /services/revops/server_runtime.pyc >/tmp/revops.log 2>&1 &\n\
  for i in $(seq 1 60); do\n\
    if python3 -c '"'"'import urllib.request; urllib.request.urlopen(\"http://127.0.0.1:8144/health\", timeout=1).read()'"'"' >/dev/null 2>&1; then\n\
      break\n\
    fi\n\
    sleep 0.5\n\
  done\n\
fi\n\
\n\
python3 -c '"'"'import urllib.request; urllib.request.urlopen(\"http://127.0.0.1:8144/health\", timeout=1).read()'"'"' >/dev/null 2>&1 || {\n\
  echo \"revops service failed to start\" >&2\n\
  [ -f /tmp/revops.log ] && cat /tmp/revops.log >&2 || true\n\
  exit 1\n\
}\n' > /usr/local/bin/start-revops \
    && chmod 755 /usr/local/bin/start-revops

RUN printf '#!/bin/bash\n\
if command -v start-revops >/dev/null 2>&1; then\n\
  start-revops >/tmp/revops-profile.log 2>&1 || true\n\
fi\n' > /etc/profile.d/revops.sh \
    && chmod 644 /etc/profile.d/revops.sh

RUN printf '#!/bin/bash\n\
set -euo pipefail\n\
/usr/local/bin/start-revops\n\
if [ \"$#\" -eq 0 ]; then\n\
  exec /bin/bash\n\
elif [ \"$#\" -eq 1 ]; then\n\
  exec /bin/bash -lc \"$1\"\n\
else\n\
  exec \"$@\"\n\
fi\n' > /usr/local/bin/revops-entrypoint \
    && chmod 755 /usr/local/bin/revops-entrypoint

ENTRYPOINT ["/usr/local/bin/revops-entrypoint"]
CMD ["/bin/bash"]
