FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_PROGRESS_BAR=off
ENV MPLBACKEND=Agg
ENV BIOINFO_SCANPY_PORT=8143
ENV BIOINFO_SCANPY_SEED_DIR=/opt/bioinfo-scanpy/seed

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    ca-certificates \
    nodejs \
    npm \
    ripgrep \
    tini \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --upgrade pip \
    && python3 -m pip install --timeout 120 \
      scanpy==1.10.2 \
      igraph==0.11.5 \
      leidenalg==0.10.2

RUN mkdir -p /services/bioinfo-scanpy \
    /opt/bioinfo-scanpy/seed \
    /root/data \
    /root/output \
    /root/workspace \
    /root/.codex/skills \
    /logs/agent/skills \
    /logs/verifier \
    /var/log/bioinfo-scanpy

COPY data /root/data
COPY service_seed /opt/bioinfo-scanpy/seed
COPY hidden-service-src/server.py /services/bioinfo-scanpy/server.py
COPY skills /root/environment/skills

RUN if [ -d /root/environment/skills ]; then \
      cp -R /root/environment/skills/. /root/.codex/skills/; \
    fi \
    && find /services/bioinfo-scanpy -type f -name '*.py' -print0 | sort -z | xargs -0 sha256sum > /opt/bioinfo-scanpy-service.sha256 \
    && find /root/data -type f -print0 | sort -z | xargs -0 sha256sum > /opt/bioinfo-scanpy-data.sha256 \
    && find /opt/bioinfo-scanpy/seed -type f -print0 | sort -z | xargs -0 sha256sum > /opt/bioinfo-scanpy-seed.sha256 \
    && chmod 755 /services/bioinfo-scanpy/server.py \
    && chmod -R a+rX /root/data /opt/bioinfo-scanpy/seed /root/.codex/skills /logs/agent/skills \
    && chmod 777 /root/output /root/workspace /var/log/bioinfo-scanpy

RUN printf '#!/bin/bash\n\
set -euo pipefail\n\
if ! python3 -c '"'"'import urllib.request; urllib.request.urlopen(\"http://127.0.0.1:8143/health\", timeout=1).read()'"'"' >/dev/null 2>&1; then\n\
  nohup python3 /services/bioinfo-scanpy/server.py >/tmp/bioinfo-scanpy.log 2>&1 &\n\
  for i in $(seq 1 120); do\n\
    if python3 -c '"'"'import urllib.request; urllib.request.urlopen(\"http://127.0.0.1:8143/health\", timeout=1).read()'"'"' >/dev/null 2>&1; then\n\
      break\n\
    fi\n\
    sleep 0.5\n\
  done\n\
fi\n\
python3 -c '"'"'import urllib.request; urllib.request.urlopen(\"http://127.0.0.1:8143/health\", timeout=1).read()'"'"' >/dev/null 2>&1 || {\n\
  echo \"bioinfo-scanpy service failed to start\" >&2\n\
  [ -f /tmp/bioinfo-scanpy.log ] && cat /tmp/bioinfo-scanpy.log >&2 || true\n\
  exit 1\n\
}\n' > /usr/local/bin/start-bioinfo-scanpy-service \
    && chmod 755 /usr/local/bin/start-bioinfo-scanpy-service

RUN printf '#!/bin/bash\n\
set -euo pipefail\n\
/usr/local/bin/start-bioinfo-scanpy-service\n\
if [ \"$#\" -eq 0 ]; then\n\
  exec /bin/bash\n\
elif [ \"$#\" -eq 1 ]; then\n\
  exec /bin/bash -lc \"$1\"\n\
else\n\
  exec \"$@\"\n\
fi\n' > /usr/local/bin/bioinfo-scanpy-entrypoint \
    && chmod 755 /usr/local/bin/bioinfo-scanpy-entrypoint

RUN printf '\nif command -v start-bioinfo-scanpy-service >/dev/null 2>&1; then\n  start-bioinfo-scanpy-service >/dev/null 2>&1 || true\nfi\n' >> /root/.bashrc

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/bioinfo-scanpy-entrypoint"]
CMD ["/bin/bash"]
