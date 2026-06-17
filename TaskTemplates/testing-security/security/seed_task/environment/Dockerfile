FROM node:22-bookworm

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV TASK_ROOT=/app
ENV EXPORT_SIGNING_SECRET=task-export-signing-secret

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pip curl \
    && python3 -m pip install --break-system-packages pytest \
    && rm -rf /var/lib/apt/lists/*

COPY workspace /app/workspace
COPY skills /app/workspace/skills
COPY skills /root/.codex/skills
COPY skills /logs/agent/skills

RUN cd /app/workspace \
    && npm install \
    && node scripts/reset_runtime_state.js \
    && mkdir -p /logs/agent /logs/verifier /var/log/tenant-advisory

RUN printf '#!/bin/bash\n\
set -euo pipefail\n\
cd /app/workspace\n\
node scripts/reset_runtime_state.js >/dev/null\n\
if [ "$#" -eq 0 ]; then\n\
  exec /bin/bash\n\
elif [ "$#" -eq 1 ]; then\n\
  exec /bin/bash -lc "$1"\n\
else\n\
  exec "$@"\n\
fi\n' > /usr/local/bin/tenant-advisory-entrypoint \
    && chmod 755 /usr/local/bin/tenant-advisory-entrypoint

ENTRYPOINT ["/usr/local/bin/tenant-advisory-entrypoint"]
CMD ["/bin/bash"]
