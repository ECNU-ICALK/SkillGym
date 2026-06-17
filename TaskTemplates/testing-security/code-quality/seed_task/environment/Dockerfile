FROM node:22-bookworm

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV TASK_ROOT=/app
ENV RELEASE_AUDIT_LOG=/logs/agent/release_audit_command_log.jsonl

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pip git ca-certificates ripgrep \
    && python3 -m pip install --break-system-packages pytest \
    && rm -rf /var/lib/apt/lists/*

COPY workspace /app/workspace
COPY package_base /opt/task-base/package_base
COPY skills /app/workspace/skills
COPY skills /root/.codex/skills

RUN mkdir -p /app/output /logs/agent /logs/verifier \
    && cp -R /opt/task-base/package_base /app/workspace/package \
    && cd /app/workspace/package \
    && npm install \
    && git init -b main \
    && git config user.name "Task Builder" \
    && git config user.email "task-builder@example.com" \
    && git add . \
    && git commit -m "baseline toolchain digest package" \
    && printf '%s\n' \
         'export const releaseMessaging = {' \
         '  banner: "Toolchain digest candidate",' \
         '  reviewerHint: "Audit the current candidate before promotion.",' \
         '  candidateTrack: "june-review",' \
         '} as const;' > src/releaseMessaging.ts

RUN find /app/workspace/data -type f -print0 \
      | sort -z \
      | xargs -0 -r sha256sum > /opt/toolchain-data.sha256 \
    && cd /app/workspace/package \
    && git diff --binary | sha256sum | awk '{print $1}' > /opt/toolchain-package.diff.sha256

RUN printf '#!/bin/bash\n\
set -euo pipefail\n\
if [ \"$#\" -eq 0 ]; then\n\
  exec /bin/bash\n\
elif [ \"$#\" -eq 1 ]; then\n\
  exec /bin/bash -lc \"$1\"\n\
else\n\
  exec \"$@\"\n\
fi\n' > /usr/local/bin/code-quality-entrypoint \
    && chmod 755 /usr/local/bin/code-quality-entrypoint

ENTRYPOINT ["/usr/local/bin/code-quality-entrypoint"]
CMD ["/bin/bash"]
