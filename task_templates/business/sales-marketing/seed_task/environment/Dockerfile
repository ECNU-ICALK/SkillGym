FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV SEO_AUDIT_PORT=8139
ENV PATH="/usr/local/bin:${PATH}"

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    coreutils \
    jq \
    nodejs \
    npm \
    ripgrep \
    && rm -rf /var/lib/apt/lists/*

RUN chmod 755 /root /bin /usr/bin /bin/sh /bin/bash || true

COPY . /opt/task_environment

RUN mkdir -p /root/workspace /root/.codex/skills /logs/agent/skills /logs/verifier /opt/.seo-runtime /var/log/seo-audit /root/output \
    && cp -R /opt/task_environment/data/site/. /root/workspace/site/ \
    && mkdir -p /root/workspace/seo_inputs \
    && cp /opt/task_environment/data/site_manifest.json /root/workspace/seo_inputs/site_manifest.json \
    && cp /opt/task_environment/data/keyword_map.csv /root/workspace/seo_inputs/keyword_map.csv \
    && cp /opt/task_environment/data/search_console_snapshot.json /root/workspace/seo_inputs/search_console_snapshot.json \
    && cp /opt/task_environment/data/crawl_snapshot.ndjson /root/workspace/seo_inputs/crawl_snapshot.ndjson \
    && cp -R /opt/task_environment/data/content_briefs/. /root/workspace/seo_inputs/content_briefs/ \
    && cp -R /opt/task_environment/data/reference_pages/. /root/workspace/seo_inputs/reference_pages/ \
    && cp /opt/task_environment/hidden-service-src/server.py /opt/.seo-runtime/seo_daemon.py \
    && chmod 755 /opt/.seo-runtime/seo_daemon.py /root/workspace/site/build_site.py \
    && sha256sum /opt/.seo-runtime/seo_daemon.py | awk '{print $1}' > /opt/seo-audit-server.sha256 \
    && find /root/workspace/seo_inputs -type f -print0 | sort -z | xargs -0 sha256sum > /opt/seo-inputs.sha256 \
    && if [ -d /opt/task_environment/skills ]; then cp -R /opt/task_environment/skills/. /root/.codex/skills/; fi \
    && if [ -d /opt/task_environment/skills ]; then cp -R /opt/task_environment/skills/. /logs/agent/skills/; fi \
    && if [ -f /root/.codex/skills/seo/bin/seo-audit ]; then cp /root/.codex/skills/seo/bin/seo-audit /usr/local/bin/seo-audit; fi \
    && for base in /root/.codex/skills /logs/agent/skills; do \
         if [ -f "$base/seo/SKILL.md" ] && ! head -n 1 "$base/seo/SKILL.md" | grep -q '^---$'; then \
           tmp="$(mktemp)"; \
           printf '%s\n' '---' 'name: seo' 'description: Use when repairing a marketing site so landing pages pass a live SEO release gate backed by a local audit chain.' '---' '' > "$tmp"; \
           cat "$base/seo/SKILL.md" >> "$tmp"; \
           mv "$tmp" "$base/seo/SKILL.md"; \
         fi; \
       done \
    && find /root/.codex/skills -type f -exec chmod 755 {} + || true \
    && find /logs/agent/skills -type f -exec chmod 755 {} + || true \
    && if [ -d /root/.codex/skills ]; then find /root/.codex/skills -type f -print0 | sort -z | xargs -0 sha256sum > /opt/seo-skills.sha256; fi \
    && rm -rf /opt/task_environment/hidden-service-src /opt/task_environment/bin \
    && chmod 777 /root/workspace /logs/verifier /var/log/seo-audit /root/output

RUN printf '#!/bin/bash\n\
set -euo pipefail\n\
\n\
if ! python3 -c '"'"'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8139/health", timeout=1).read()'"'"' >/dev/null 2>&1; then\n\
  nohup python3 /opt/.seo-runtime/seo_daemon.py >/tmp/seo-audit.log 2>&1 &\n\
  for i in $(seq 1 60); do\n\
    if python3 -c '"'"'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8139/health", timeout=1).read()'"'"' >/dev/null 2>&1; then\n\
      break\n\
    fi\n\
    sleep 0.5\n\
  done\n\
fi\n\
\n\
python3 -c '"'"'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8139/health", timeout=1).read()'"'"' >/dev/null 2>&1 || {\n\
  echo \"seo audit service failed to start\" >&2\n\
  [ -f /tmp/seo-audit.log ] && cat /tmp/seo-audit.log >&2 || true\n\
  exit 1\n\
}\n\
\n' > /opt/.seo-runtime/start_service.sh \
    && chmod 755 /opt/.seo-runtime/start_service.sh

RUN printf '#!/bin/bash\n\
set -euo pipefail\n\
/opt/.seo-runtime/start_service.sh\n\
if [ "$#" -eq 0 ]; then\n\
  exec /bin/bash\n\
elif [ "$#" -eq 1 ]; then\n\
  exec /bin/bash -lc "$1"\n\
else\n\
  exec "$@"\n\
fi\n' > /usr/local/bin/seo-task-entrypoint \
    && chmod 755 /usr/local/bin/seo-task-entrypoint

WORKDIR /root/workspace
ENTRYPOINT ["/usr/local/bin/seo-task-entrypoint"]
CMD ["/bin/bash"]
