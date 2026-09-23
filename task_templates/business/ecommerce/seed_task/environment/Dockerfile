FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV ECOMMERCE_RECON_PORT=8123

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    coreutils \
    curl \
    nodejs \
    npm \
    ripgrep \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /services/ecommerce-recon /root/.codex/skills /logs/agent/skills

COPY data /root/data
COPY hidden-service-src/server.py /services/ecommerce-recon/server.py
COPY skills /root/.codex/skills
COPY skills /logs/agent/skills

RUN mkdir -p /root/output /logs/verifier /var/log/ecommerce-recon \
    && sha256sum /services/ecommerce-recon/server.py | awk '{print $1}' > /opt/ecommerce-recon-server.sha256 \
    && find /root/data -type f -print0 | sort -z | xargs -0 sha256sum > /opt/ecommerce-recon-data.sha256 \
    && chmod 755 /services/ecommerce-recon/server.py \
    && chmod 644 /opt/ecommerce-recon-server.sha256 /opt/ecommerce-recon-data.sha256 \
    && chmod 777 /var/log/ecommerce-recon

RUN printf '#!/bin/bash\n\
set -euo pipefail\n\
\n\
if ! python3 -c '"'"'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8123/health", timeout=1).read()'"'"' >/dev/null 2>&1; then\n\
  nohup python3 /services/ecommerce-recon/server.py >/tmp/ecommerce-recon.log 2>&1 &\n\
  for i in $(seq 1 60); do\n\
    if python3 -c '"'"'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8123/health", timeout=1).read()'"'"' >/dev/null 2>&1; then\n\
      break\n\
    fi\n\
    sleep 0.5\n\
  done\n\
fi\n\
\n\
python3 -c '"'"'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8123/health", timeout=1).read()'"'"' >/dev/null 2>&1 || {\n\
  echo \"ecommerce reconciliation services failed to start\" >&2\n\
  [ -f /tmp/ecommerce-recon.log ] && cat /tmp/ecommerce-recon.log >&2 || true\n\
  exit 1\n\
}\n\
\n' > /usr/local/bin/start-ecommerce-recon \
    && chmod 755 /usr/local/bin/start-ecommerce-recon

RUN printf '#!/bin/bash\n\
set -euo pipefail\n\
/usr/local/bin/start-ecommerce-recon\n\
if [ "$#" -eq 0 ]; then\n\
  exec /bin/bash\n\
elif [ "$#" -eq 1 ]; then\n\
  exec /bin/bash -lc "$1"\n\
else\n\
  exec "$@"\n\
fi\n' > /usr/local/bin/ecommerce-recon-entrypoint \
    && chmod 755 /usr/local/bin/ecommerce-recon-entrypoint

ENTRYPOINT ["/usr/local/bin/ecommerce-recon-entrypoint"]
CMD ["/bin/bash"]
