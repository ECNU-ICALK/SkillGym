FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV CONTENT_PACK_PORT=8080

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    ca-certificates \
    coreutils \
    curl \
    jq \
    npm \
    ripgrep \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir pytest

COPY . /opt/literature-writing-environment
COPY skills /opt/literature-writing-environment/skills
COPY skills /root/.codex/skills
COPY skills /logs/agent/skills

RUN mkdir -p /workspace/notes /workspace/drafts /workspace/examples/approved_copy /opt/launch-copy-data /services/launch-copy-service /var/log/launch-copy /root/.codex/skills /logs/agent/skills \
    && cp /opt/literature-writing-environment/data/work_order.json /workspace/work_order.json \
    && cp /opt/literature-writing-environment/data/service_manifest.json /workspace/service_manifest.json \
    && cp /opt/literature-writing-environment/data/editorial_constraints.json /workspace/notes/editorial_constraints.json \
    && cp /opt/literature-writing-environment/data/rejected_copy.json /workspace/drafts/rejected_copy.json \
    && cp -R /opt/literature-writing-environment/data/tone_examples/. /workspace/examples/approved_copy/ \
    && cp -R /opt/literature-writing-environment/data/. /opt/launch-copy-data/ \
    && cp -R /opt/literature-writing-environment/hidden-service-src/. /services/launch-copy-service/ \
    && find /workspace/work_order.json /workspace/service_manifest.json /workspace/notes /workspace/drafts /workspace/examples/approved_copy -type f -print0 | sort -z | xargs -0 sha256sum > /opt/workspace-inputs.sha256 \
    && find /opt/launch-copy-data -type f -print0 | sort -z | xargs -0 sha256sum > /opt/launch-copy-data.sha256 \
    && find /services/launch-copy-service -type f -print0 | sort -z | xargs -0 sha256sum > /opt/launch-copy-service.sha256 \
    && chmod -R 755 /services/launch-copy-service \
    && chmod 644 /opt/workspace-inputs.sha256 /opt/launch-copy-data.sha256 /opt/launch-copy-service.sha256

RUN printf '#!/bin/bash\n\
set -euo pipefail\n\
\n\
if ! python3 -c '"'"'import urllib.request; urllib.request.urlopen(\"http://127.0.0.1:8080/health\", timeout=1).read()'"'"' >/dev/null 2>&1; then\n\
  nohup python3 /services/launch-copy-service/server.py >/tmp/launch-copy-service.log 2>&1 &\n\
  for i in $(seq 1 60); do\n\
    if python3 -c '"'"'import urllib.request; urllib.request.urlopen(\"http://127.0.0.1:8080/health\", timeout=1).read()'"'"' >/dev/null 2>&1; then\n\
      break\n\
    fi\n\
    sleep 0.5\n\
  done\n\
fi\n\
\n\
python3 -c '"'"'import urllib.request; urllib.request.urlopen(\"http://127.0.0.1:8080/health\", timeout=1).read()'"'"' >/dev/null 2>&1 || {\n\
  echo \"launch copy service failed to start\" >&2\n\
  [ -f /tmp/launch-copy-service.log ] && cat /tmp/launch-copy-service.log >&2 || true\n\
  exit 1\n\
}\n' > /usr/local/bin/start-launch-copy-service \
    && chmod 755 /usr/local/bin/start-launch-copy-service

RUN printf '#!/bin/bash\n\
if command -v start-launch-copy-service >/dev/null 2>&1; then\n\
  start-launch-copy-service >/tmp/launch-copy-profile.log 2>&1 || true\n\
fi\n' > /etc/profile.d/launch-copy-service.sh \
    && chmod 644 /etc/profile.d/launch-copy-service.sh

RUN printf '#!/bin/bash\n\
set -euo pipefail\n\
/usr/local/bin/start-launch-copy-service\n\
if [ \"$#\" -eq 0 ]; then\n\
  exec /bin/bash\n\
elif [ \"$#\" -eq 1 ]; then\n\
  exec /bin/bash -lc \"$1\"\n\
else\n\
  exec \"$@\"\n\
fi\n' > /usr/local/bin/launch-copy-entrypoint \
    && chmod 755 /usr/local/bin/launch-copy-entrypoint

ENTRYPOINT ["/usr/local/bin/launch-copy-entrypoint"]
CMD ["/bin/bash"]
