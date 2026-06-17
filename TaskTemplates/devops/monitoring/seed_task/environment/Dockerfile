FROM node:22-bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV HOME=/root

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    jq \
    python3 \
    ripgrep \
    tini \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://github.com/prometheus/prometheus/releases/download/v2.55.1/prometheus-2.55.1.linux-amd64.tar.gz \
    | tar -xz -C /tmp \
    && mv /tmp/prometheus-2.55.1.linux-amd64/prometheus /usr/local/bin/prometheus \
    && mv /tmp/prometheus-2.55.1.linux-amd64/promtool /usr/local/bin/promtool \
    && rm -rf /tmp/prometheus-2.55.1.linux-amd64

WORKDIR /app
COPY . /tmp/template-environment
COPY skills /tmp/template-environment/skills
COPY skills /root/.codex/skills
COPY skills /logs/agent/skills

RUN mkdir -p \
      /app/bin \
      /app/data \
      /app/output \
      /app/runtime \
      /app/workspace \
      /services/metrics \
      /root/.codex/skills \
      /logs/agent/skills \
      /logs/verifier \
    && cp -R /tmp/template-environment/bin/. /app/bin/ \
    && cp -R /tmp/template-environment/data/. /app/data/ \
    && cp -R /tmp/template-environment/runtime/. /app/runtime/ \
    && cp -R /tmp/template-environment/workspace/. /app/workspace/ \
    && cp -R /tmp/template-environment/services/. /services/metrics/ \
    && cp -R /app/runtime/inventory/. /app/workspace/prometheus/inventory/ \
    && mkdir -p /app/workspace/prometheus/skill_hints \
    && if [ -d /tmp/template-environment/skills ]; then \
         find /tmp/template-environment/skills -mindepth 2 -maxdepth 4 -type f \( -path "*/resources/*" -o -path "*/references/*" -o -path "*/assets/*" \) -print0 | while IFS= read -r -d "" file; do \
           rel="${file#/tmp/template-environment/skills/}"; \
           skill_name="${rel%%/*}"; \
           base="$(basename "$file")"; \
           cp "$file" "/app/workspace/prometheus/skill_hints/${skill_name}__${base}"; \
         done; \
         find /tmp/template-environment/skills -path "*/resources/implementation-playbook.md" -print -quit | while IFS= read -r file; do cp "$file" /app/workspace/prometheus/PROMETHEUS_PLAYBOOK.md; done; \
         find /tmp/template-environment/skills -path "*/references/scrape-configs.md" -print -quit | while IFS= read -r file; do cp "$file" /app/workspace/prometheus/SCRAPE_CONFIGS.md; done; \
         find /tmp/template-environment/skills -path "*/assets/prometheus.yml.template" -print -quit | while IFS= read -r file; do cp "$file" /app/workspace/prometheus/prometheus.template.yml; done; \
         find /tmp/template-environment/skills -path "*/assets/post-build-checklist.md" -print -quit | while IFS= read -r file; do cp "$file" /app/workspace/prometheus/POST_BUILD_CHECKLIST.md; done; \
         find /tmp/template-environment/skills -path "*/assets/inventory-readme-snippet.md" -print -quit | while IFS= read -r file; do printf "\n" >> /app/workspace/prometheus/inventory/README.md; cat "$file" >> /app/workspace/prometheus/inventory/README.md; done; \
       fi \
    && find /app/data -type f -print0 | sort -z | xargs -0 sha256sum | sed 's#  /app/data/#  #' > /opt/monitoring-input.sha256 \
    && chmod +x /app/bin/start_metrics_services.sh \
                /app/bin/start_bundle.sh \
                /app/bin/reload_bundle.sh \
                /app/bin/render_report.py \
                /app/bin/query_prometheus.py \
                /services/metrics/serve_metrics.py \
    && chmod -R a+rX /app /services/metrics /logs/agent/skills /opt/monitoring-input.sha256

RUN printf '%s\n' '#!/bin/bash' \
    'set -euo pipefail' \
    '/app/bin/start_bundle.sh >/app/runtime/logs/entrypoint-start.log 2>&1 || {' \
    '  cat /app/runtime/logs/entrypoint-start.log >&2' \
    '  exit 1' \
    '}' \
    'if [ "$#" -eq 0 ]; then' \
    '  exec /bin/bash' \
    'elif [ "$#" -eq 1 ]; then' \
    '  exec /bin/bash -lc "$1"' \
    'else' \
    '  exec "$@"' \
    'fi' > /usr/local/bin/monitoring-entrypoint \
    && chmod 755 /usr/local/bin/monitoring-entrypoint

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/monitoring-entrypoint"]
CMD ["/bin/bash"]
