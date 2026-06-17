FROM node:22-bookworm

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV TASK_ROOT=/app

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pip curl \
    && python3 -m pip install --break-system-packages pytest \
    && rm -rf /var/lib/apt/lists/*

COPY workspace /app/workspace
COPY provider-sim /services/provider-sim
COPY skills /app/workspace/skills
COPY skills /root/.codex/skills
COPY skills /logs/agent/skills

RUN cd /app/workspace && npm install
RUN cd /services/provider-sim && npm install

RUN cd /app/workspace \
    && node scripts/reset_runtime_state.js \
    && mkdir -p /logs/agent /logs/verifier \
    && find /app/workspace/data -type f -print0 | sort -z | xargs -0 sha256sum > /opt/llm-ai-template-static-data.sha256

RUN printf '#!/bin/bash\n\
set -euo pipefail\n\
cd /app/workspace\n\
node scripts/reset_runtime_state.js >/dev/null\n\
if [ \"$#\" -eq 0 ]; then\n\
  exec /bin/bash\n\
elif [ \"$#\" -eq 1 ]; then\n\
  exec /bin/bash -lc \"$1\"\n\
else\n\
  exec \"$@\"\n\
fi\n' > /usr/local/bin/llm-ai-template-entrypoint \
    && chmod 755 /usr/local/bin/llm-ai-template-entrypoint

ENTRYPOINT ["/usr/local/bin/llm-ai-template-entrypoint"]
CMD ["/bin/bash"]
