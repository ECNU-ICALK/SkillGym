FROM mcr.microsoft.com/devcontainers/base:bookworm

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV REAUCTION_PORT=8146
ENV REAUCTION_SEED_DIR=/opt/real-estate-legal-audit/seed

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    bash \
    tini \
    ca-certificates \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN bash -lc 'curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.2/install.sh | bash \
    && export NVM_DIR="$HOME/.nvm" \
    && . "$NVM_DIR/nvm.sh" \
    && nvm install 22 \
    && ln -sf "$(command -v node)" /usr/local/bin/node \
    && ln -sf "$(command -v npm)" /usr/local/bin/npm'

RUN mkdir -p /services/real-estate-legal-audit \
    /opt/real-estate-legal-audit/seed \
    /root/data \
    /root/output \
    /root/.codex/skills \
    /logs/agent/skills \
    /logs/verifier \
    /var/log/real-estate-legal-audit

COPY data /root/data
COPY service_seed /opt/real-estate-legal-audit/seed
COPY hidden-service-src/server.py /services/real-estate-legal-audit/server.py
COPY skills /tmp/skills

RUN if [ -d /tmp/skills ]; then \
      cp -R /tmp/skills/. /root/.codex/skills/; \
      cp -R /tmp/skills/. /logs/agent/skills/; \
    fi \
    && rm -rf /tmp/skills \
    && find /services/real-estate-legal-audit -type f -name '*.py' -print0 | sort -z | xargs -0 sha256sum > /opt/real-estate-legal-service.sha256 \
    && find /root/data -type f -print0 | sort -z | xargs -0 sha256sum > /opt/real-estate-legal-data.sha256 \
    && find /opt/real-estate-legal-audit/seed -type f -print0 | sort -z | xargs -0 sha256sum > /opt/real-estate-legal-seed.sha256 \
    && chmod 755 /services/real-estate-legal-audit/server.py \
    && chmod -R a+rX /root/data /opt/real-estate-legal-audit/seed /root/.codex/skills /logs/agent/skills \
    && chmod 777 /root/output /var/log/real-estate-legal-audit

RUN printf '#!/bin/bash\n\
set -euo pipefail\n\
if ! python3 -c '"'"'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8146/health", timeout=1).read()'"'"' >/dev/null 2>&1; then\n\
  nohup python3 /services/real-estate-legal-audit/server.py >/tmp/real-estate-legal-audit.log 2>&1 &\n\
  for i in $(seq 1 60); do\n\
    if python3 -c '"'"'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8146/health", timeout=1).read()'"'"' >/dev/null 2>&1; then\n\
      break\n\
    fi\n\
    sleep 0.5\n\
  done\n\
fi\n\
python3 -c '"'"'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8146/health", timeout=1).read()'"'"' >/dev/null 2>&1 || {\n\
  echo "real-estate-legal audit service failed to start" >&2\n\
  [ -f /tmp/real-estate-legal-audit.log ] && cat /tmp/real-estate-legal-audit.log >&2 || true\n\
  exit 1\n\
}\n' > /usr/local/bin/start-real-estate-legal-audit \
    && chmod 755 /usr/local/bin/start-real-estate-legal-audit

RUN printf '#!/bin/bash\n\
set -euo pipefail\n\
/usr/local/bin/start-real-estate-legal-audit\n\
if [ "$#" -eq 0 ]; then\n\
  exec /bin/bash\n\
elif [ "$#" -eq 1 ]; then\n\
  exec /bin/bash -lc "$1"\n\
else\n\
  exec "$@"\n\
fi\n' > /usr/local/bin/real-estate-legal-entrypoint \
    && chmod 755 /usr/local/bin/real-estate-legal-entrypoint

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/real-estate-legal-entrypoint"]
CMD ["/bin/bash"]
