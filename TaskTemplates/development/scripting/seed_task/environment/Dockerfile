FROM node:22-bookworm

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8
ENV HOME=/root

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 bash coreutils findutils grep sed gawk ca-certificates tini curl ripgrep \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . /tmp/template-environment
COPY skills /tmp/template-environment/skills
COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills
COPY skills /logs/agent/skills

RUN mkdir -p /app/bin /app/data /app/output /root/.claude/skills /root/.codex/skills /root/.opencode/skill /root/.goose/skills /root/.factory/skills /root/.agents/skills /root/.gemini/skills /logs/agent/skills /logs/verifier \
    && cp -R /tmp/template-environment/bin/. /app/bin/ \
    && cp -R /tmp/template-environment/data/. /app/data/ \
    && chmod +x /app/bin/rebuild_airport_reports.sh /app/bin/steps/*.sh \
    && chmod -R a+rX /app /logs/agent/skills

RUN printf '%s\n' '#!/bin/bash' \
    'set -euo pipefail' \
    'if [ "$#" -eq 0 ]; then' \
    '  exec /bin/bash' \
    'elif [ "$#" -eq 1 ]; then' \
    '  exec /bin/bash -lc "$1"' \
    'else' \
    '  exec "$@"' \
    'fi' > /usr/local/bin/scripting-airports-entrypoint \
    && chmod 755 /usr/local/bin/scripting-airports-entrypoint

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/scripting-airports-entrypoint"]
CMD ["/bin/bash"]
